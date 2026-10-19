"""Caso de uso: confirmar un reporte existente en lugar de crear otro (HU-16, guía 2.5).

Las confirmaciones no cambian la urgencia U: solo aportan evidencia y desempate (guía 2.2).
"""

import uuid

from app.modules.confirmations.domain.errors import (
    OwnReportConfirmationError,
    ReportNotActiveError,
    ReportNotFoundError,
)
from app.modules.confirmations.domain.ports import ConfirmationRepository
from app.modules.reports.domain.status import ReportStatus
from app.shared.application.clock import Clock
from app.shared.application.rate_limit import RateLimit, RateLimiter
from app.shared.application.transaction import TransactionManager


class ConfirmReport:
    def __init__(
        self,
        confirmations: ConfirmationRepository,
        rate_limiter: RateLimiter,
        limit_per_user: RateLimit,
        clock: Clock,
        transaction: TransactionManager,
    ) -> None:
        self._confirmations = confirmations
        self._rate_limiter = rate_limiter
        self._limit_per_user = limit_per_user
        self._clock = clock
        self._transaction = transaction

    def execute(self, report_id: uuid.UUID, user_id: uuid.UUID) -> int:
        """Confirma el reporte y devuelve cuántas confirmaciones tiene ahora."""
        # El cupo va primero: que no sirva para sondear qué identificadores existen.
        self._rate_limiter.hit(f"confirm:user:{user_id}", self._limit_per_user, self._clock.now())
        target = self._confirmations.find_target(report_id)
        if target is None:
            raise ReportNotFoundError(str(report_id))
        if target.status is ReportStatus.REPAIRED:
            raise ReportNotActiveError(str(report_id))
        if target.owner_id == user_id:
            raise OwnReportConfirmationError(str(report_id))
        try:
            self._confirmations.add(report_id, user_id)
            self._transaction.commit()
        except Exception:
            self._transaction.rollback()
            raise
        return self._confirmations.count(report_id)
