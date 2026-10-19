import uuid
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.modules.reports.domain.entities import ReportDetails
from app.modules.reports.domain.my_reports import (
    ConfirmedReport,
    MyReportsPage,
    OwnReport,
    PublicReportView,
)
from app.modules.reports.domain.public_location import PUBLIC_GRID_DEGREES
from app.modules.reports.domain.severity import Severity
from app.modules.reports.domain.status import ReportStatus
from app.shared.domain.geo import GeoPoint

# Una fila por relación del usuario con un reporte: lo creó (fecha de creación) o lo
# confirmó (fecha de la confirmación). Por la propuesta 48 no puede tener las dos. Las dos
# consultas repiten el mismo WITH a propósito: SQL literal, sin concatenar texto.
_PAGE = text(
    """
    WITH relacionados AS (
        SELECT r.id_reporte, 'own' AS relacion, r.fecha_creacion AS fecha_relacion
        FROM reporte AS r WHERE r.id_usuario = :usuario
        UNION ALL
        SELECT cf.id_reporte, 'confirmed', cf.fecha
        FROM confirmacion AS cf WHERE cf.id_usuario = :usuario
    )
    SELECT rel.relacion, rel.fecha_relacion, r.id_reporte, r.id_usuario,
           ST_X(r.ubicacion) AS lon, ST_Y(r.ubicacion) AS lat,
           ST_X(ST_SnapToGrid(r.ubicacion, :rejilla)) AS lon_publica,
           ST_Y(ST_SnapToGrid(r.ubicacion, :rejilla)) AS lat_publica,
           r.severidad, r.descripcion, r.estado, r.puntaje_prioridad, r.id_via,
           v.nombre AS nombre_via, r.fecha_creacion,
           (SELECT count(*) FROM confirmacion AS cf
            WHERE cf.id_reporte = r.id_reporte) AS confirmaciones
    FROM relacionados AS rel
    JOIN reporte AS r ON r.id_reporte = rel.id_reporte
    LEFT JOIN via AS v ON v.id_via = r.id_via
    ORDER BY rel.fecha_relacion DESC, r.id_reporte
    LIMIT :limite OFFSET :desplazamiento
    """
)

_TOTAL = text(
    """
    SELECT (SELECT count(*) FROM reporte WHERE id_usuario = :usuario)
         + (SELECT count(*) FROM confirmacion WHERE id_usuario = :usuario)
    """
)


class SqlMyReportsReader:
    """Implementa ``MyReportsReader`` con dos consultas parametrizadas (página y total)."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def list_for_user(self, user_id: uuid.UUID, limit: int, offset: int) -> MyReportsPage:
        rows = self._session.execute(
            _PAGE,
            {
                "usuario": user_id,
                "rejilla": PUBLIC_GRID_DEGREES,
                "limite": limit,
                "desplazamiento": offset,
            },
        ).all()
        total = self._session.execute(_TOTAL, {"usuario": user_id}).scalar_one()
        return MyReportsPage(
            items=[_item(row) for row in rows], total=int(total), limit=limit, offset=offset
        )


def _item(row: Any) -> OwnReport | ConfirmedReport:
    confirmations = int(row.confirmaciones)
    if row.relacion == "own":
        return OwnReport(
            details=ReportDetails(
                id=row.id_reporte,
                user_id=row.id_usuario,
                location=GeoPoint(longitude=row.lon, latitude=row.lat),
                severity=Severity(row.severidad),
                description=row.descripcion,
                status=ReportStatus(row.estado),
                priority_score=row.puntaje_prioridad,
                road_id=row.id_via,
                road_name=row.nombre_via,
                created_at=row.fecha_creacion,
            ),
            confirmations=confirmations,
        )
    return ConfirmedReport(
        public=PublicReportView(
            id=row.id_reporte,
            location=GeoPoint(longitude=row.lon_publica, latitude=row.lat_publica),
            status=ReportStatus(row.estado),
            severity=Severity(row.severidad),
            confirmations=confirmations,
            road_id=row.id_via,
            road_name=row.nombre_via,
            created_at=row.fecha_creacion,
        ),
        confirmed_at=row.fecha_relacion,
    )
