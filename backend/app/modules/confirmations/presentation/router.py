"""Ruta de confirmaciones: /api/v1/reports/{id}/confirmations (HU-16)."""

import uuid
from typing import Any

from fastapi import APIRouter, Depends, status

from app.core.errors import AppError
from app.core.rate_limiting import too_many_requests
from app.modules.auth.presentation.dependencies import CurrentUserDep, forbid_evaluator
from app.modules.confirmations.domain.errors import (
    AlreadyConfirmedError,
    ConfirmationTooFarError,
    OwnReportConfirmationError,
    ReportNotActiveError,
    ReportNotFoundError,
)
from app.modules.confirmations.presentation.dependencies import ConfirmReportDep
from app.modules.confirmations.presentation.schemas import (
    ConfirmationRequest,
    ConfirmationResponse,
)
from app.shared.application.rate_limit import RateLimitExceededError
from app.shared.domain.geo import GeoPoint
from app.shared.domain.geo_parameters import CONFIRMATION_RADIUS_M

router = APIRouter(prefix="/reports", tags=["confirmaciones"])

_DOC: dict[int | str, dict[str, Any]] = {
    status.HTTP_403_FORBIDDEN: {
        "description": "Quien confirma está a más de 50 m del daño (CONFIRMATION_TOO_FAR) o es "
        "una cuenta de evaluador (EVALUATOR_CANNOT_REPORT)"
    },
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
    dependencies=[Depends(forbid_evaluator)],
    responses=_DOC,
)
def confirm_report(
    report_id: uuid.UUID,
    body: ConfirmationRequest,
    user: CurrentUserDep,
    use_case: ConfirmReportDep,
) -> ConfirmationResponse:
    """Confirma un reporte activo de otro ciudadano, en lugar de crear uno repetido.

    Pide la ubicación actual de quien confirma: solo se acepta a 50 m o menos del daño
    (propuesta 112). No cambia la urgencia U; cuenta como evidencia y para el desempate
    (guía 2.2).
    """
    location = GeoPoint(longitude=body.longitude, latitude=body.latitude)
    try:
        total = use_case.execute(report_id, user.id, location, body.duplicate_warning_id)
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
    except ConfirmationTooFarError as exc:
        # Sin la distancia exacta: con ella se podría ubicar el reporte con más precisión
        # que la vista pública (propuesta 43).
        raise AppError(
            "CONFIRMATION_TOO_FAR",
            "Para confirmar este daño tienes que estar cerca de él. Acércate y vuelve a "
            "intentarlo.",
            status.HTTP_403_FORBIDDEN,
            details={"max_distance_m": CONFIRMATION_RADIUS_M},
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
