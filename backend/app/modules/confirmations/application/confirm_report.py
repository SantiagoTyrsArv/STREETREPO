"""Caso de uso: confirmar un reporte existente en lugar de crear otro (HU-16, guía 2.5).

Las confirmaciones no cambian la urgencia U: solo aportan evidencia y desempate (guía 2.2).
Solo se aceptan desde ``CONFIRMATION_RADIUS_M`` del daño (propuesta 112): una confirmación
desde otro lugar no prueba que el daño exista. El GPS se puede falsear, así que esto encarece
el abuso, no lo impide.
"""

import uuid

from app.modules.confirmations.domain.errors import (
    ConfirmationTooFarError,
    OwnReportConfirmationError,
    ReportNotActiveError,
    ReportNotFoundError,
)
from app.modules.confirmations.domain.ports import ConfirmationRepository
from app.modules.reports.domain.ports import DuplicateWarningRecorder
from app.modules.reports.domain.status import ReportStatus
from app.shared.application.clock import Clock
from app.shared.application.rate_limit import RateLimit, RateLimiter
from app.shared.application.transaction import TransactionManager
from app.shared.domain.geo import GeoPoint
from app.shared.domain.geo_parameters import CONFIRMATION_RADIUS_M


class ConfirmReport:
    def __init__(
        self,
        *,
        confirmations: ConfirmationRepository,
        rate_limiter: RateLimiter,
        limit_per_user: RateLimit,
        clock: Clock,
        transaction: TransactionManager,
        warnings: DuplicateWarningRecorder,
    ) -> None:
        self._confirmations = confirmations
        self._rate_limiter = rate_limiter
        self._limit_per_user = limit_per_user
        self._clock = clock
        self._transaction = transaction
        self._warnings = warnings

    def execute(
        self,
        report_id: uuid.UUID,
        user_id: uuid.UUID,
        location: GeoPoint,
        duplicate_warning_id: uuid.UUID | None = None,
    ) -> int:
        """Confirma el reporte y devuelve cuántas confirmaciones tiene ahora.

        Si llega ``duplicate_warning_id`` (se confirmó desde «Posible duplicado»), el aviso
        queda «confirmo» en la misma transacción; uno que no aplica no la impide.
        """
        # El cupo va primero: que no sirva para sondear qué identificadores existen.
        self._rate_limiter.hit(f"confirm:user:{user_id}", self._limit_per_user, self._clock.now())
        target = self._confirmations.find_target(report_id, location)
        if target is None:
            raise ReportNotFoundError(str(report_id))
        if target.status is ReportStatus.REPAIRED:
            raise ReportNotActiveError(str(report_id))
        if target.owner_id == user_id:
            raise OwnReportConfirmationError(str(report_id))
        if target.distance_m > CONFIRMATION_RADIUS_M:
            raise ConfirmationTooFarError(str(report_id))
        try:
            self._confirmations.add(report_id, user_id, target.distance_m)
            if duplicate_warning_id is not None:
                self._warnings.resolve(duplicate_warning_id, user_id, "confirmo", report_id)
            self._transaction.commit()
        except Exception:
            self._transaction.rollback()
            raise
        return self._confirmations.count(report_id)
