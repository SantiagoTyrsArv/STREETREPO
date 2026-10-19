from collections.abc import Sequence
from typing import Final

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.modules.reports.domain.duplicates import DuplicateCandidate
from app.modules.reports.domain.public_location import PUBLIC_GRID_DEGREES
from app.modules.reports.domain.severity import Severity
from app.modules.reports.domain.status import ReportStatus
from app.shared.domain.geo import GeoPoint

# ST_DWithin filtra con la ubicación exacta y el índice ix_reporte_ubicacion_geog
# (ADR 0003). Lo que se devuelve es público (propuesta 43): la ubicación ajustada a la
# cuadrícula y la distancia medida desde ella. id_reporte desempata para que el
# resultado sea determinista.
_ACTIVE_WITHIN = text(
    """
    WITH punto AS (
        SELECT ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography AS geog
    ),
    cercanos AS (
        SELECT r.id_reporte, r.estado, r.severidad, r.id_via, r.fecha_creacion,
               ST_SnapToGrid(r.ubicacion, :rejilla) AS publica
        FROM reporte AS r, punto
        WHERE r.estado <> CAST(:reparado AS estado_reporte)
          AND ST_DWithin(r.ubicacion::geography, punto.geog, :radio_m)
    )
    SELECT c.id_reporte, c.estado, c.severidad, c.id_via, v.nombre AS nombre_via,
           c.fecha_creacion, ST_X(c.publica) AS lon_publica, ST_Y(c.publica) AS lat_publica,
           ST_Distance(c.publica::geography, punto.geog) AS distancia_m,
           (SELECT count(*) FROM confirmacion AS cf
            WHERE cf.id_reporte = c.id_reporte) AS confirmaciones
    FROM cercanos AS c
    CROSS JOIN punto
    LEFT JOIN via AS v ON v.id_via = c.id_via
    ORDER BY distancia_m, c.id_reporte
    LIMIT :limite
    """
)

# Clave del candado de transacción de PostgreSQL para crear reportes; cualquier número
# fijo sirve mientras ninguna otra parte del sistema use el mismo.
REPORT_CREATION_LOCK_KEY: Final = 5_250_001


class PostgisNearbyReportFinder:
    """Implementa ``NearbyReportFinder`` con PostGIS local (guía 2.5)."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def find_active_within(
        self, point: GeoPoint, radius_m: float, limit: int
    ) -> Sequence[DuplicateCandidate]:
        rows = self._session.execute(
            _ACTIVE_WITHIN,
            {
                "lon": point.longitude,
                "lat": point.latitude,
                "radio_m": radius_m,
                "reparado": ReportStatus.REPAIRED.value,
                "rejilla": PUBLIC_GRID_DEGREES,
                "limite": limit,
            },
        ).all()
        return [
            DuplicateCandidate(
                id=row.id_reporte,
                location=GeoPoint(longitude=row.lon_publica, latitude=row.lat_publica),
                distance_m=float(row.distancia_m),
                status=ReportStatus(row.estado),
                severity=Severity(row.severidad),
                confirmations=int(row.confirmaciones),
                road_id=row.id_via,
                road_name=row.nombre_via,
                created_at=row.fecha_creacion,
            )
            for row in rows
        ]


class PostgresReportCreationLock:
    """Implementa ``ReportCreationLock`` con ``pg_advisory_xact_lock``.

    Se libera solo al confirmar o revertir. Serializa la creación de reportes: el
    candado dura unos milisegundos (la foto ya está procesada), y a la escala del MVP
    es más simple y seguro que bloquear por zona.
    """

    def __init__(self, session: Session) -> None:
        self._session = session

    def acquire(self) -> None:
        self._session.execute(
            text("SELECT pg_advisory_xact_lock(:key)"), {"key": REPORT_CREATION_LOCK_KEY}
        )
