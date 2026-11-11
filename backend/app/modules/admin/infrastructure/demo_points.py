"""Puntos de demostración sobre los datos de OSM cargados en PostGIS (decisión 76).

Con los mismos datos de OSM, ``pick`` devuelve siempre los mismos puntos: las consultas
ordenan por identificador y no hay azar.
"""

import math
from collections.abc import Iterable, Sequence
from typing import Final

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.modules.admin.domain.demo import (
    DEMO_NEAR_SERVICE_COUNT,
    DEMO_OFF_ROAD_COUNT,
    DEMO_ROAD_QUOTAS,
    DemoPoint,
)
from app.modules.reports.domain.severity import Severity
from app.modules.roads.domain.road_class import RoadClass
from app.shared.domain.geo import BoundingBox, GeoPoint
from app.shared.domain.geo_parameters import (
    DEDUPLICATION_RADIUS_M,
    PROXIMITY_FULL_SCORE_RADIUS_M,
    ROAD_MATCHING_RADIUS_M,
)

# El doble del radio de deduplicación: ningún punto es «posible duplicado» de otro, con
# margen para la distancia aproximada de ``_distance_m``.
MIN_SEPARATION_M: Final = 2 * DEDUPLICATION_RADIUS_M
# El punto «cerca de un servicio» se pone sobre una vía a esta distancia o menos del
# servicio: queda dentro del radio de P = 10 con margen.
NEAR_SERVICE_ROAD_RADIUS_M: Final = PROXIMITY_FULL_SCORE_RADIUS_M / 2
# Un punto «sin vía» debe quedar más lejos que el radio de map-matching, con margen.
OFF_ROAD_MIN_DISTANCE_M: Final = ROAD_MATCHING_RADIUS_M + 10.0
# Lado de la malla de candidatos «sin vía» (25 por 25 puntos repartidos por el área).
OFF_ROAD_GRID_SIDE: Final = 25
# Se leen más candidatos que cupos: algunos se descartan por estar junto a otro punto.
CANDIDATES_PER_SLOT: Final = 25

_SEVERITY_CYCLE: Final = (Severity.LOW, Severity.MEDIUM, Severity.HIGH)
_EARTH_RADIUS_M: Final = 6_371_008.8

_ENVELOPE = "ST_MakeEnvelope(:west, :south, :east, :north, 4326)"

# Punto medio de cada vía de la jerarquía pedida.
_ROAD_MIDPOINTS = text(
    f"""
    SELECT c.id_via, ST_X(c.medio) AS lon, ST_Y(c.medio) AS lat
    FROM (
        SELECT v.id_via, ST_LineInterpolatePoint(v.geom, 0.5) AS medio
        FROM via AS v
        WHERE v.jerarquia_vial = CAST(:road_class AS jerarquia_vial)
          AND v.geom && {_ENVELOPE}
    ) AS c
    WHERE c.medio && {_ENVELOPE}
    ORDER BY c.id_via
    LIMIT :limit
    """  # noqa: S608 - solo se interpola la constante _ENVELOPE; los valores van enlazados
)

# Para cada servicio crítico, el punto de la vía más cercana que queda frente a él.
_POINTS_NEAR_SERVICES = text(
    f"""
    SELECT c.id_via, ST_X(c.punto) AS lon, ST_Y(c.punto) AS lat
    FROM servicio_critico AS s
    CROSS JOIN LATERAL (
        SELECT v.id_via, ST_ClosestPoint(v.geom, s.ubicacion) AS punto
        FROM via AS v
        WHERE ST_DWithin(v.geom::geography, s.ubicacion::geography, :radio_m)
        ORDER BY ST_Distance(v.geom::geography, s.ubicacion::geography), v.id_via
        LIMIT 1
    ) AS c
    WHERE s.ubicacion && {_ENVELOPE}
    ORDER BY s.id_servicio
    LIMIT :limit
    """  # noqa: S608 - solo se interpola la constante _ENVELOPE; los valores van enlazados
)

# Puntos de una malla sobre el área que no tienen ninguna vía cerca, empezando por los
# más próximos a la red vial (los bordes de la ciudad antes que el campo abierto).
_POINTS_OFF_ROAD = text(
    """
    WITH malla AS (
        SELECT i, j,
               ST_SetSRID(
                   ST_MakePoint(
                       :west + (:east - :west) * (i + 0.5) / :side,
                       :south + (:north - :south) * (j + 0.5) / :side
                   ),
                   4326
               ) AS punto
        FROM generate_series(0, :side - 1) AS i, generate_series(0, :side - 1) AS j
    )
    SELECT ST_X(m.punto) AS lon, ST_Y(m.punto) AS lat
    FROM malla AS m
    CROSS JOIN LATERAL (
        SELECT ST_Distance(v.geom::geography, m.punto::geography) AS distancia_m
        FROM via AS v
        ORDER BY v.geom <-> m.punto
        LIMIT 1
    ) AS cercana
    WHERE cercana.distancia_m > :min_distance_m
    ORDER BY cercana.distancia_m, m.i, m.j
    LIMIT :limit
    """
)


def _distance_m(a: GeoPoint, b: GeoPoint) -> float:
    """Distancia aproximada (proyección equirrectangular): basta para separar puntos a
    decenas de metros; las distancias del modelo las mide PostGIS."""
    mean_latitude = math.radians((a.latitude + b.latitude) / 2)
    x = math.radians(b.longitude - a.longitude) * math.cos(mean_latitude)
    y = math.radians(b.latitude - a.latitude)
    return math.hypot(x, y) * _EARTH_RADIUS_M


class _Selection:
    """Acepta candidatos en orden, sin repetir vía ni acercarse a otro punto aceptado."""

    def __init__(self, area: BoundingBox) -> None:
        self._area = area
        self._road_ids: set[int] = set()
        self.locations: list[GeoPoint] = []

    def take(self, candidates: Iterable[tuple[int | None, GeoPoint]], count: int) -> None:
        taken = 0
        for road_id, location in candidates:
            if taken == count:
                return
            if road_id in self._road_ids or not self._area.contains(location):
                continue
            if any(_distance_m(location, other) <= MIN_SEPARATION_M for other in self.locations):
                continue
            if road_id is not None:
                self._road_ids.add(road_id)
            self.locations.append(location)
            taken += 1


class PostgisDemoPointPicker:
    """Implementa ``DemoPointSource``.

    Reparte los puntos por jerarquía vial (punto medio de cada vía), añade dos frente a
    servicios críticos (P = 10) y dos lejos de toda vía («Revisar vía»). Las severidades
    van en ciclo baja → media → alta.
    """

    def __init__(self, session: Session) -> None:
        self._session = session

    def pick(self, area: BoundingBox) -> Sequence[DemoPoint]:
        selection = _Selection(area)
        for road_class, quota in DEMO_ROAD_QUOTAS.items():
            selection.take(self._road_midpoints(area, road_class, quota), quota)
        selection.take(self._near_services(area), DEMO_NEAR_SERVICE_COUNT)
        selection.take(self._off_road(area), DEMO_OFF_ROAD_COUNT)
        return [
            DemoPoint(location, _SEVERITY_CYCLE[position % len(_SEVERITY_CYCLE)])
            for position, location in enumerate(selection.locations)
        ]

    def _road_midpoints(
        self, area: BoundingBox, road_class: RoadClass, quota: int
    ) -> list[tuple[int | None, GeoPoint]]:
        rows = self._session.execute(
            _ROAD_MIDPOINTS,
            _envelope(area)
            | {"road_class": road_class.value, "limit": quota * CANDIDATES_PER_SLOT},
        )
        return [(row.id_via, GeoPoint(longitude=row.lon, latitude=row.lat)) for row in rows]

    def _near_services(self, area: BoundingBox) -> list[tuple[int | None, GeoPoint]]:
        rows = self._session.execute(
            _POINTS_NEAR_SERVICES,
            _envelope(area)
            | {
                "radio_m": NEAR_SERVICE_ROAD_RADIUS_M,
                "limit": DEMO_NEAR_SERVICE_COUNT * CANDIDATES_PER_SLOT,
            },
        )
        return [(row.id_via, GeoPoint(longitude=row.lon, latitude=row.lat)) for row in rows]

    def _off_road(self, area: BoundingBox) -> list[tuple[int | None, GeoPoint]]:
        rows = self._session.execute(
            _POINTS_OFF_ROAD,
            _envelope(area)
            | {
                "side": OFF_ROAD_GRID_SIDE,
                "min_distance_m": OFF_ROAD_MIN_DISTANCE_M,
                "limit": DEMO_OFF_ROAD_COUNT * CANDIDATES_PER_SLOT,
            },
        )
        return [(None, GeoPoint(longitude=row.lon, latitude=row.lat)) for row in rows]


def _envelope(area: BoundingBox) -> dict[str, object]:
    return {"west": area.west, "south": area.south, "east": area.east, "north": area.north}
