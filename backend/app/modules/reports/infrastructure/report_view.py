import uuid
from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.modules.confirmations.infrastructure.models import ConfirmationModel
from app.modules.reports.domain.entities import ReportDetails
from app.modules.reports.domain.my_reports import PublicReportView
from app.modules.reports.domain.public_location import PUBLIC_GRID_DEGREES
from app.modules.reports.domain.report_view import StatusHistoryEntry
from app.modules.reports.domain.severity import Severity
from app.modules.reports.domain.status import ReportStatus
from app.modules.reports.infrastructure.models import StatusHistoryModel
from app.modules.reports.infrastructure.repository import SqlReportRepository
from app.shared.domain.geo import GeoPoint

_PUBLIC_VIEW = text(
    """
    SELECT r.id_reporte, r.estado, r.severidad, r.id_via, v.nombre AS nombre_via,
           r.fecha_creacion,
           ST_X(ST_SnapToGrid(r.ubicacion, :rejilla)) AS lon_publica,
           ST_Y(ST_SnapToGrid(r.ubicacion, :rejilla)) AS lat_publica,
           (SELECT count(*) FROM confirmacion AS cf
            WHERE cf.id_reporte = r.id_reporte) AS confirmaciones
    FROM reporte AS r
    LEFT JOIN via AS v ON v.id_via = r.id_via
    WHERE r.id_reporte = :reporte
    """
)


class SqlReportViewReader:
    """Implementa ``ReportViewReader`` con consultas parametrizadas."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_details(self, report_id: uuid.UUID) -> ReportDetails | None:
        return SqlReportRepository(self._session).get_details(report_id)

    def public_view(self, report_id: uuid.UUID) -> PublicReportView | None:
        row = self._session.execute(
            _PUBLIC_VIEW, {"reporte": report_id, "rejilla": PUBLIC_GRID_DEGREES}
        ).one_or_none()
        if row is None:
            return None
        return PublicReportView(
            id=row.id_reporte,
            location=GeoPoint(longitude=row.lon_publica, latitude=row.lat_publica),
            status=ReportStatus(row.estado),
            severity=Severity(row.severidad),
            confirmations=int(row.confirmaciones),
            road_id=row.id_via,
            road_name=row.nombre_via,
            created_at=row.fecha_creacion,
        )

    def confirmed_at(self, report_id: uuid.UUID, user_id: uuid.UUID) -> datetime | None:
        return self._session.execute(
            select(ConfirmationModel.confirmed_at).where(
                ConfirmationModel.report_id == report_id, ConfirmationModel.user_id == user_id
            )
        ).scalar_one_or_none()

    def confirmations(self, report_id: uuid.UUID) -> int:
        return self._session.execute(
            select(func.count()).where(ConfirmationModel.report_id == report_id)
        ).scalar_one()

    def history(self, report_id: uuid.UUID) -> Sequence[StatusHistoryEntry]:
        rows = self._session.execute(
            select(
                StatusHistoryModel.new_status,
                StatusHistoryModel.changed_at,
                StatusHistoryModel.note,
            )
            .where(StatusHistoryModel.report_id == report_id)
            .order_by(StatusHistoryModel.changed_at, StatusHistoryModel.id)
        ).all()
        return [
            StatusHistoryEntry(
                status=ReportStatus(row.new_status), changed_at=row.changed_at, note=row.note
            )
            for row in rows
        ]
