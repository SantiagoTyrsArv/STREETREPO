from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.modules.roads.domain.entities import RoadMatch
from app.modules.roads.domain.road_class import RoadClass
from app.shared.domain.geo import GeoPoint

# ST_DWithin filtra con el índice ix_via_geom_geog; ST_Distance solo ordena los
# candidatos (guía 5). id_via desempata para que el resultado sea determinista.
_NEAREST_ROAD = text(
    """
    WITH punto AS (
        SELECT ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography AS geog
    )
    SELECT v.id_via, v.nombre, v.jerarquia_vial, v.factor_flujo,
           ST_Distance(v.geom::geography, punto.geog) AS distancia_m
    FROM via AS v, punto
    WHERE ST_DWithin(v.geom::geography, punto.geog, :radio_m)
    ORDER BY distancia_m, v.id_via
    LIMIT 1
    """
)


class PostgisRoadMatcher:
    """Implementa ``RoadMatcher``: asocia un punto a la vía OSM más cercana."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def find_nearest(self, point: GeoPoint, max_distance_m: float) -> RoadMatch | None:
        row = self._session.execute(
            _NEAREST_ROAD,
            {"lon": point.longitude, "lat": point.latitude, "radio_m": max_distance_m},
        ).one_or_none()
        if row is None:
            return None
        return RoadMatch(
            road_id=row.id_via,
            name=row.nombre,
            road_class=RoadClass(row.jerarquia_vial),
            flow_factor=Decimal(row.factor_flujo),
            distance_m=float(row.distancia_m),
        )
