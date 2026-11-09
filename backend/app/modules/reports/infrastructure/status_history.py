import uuid

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.modules.reports.domain.status import ReportStatus
from app.modules.reports.domain.status_machine import StatusChange
from app.modules.reports.infrastructure.models import ReportModel, StatusHistoryModel


class SqlStatusHistoryRecorder:
    """Implementa ``StatusHistoryRecorder``: estado y historial en la misma transacción."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def apply(self, report_id: uuid.UUID, change: StatusChange) -> None:
        self._session.execute(
            update(ReportModel).where(ReportModel.id == report_id).values(status=change.new)
        )
        self._session.add(
            StatusHistoryModel(
                report_id=report_id,
                user_id=change.changed_by,
                previous_status=change.previous,
                new_status=change.new,
                note=change.note,
            )
        )
        self._session.flush()


class SqlReportStatusLock:
    """Implementa ``ReportStatusLock`` con ``SELECT … FOR UPDATE``."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def lock_status(self, report_id: uuid.UUID) -> ReportStatus | None:
        return self._session.execute(
            select(ReportModel.status).where(ReportModel.id == report_id).with_for_update()
        ).scalar_one_or_none()
