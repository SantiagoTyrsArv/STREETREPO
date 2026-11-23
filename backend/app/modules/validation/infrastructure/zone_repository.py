"""Zonas de validación en PostGIS (consultas parametrizadas)."""

import json
from collections.abc import Sequence
from typing import Final

from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from app.modules.reports.domain.status import ReportStatus
from app.modules.validation.domain.ports import ZoneSummary
from app.modules.validation.domain.zones import Concentration, InvalidZonesError, ZoneDefinition

# ~5 m en grados: aligera el polígono para el mapa del panel sin alterar su forma visible.
SIMPLIFY_TOLERANCE_DEG: Final = 0.00005

_UPSERT = text(
    """
    INSERT INTO zona (nombre, concentracion, geom)
    VALUES (:name, CAST(:concentration AS concentracion_zona),
            ST_SetSRID(ST_GeomFromGeoJSON(CAST(:geometry AS text)), 4326))
    ON CONFLICT (nombre) DO UPDATE
       SET concentracion = EXCLUDED.concentracion, geom = EXCLUDED.geom
    """
)
_INVALID = text("SELECT nombre FROM zona WHERE nombre = ANY(:names) AND NOT ST_IsValid(geom)")
# Se solapan si sus interiores se cortan; compartir solo el borde está permitido.
_OVERLAPPING = text(
    """
    SELECT a.nombre AS first_name, b.nombre AS second_name
    FROM zona a JOIN zona b ON a.id_zona < b.id_zona
    WHERE ST_Intersects(a.geom, b.geom) AND NOT ST_Touches(a.geom, b.geom)
    ORDER BY a.nombre, b.nombre LIMIT 1
    """
)
_ASSIGN = text(
    """
    UPDATE reporte SET id_zona = (
        SELECT z.id_zona FROM zona z WHERE ST_Covers(z.geom, reporte.ubicacion)
        ORDER BY z.id_zona LIMIT 1
    )
    """
)
_ASSIGNED = text("SELECT count(*) FROM reporte WHERE id_zona IS NOT NULL")
_LIST = text(
    """
    SELECT z.id_zona, z.nombre, CAST(z.concentracion AS text) AS concentracion,
           count(r.id_reporte) FILTER (
               WHERE r.estado <> CAST(:repaired AS estado_reporte)) AS activos,
           count(r.id_reporte) AS total,
           ST_AsGeoJSON(ST_SimplifyPreserveTopology(z.geom, :tolerance)) AS geometry
    FROM zona z LEFT JOIN reporte r ON r.id_zona = z.id_zona
    GROUP BY z.id_zona, z.nombre, z.concentracion, z.geom
    ORDER BY z.nombre
    """
)


class SqlZoneRepository:
    """Implementa ``ZoneRepository``. No confirma: lo hace el caso de uso."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def upsert(self, zones: Sequence[ZoneDefinition]) -> None:
        for zone in zones:
            try:
                self._session.execute(
                    _UPSERT,
                    {
                        "name": zone.name,
                        "concentration": zone.concentration.value,
                        "geometry": json.dumps(zone.polygon_geojson),
                    },
                )
            except DBAPIError as exc:
                raise InvalidZonesError(
                    f"La geometría de la zona «{zone.name}» no se pudo leer como polígono."
                ) from exc
        invalid = self._session.execute(_INVALID, {"names": [z.name for z in zones]}).scalars()
        for name in invalid:
            raise InvalidZonesError(f"La zona «{name}» no es un polígono válido (se cruza).")
        overlap = self._session.execute(_OVERLAPPING).first()
        if overlap is not None:
            raise InvalidZonesError(
                f"Las zonas «{overlap.first_name}» y «{overlap.second_name}» se solapan."
            )

    def assign_reports(self) -> int:
        self._session.execute(_ASSIGN)
        return int(self._session.execute(_ASSIGNED).scalar_one())

    def list_with_counts(self) -> list[ZoneSummary]:
        rows = self._session.execute(
            _LIST, {"repaired": ReportStatus.REPAIRED.value, "tolerance": SIMPLIFY_TOLERANCE_DEG}
        )
        return [
            ZoneSummary(
                id=row.id_zona,
                name=row.nombre,
                concentration=Concentration(row.concentracion),
                active_reports=row.activos,
                total_reports=row.total,
                geometry_geojson=json.loads(row.geometry),
            )
            for row in rows
        ]
