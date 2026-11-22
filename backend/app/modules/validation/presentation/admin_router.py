"""Rutas administrativas del estudio de validación: /api/v1/admin/... (objetivo 4).

Exigen el rol de administrador en el servidor (guía 7.1); los evaluadores no entran.
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.core.errors import AppError
from app.modules.auth.presentation.dependencies import AdminUserDep, require_admin
from app.modules.priority.application.evaluate_report import WeightsNotConfiguredError
from app.modules.validation.domain.parameters import MIN_REPORTS_PER_ZONE
from app.modules.validation.domain.rounds import (
    NoZonesError,
    RoundAlreadyClosedError,
    RoundAlreadyOpenError,
    RoundNotFoundError,
    ZoneTooSmallError,
)
from app.modules.validation.presentation.dependencies import (
    CloseRoundDep,
    ListZonesDep,
    OpenRoundDep,
    ReadRoundsDep,
)
from app.modules.validation.presentation.schemas import (
    OpenRoundRequest,
    RoundCreatedResponse,
    RoundProgressResponse,
    RoundsResponse,
    RoundSummaryResponse,
    ZonesResponse,
)

DEFAULT_ROUNDS_PAGE: int = 20
MAX_ROUNDS_PAGE: int = 50

router = APIRouter(prefix="/admin", tags=["validación"], dependencies=[Depends(require_admin)])


def _not_found() -> AppError:
    return AppError(
        "EVALUATION_ROUND_NOT_FOUND", "La ronda de evaluación no existe.", status.HTTP_404_NOT_FOUND
    )


@router.get("/zones", response_model=ZonesResponse)
def list_zones(use_case: ListZonesDep) -> ZonesResponse:
    """Zonas del piloto con sus reportes activos (todo salvo Reparado) y totales."""
    return ZonesResponse.from_summaries(use_case.execute())


@router.post(
    "/evaluation-rounds",
    status_code=status.HTTP_201_CREATED,
    response_model=RoundCreatedResponse,
    responses={
        409: {"description": "Ya hay una ronda abierta (EVALUATION_ROUND_ALREADY_OPEN)"},
        422: {
            "description": "Sin zonas (EVALUATION_NO_ZONES), una zona con pocos reportes "
            "(EVALUATION_ZONE_TOO_SMALL) o pesos sin configurar (WEIGHTS_NOT_CONFIGURED)"
        },
    },
)
def open_round(
    body: OpenRoundRequest, admin: AdminUserDep, use_case: OpenRoundDep
) -> RoundCreatedResponse:
    """Congela la muestra de reportes activos de cada zona con su U y el orden del motor."""
    try:
        round_id = use_case.execute(body.name, body.sample_size, admin.id)
    except RoundAlreadyOpenError as exc:
        raise AppError(
            "EVALUATION_ROUND_ALREADY_OPEN",
            "Ya hay una ronda de evaluación abierta. Ciérrala antes de abrir otra.",
            status.HTTP_409_CONFLICT,
        ) from exc
    except NoZonesError as exc:
        raise AppError(
            "EVALUATION_NO_ZONES",
            "No hay zonas de validación cargadas.",
            status.HTTP_422_UNPROCESSABLE_CONTENT,
        ) from exc
    except ZoneTooSmallError as exc:
        raise AppError(
            "EVALUATION_ZONE_TOO_SMALL",
            f"La zona «{exc.zone_name}» tiene {exc.count} reportes activos y se necesitan "
            f"al menos {MIN_REPORTS_PER_ZONE}.",
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            {"zone": exc.zone_name, "reports": exc.count, "minimum": MIN_REPORTS_PER_ZONE},
        ) from exc
    except WeightsNotConfiguredError as exc:
        raise AppError(
            "WEIGHTS_NOT_CONFIGURED",
            "No hay una versión de pesos vigente.",
            status.HTTP_422_UNPROCESSABLE_CONTENT,
        ) from exc
    return RoundCreatedResponse(id=round_id)


@router.get("/evaluation-rounds", response_model=RoundsResponse)
def list_rounds(
    use_case: ReadRoundsDep,
    limit: Annotated[int, Query(ge=1, le=MAX_ROUNDS_PAGE)] = DEFAULT_ROUNDS_PAGE,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> RoundsResponse:
    """Rondas de la más reciente a la más antigua."""
    return RoundsResponse(
        items=[RoundSummaryResponse.from_summary(s) for s in use_case.list(limit, offset)],
        limit=limit,
        offset=offset,
    )


@router.get(
    "/evaluation-rounds/{round_id}",
    response_model=RoundProgressResponse,
    responses={404: {"description": "La ronda no existe (EVALUATION_ROUND_NOT_FOUND)"}},
)
def get_round(round_id: uuid.UUID, use_case: ReadRoundsDep) -> RoundProgressResponse:
    """Avance de la ronda: reportes por zona y quién ya envió su orden («Evaluador k»)."""
    try:
        return RoundProgressResponse.from_round_progress(use_case.progress(round_id))
    except RoundNotFoundError as exc:
        raise _not_found() from exc


@router.post(
    "/evaluation-rounds/{round_id}/close",
    response_model=RoundSummaryResponse,
    responses={
        404: {"description": "La ronda no existe (EVALUATION_ROUND_NOT_FOUND)"},
        409: {"description": "La ronda ya estaba cerrada (EVALUATION_ROUND_CLOSED)"},
    },
)
def close_round(
    round_id: uuid.UUID, close: CloseRoundDep, read: ReadRoundsDep
) -> RoundSummaryResponse:
    """Cierra la ronda: ya no recibe órdenes de evaluadores."""
    try:
        close.execute(round_id)
    except RoundNotFoundError as exc:
        raise _not_found() from exc
    except RoundAlreadyClosedError as exc:
        raise AppError(
            "EVALUATION_ROUND_CLOSED",
            "La ronda de evaluación ya está cerrada.",
            status.HTTP_409_CONFLICT,
        ) from exc
    return RoundSummaryResponse.from_summary(read.progress(round_id).summary)
