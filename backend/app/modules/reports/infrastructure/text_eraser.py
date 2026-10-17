import uuid

from sqlalchemy import update
from sqlalchemy.orm import Session

from app.modules.reports.infrastructure.models import ReportModel


class SqlReportTextEraser:
    """Implementa ``ReportTextEraser``: deja en NULL la descripción de los reportes del titular."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def clear_descriptions(self, user_id: uuid.UUID) -> None:
        self._session.execute(
            update(ReportModel)
            .where(ReportModel.user_id == user_id, ReportModel.description.is_not(None))
            .values(description=None)
        )
