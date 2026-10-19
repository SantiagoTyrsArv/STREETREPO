"""Ruta de confirmaciones: /api/v1/reports/{id}/confirmations (HU-16)."""

import uuid
from typing import Any

from fastapi import APIRouter, status

from app.core.errors import AppError
from app.core.rate_limiting import too_many_requests
from app.modules.auth.presentation.dependencies import CurrentUserDep
from app.modules.confirmations.domain.errors import (
    AlreadyConfirmedError,
    OwnReportConfirmationError,
    ReportNotActiveError,
    ReportNotFoundError,
)
from app.modules.confirmations.presentation.dependencies import ConfirmReportDep
from app.modules.confirmations.presentation.schemas import ConfirmationResponse
from app.shared.application.rate_limit import RateLimitExceededError

router = APIRouter(prefix="/reports", tags=["confirmaciones"])

_DOC: dict[int | str, dict[str, Any]] = {
    status.HTTP_404_NOT_FOUND: {"description": "El reporte no existe (REPORT_NOT_FOUND)"},
    status.HTTP_409_CONFLICT: {
        "description": "Reparado (REPORT_NOT_ACTIVE), propio (CONFIRMATION_OWN_REPORT) o ya "
        "confirmado (CONFIRMATION_ALREADY_EXISTS)"
    },
    status.HTTP_429_TOO_MANY_REQUESTS: {
        "description": "Demasiadas confirmaciones; ver Retry-After"
    },
}


@router.post(
    "/{report_id}/confirmations",
    response_model=ConfirmationResponse,
    status_code=status.HTTP_201_CREATED,
    responses=_DOC,
)
def confirm_report(
    report_id: uuid.UUID, user: CurrentUserDep, use_case: ConfirmReportDep
) -> ConfirmationResponse:
    """Confirma un reporte activo de otro ciudadano, en lugar de crear uno repetido.

    No cambia la urgencia U; cuenta como evidencia y para el desempate (guía 2.2).
    """
    try:
        total = use_case.execute(report_id, user.id)
    except ReportNotFoundError as exc:
        raise AppError(
            "REPORT_NOT_FOUND", "No encontramos ese reporte.", status.HTTP_404_NOT_FOUND
        ) from exc
    except ReportNotActiveError as exc:
        raise AppError(
            "REPORT_NOT_ACTIVE",
            "Este reporte ya fue reparado; no necesita más confirmaciones.",
            status.HTTP_409_CONFLICT,
        ) from exc
    except OwnReportConfirmationError as exc:
        raise AppError(
            "CONFIRMATION_OWN_REPORT",
            "No puedes confirmar tu propio reporte.",
            status.HTTP_409_CONFLICT,
        ) from exc
    except AlreadyConfirmedError as exc:
        raise AppError(
            "CONFIRMATION_ALREADY_EXISTS", "Ya confirmaste este reporte.", status.HTTP_409_CONFLICT
        ) from exc
    except RateLimitExceededError as exc:
        raise too_many_requests(
            "CONFIRMATION_RATE_LIMITED",
            "Hiciste muchas confirmaciones en poco tiempo. Intenta de nuevo más tarde.",
            exc.retry_after,
        ) from exc
    return ConfirmationResponse(report_id=report_id, confirmations=total)
