from collections.abc import Sequence
from typing import Final

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.modules.reports.domain.duplicates import DuplicateCandidate
from app.modules.reports.domain.severity import Severity
from app.modules.reports.domain.status import ReportStatus
from app.shared.domain.geo import GeoPoint

# ST_DWithin filtra con el índice ix_reporte_ubicacion_geog (ADR 0003); ST_Distance solo
# da el valor y ordena. id_reporte desempata para que el resultado sea determinista.
_ACTIVE_WITHIN = text(
    """
    WITH punto AS (
        SELECT ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography AS geog
    )
    SELECT r.id_reporte, r.estado, r.severidad, r.id_via, v.nombre AS nombre_via,
           r.fecha_creacion,
           ST_Distance(r.ubicacion::geography, punto.geog) AS distancia_m,
           (SELECT count(*) FROM confirmacion AS c
            WHERE c.id_reporte = r.id_reporte) AS confirmaciones
    FROM reporte AS r
    CROSS JOIN punto
    LEFT JOIN via AS v ON v.id_via = r.id_via
    WHERE r.estado <> CAST(:reparado AS estado_reporte)
      AND ST_DWithin(r.ubicacion::geography, punto.geog, :radio_m)
    ORDER BY distancia_m, r.id_reporte
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
                "limite": limit,
            },
        ).all()
        return [
            DuplicateCandidate(
                id=row.id_reporte,
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
