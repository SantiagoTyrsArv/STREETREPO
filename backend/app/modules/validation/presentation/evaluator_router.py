"""Rutas del evaluador: /api/v1/evaluation/... (objetivo 4, HU-09).

Exigen el rol de evaluador en el servidor. Ninguna respuesta lleva información del motor
de priorización ni de otros evaluadores (vista a ciegas, diseño sección 6).
"""

import uuid
from typing import Annotated, Any, Final

from fastapi import APIRouter, Depends, Path, Response, status

from app.core.errors import AppError
from app.modules.auth.presentation.dependencies import EvaluatorUserDep, require_evaluator
from app.modules.validation.domain.blind import (
    BlindPhotoNotAvailableError,
    InvalidOrderError,
    NoOpenRoundError,
    OrderAlreadySubmittedError,
    ZoneNotInRoundError,
)
from app.modules.validation.presentation.dependencies import (
    GetBlindPhotoDep,
    SubmitOrderDep,
    ViewCurrentRoundDep,
    ViewZoneDep,
)
from app.modules.validation.presentation.schemas import (
    CurrentRoundResponse,
    OrderSubmittedResponse,
    SubmitOrderRequest,
    ZoneCardsResponse,
)

# id_zona es INTEGER: un id fuera de rango sería un error de la base (500), no un 404.
MAX_ZONE_ID: Final = 2**31 - 1
ZoneIdPath = Annotated[int, Path(ge=1, le=MAX_ZONE_ID)]

router = APIRouter(
    prefix="/evaluation", tags=["evaluación a ciegas"], dependencies=[Depends(require_evaluator)]
)

_NO_ROUND_DOC = {"description": "No hay una ronda abierta (EVALUATION_NO_OPEN_ROUND)"}
_ZONE_DOC = {
    "description": "No hay ronda abierta (EVALUATION_NO_OPEN_ROUND) o la zona no está en ella "
    "(EVALUATION_ZONE_NOT_FOUND)"
}
# Igual que la foto del dueño: ningún intermediario ni el navegador la guarda (Ley 1581).
_PHOTO_HEADERS = {"Cache-Control": "private, no-store"}
_PHOTO_DOC: dict[int | str, dict[str, Any]] = {
    status.HTTP_200_OK: {"content": {"image/jpeg": {}}, "description": "Foto en JPEG"},
    status.HTTP_404_NOT_FOUND: {
        "description": "No hay ronda abierta, el reporte no está en ella o no tiene foto "
        "(PHOTO_NOT_FOUND)"
    },
}


def _no_open_round() -> AppError:
    return AppError(
        "EVALUATION_NO_OPEN_ROUND",
        "No hay una ronda de evaluación abierta.",
        status.HTTP_404_NOT_FOUND,
    )


def _zone_not_found() -> AppError:
    return AppError(
        "EVALUATION_ZONE_NOT_FOUND",
        "Esa zona no forma parte de la ronda abierta.",
        status.HTTP_404_NOT_FOUND,
    )


@router.get("/current", response_model=CurrentRoundResponse, responses={404: _NO_ROUND_DOC})
def get_current_round(
    evaluator: EvaluatorUserDep, use_case: ViewCurrentRoundDep
) -> CurrentRoundResponse:
    """La ronda abierta con sus zonas y si el evaluador ya envió el orden de cada una."""
    try:
        return CurrentRoundResponse.from_view(use_case.execute(evaluator.id))
    except NoOpenRoundError as exc:
        raise _no_open_round() from exc


@router.get(
    "/current/zones/{zone_id}", response_model=ZoneCardsResponse, responses={404: _ZONE_DOC}
)
def get_zone_cards(
    zone_id: ZoneIdPath, evaluator: EvaluatorUserDep, use_case: ViewZoneDep
) -> ZoneCardsResponse:
    """Tarjetas a ciegas de la zona, en un orden inicial aleatorio propio del evaluador."""
    try:
        return ZoneCardsResponse.from_view(use_case.execute(evaluator.id, zone_id))
    except NoOpenRoundError as exc:
        raise _no_open_round() from exc
    except ZoneNotInRoundError as exc:
        raise _zone_not_found() from exc


def _photo_response(
    use_case: GetBlindPhotoDep, report_id: uuid.UUID, *, thumbnail: bool
) -> Response:
    try:
        content = use_case.execute(report_id, thumbnail=thumbnail)
    except BlindPhotoNotAvailableError as exc:
        raise AppError(
            "PHOTO_NOT_FOUND", "No encontramos esa foto.", status.HTTP_404_NOT_FOUND
        ) from exc
    return Response(content=content, media_type="image/jpeg", headers=_PHOTO_HEADERS)


@router.get("/current/reports/{report_id}/photo", response_class=Response, responses=_PHOTO_DOC)
def get_blind_photo(report_id: uuid.UUID, use_case: GetBlindPhotoDep) -> Response:
    """Foto (hasta 1600 px) de un reporte de la ronda abierta."""
    return _photo_response(use_case, report_id, thumbnail=False)


@router.get(
    "/current/reports/{report_id}/photo/thumbnail",
    response_class=Response,
    responses=_PHOTO_DOC,
)
def get_blind_photo_thumbnail(report_id: uuid.UUID, use_case: GetBlindPhotoDep) -> Response:
    """Miniatura (hasta 400 px) de la foto de un reporte de la ronda abierta."""
    return _photo_response(use_case, report_id, thumbnail=True)


@router.put(
    "/current/zones/{zone_id}/order",
    status_code=status.HTTP_201_CREATED,
    response_model=OrderSubmittedResponse,
    responses={
        404: _ZONE_DOC,
        409: {"description": "Ya envió el orden de esta zona (EVALUATION_ORDER_ALREADY_SUBMITTED)"},
        422: {
            "description": "La lista no es exactamente el conjunto de reportes de la zona, "
            "repite alguno o está vacía (EVALUATION_ORDER_INVALID)"
        },
    },
)
def submit_order(
    zone_id: ZoneIdPath,
    body: SubmitOrderRequest,
    evaluator: EvaluatorUserDep,
    use_case: SubmitOrderDep,
) -> OrderSubmittedResponse:
    """Guarda el orden del evaluador para la zona (posición 1 = la más urgente). Una sola vez."""
    try:
        use_case.execute(evaluator.id, zone_id, body.report_ids)
    except NoOpenRoundError as exc:
        raise _no_open_round() from exc
    except ZoneNotInRoundError as exc:
        raise _zone_not_found() from exc
    except OrderAlreadySubmittedError as exc:
        raise AppError(
            "EVALUATION_ORDER_ALREADY_SUBMITTED",
            "Ya enviaste el orden de esta zona y no se puede cambiar.",
            status.HTTP_409_CONFLICT,
        ) from exc
    except InvalidOrderError as exc:
        raise AppError(
            "EVALUATION_ORDER_INVALID",
            "El orden debe incluir cada reporte de la zona exactamente una vez.",
            status.HTTP_422_UNPROCESSABLE_CONTENT,
        ) from exc
    return OrderSubmittedResponse(zone_id=zone_id, submitted=True)
