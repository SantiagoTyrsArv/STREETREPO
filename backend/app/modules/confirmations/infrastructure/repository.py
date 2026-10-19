import uuid

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modules.confirmations.domain.errors import AlreadyConfirmedError
from app.modules.confirmations.domain.ports import ConfirmationTarget
from app.modules.confirmations.infrastructure.models import ConfirmationModel
from app.modules.reports.domain.status import ReportStatus
from app.modules.reports.infrastructure.models import ReportModel

UNIQUE_CONFIRMATION_CONSTRAINT = "uq_confirmacion_reporte_usuario"


def _violated_constraint(exc: IntegrityError) -> str | None:
    diag = getattr(exc.orig, "diag", None)
    name = getattr(diag, "constraint_name", None)
    return name if isinstance(name, str) else None


class SqlConfirmationRepository:
    """Implementa ``ConfirmationRepository``. No confirma: lo hace el caso de uso."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def find_target(self, report_id: uuid.UUID) -> ConfirmationTarget | None:
        row = self._session.execute(
            select(ReportModel.user_id, ReportModel.status).where(ReportModel.id == report_id)
        ).one_or_none()
        if row is None:
            return None
        return ConfirmationTarget(owner_id=row.user_id, status=ReportStatus(row.status))

    def add(self, report_id: uuid.UUID, user_id: uuid.UUID) -> None:
        self._session.add(ConfirmationModel(report_id=report_id, user_id=user_id))
        try:
            self._session.flush()
        except IntegrityError as exc:
            if _violated_constraint(exc) == UNIQUE_CONFIRMATION_CONSTRAINT:
                raise AlreadyConfirmedError(str(report_id)) from exc
            raise

    def count(self, report_id: uuid.UUID) -> int:
        return self._session.execute(
            select(func.count()).where(ConfirmationModel.report_id == report_id)
        ).scalar_one()
