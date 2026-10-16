import uuid

from sqlalchemy import update
from sqlalchemy.orm import Session

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
