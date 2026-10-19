"""Armado del caso de uso de confirmaciones para cada petición."""

from datetime import timedelta
from typing import Annotated

from fastapi import Depends

from app.core.dependencies import SessionDep, SettingsDep
from app.core.rate_limiting import RateLimiterDep
from app.modules.confirmations.application.confirm_report import ConfirmReport
from app.modules.confirmations.infrastructure.repository import SqlConfirmationRepository
from app.shared.application.clock import SystemClock
from app.shared.application.rate_limit import RateLimit


def get_confirm_report(
    session: SessionDep, settings: SettingsDep, limiter: RateLimiterDep
) -> ConfirmReport:
    return ConfirmReport(
        confirmations=SqlConfirmationRepository(session),
        rate_limiter=limiter,
        # Mismo valor que crear reportes y nearby, con cuenta aparte.
        limit_per_user=RateLimit(
            max_requests=settings.reports_per_user_per_hour, window=timedelta(hours=1)
        ),
        clock=SystemClock(),
        transaction=session,
    )


ConfirmReportDep = Annotated[ConfirmReport, Depends(get_confirm_report)]
