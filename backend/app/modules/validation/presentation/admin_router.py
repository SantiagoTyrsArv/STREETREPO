"""Rutas administrativas del estudio de validación: /api/v1/admin/... (objetivo 4).

Exigen el rol de administrador en el servidor (guía 7.1); los evaluadores no entran.
"""

import uuid
from collections.abc import Callable
from typing import Annotated, Any, Final

from fastapi import APIRouter, Depends, Query, Response, status

from app.core.errors import AppError
from app.modules.auth.presentation.dependencies import AdminUserDep, require_admin
from app.modules.priority.application.evaluate_report import WeightsNotConfiguredError
from app.modules.validation.domain.parameters import MIN_REPORTS_PER_ZONE
from app.modules.validation.domain.results import RoundResults, RoundStillOpenError
from app.modules.validation.domain.rounds import (
    NoZonesError,
    RoundAlreadyClosedError,
    RoundAlreadyOpenError,
    RoundNotFoundError,
    ZoneTooSmallError,
)
from app.modules.validation.presentation.csv_export import (
    avisos_csv,
    export_filename,
    ficha_csv,
    reportes_csv,
    resumen_csv,
)
from app.modules.validation.presentation.dependencies import (
    CloseRoundDep,
    ListZonesDep,
    OpenRoundDep,
    ReadRoundsDep,
    RoundResultsDep,
)
from app.modules.validation.presentation.schemas import (
    OpenRoundRequest,
    RoundCreatedResponse,
    RoundProgressResponse,
    RoundResultsResponse,
    RoundsResponse,
    RoundSummaryResponse,
    ZonesResponse,
)

DEFAULT_ROUNDS_PAGE: int = 20
MAX_ROUNDS_PAGE: int = 50

router = APIRouter(prefix="/admin", tags=["validación"], dependencies=[Depends(require_admin)])


CSV_MEDIA_TYPE: Final = "text/csv; charset=utf-8"
_NOT_FOUND_DOC: Final[dict[int | str, dict[str, Any]]] = {
    404: {"description": "La ronda no existe (EVALUATION_ROUND_NOT_FOUND)"}
}
_RESULTS_DOC: Final[dict[int | str, dict[str, Any]]] = {
    **_NOT_FOUND_DOC,
    409: {"description": "La ronda sigue abierta (EVALUATION_ROUND_STILL_OPEN)"},
}


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
    responses=_NOT_FOUND_DOC,
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


def _closed_results(round_id: uuid.UUID, use_case: RoundResultsDep) -> RoundResults:
    try:
        return use_case.results(round_id)
    except RoundNotFoundError as exc:
        raise _not_found() from exc
    except RoundStillOpenError as exc:
        raise AppError(
            "EVALUATION_ROUND_STILL_OPEN",
            "La ronda sigue abierta. Ciérrala para ver los resultados.",
            status.HTTP_409_CONFLICT,
        ) from exc


def _csv(content: bytes, round_name: str, kind: str) -> Response:
    filename = export_filename(round_name, kind)
    return Response(
        content=content,
        media_type=CSV_MEDIA_TYPE,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            # Lleva identificadores de reportes y decisiones de ciudadanos: no se guarda en cachés.
            "Cache-Control": "private, no-store",
        },
    )


def _csv_doc(description: str, errors: dict[int | str, dict[str, Any]]) -> dict[str, Any]:
    return {
        "response_class": Response,
        "responses": {200: {"content": {"text/csv": {}}, "description": description}, **errors},
    }


@router.get(
    "/evaluation-rounds/{round_id}/results",
    response_model=RoundResultsResponse,
    responses=_RESULTS_DOC,
)
def get_round_results(round_id: uuid.UUID, use_case: RoundResultsDep) -> RoundResultsResponse:
    """Métricas de acuerdo por zona, prueba entre zonas y deduplicación de la ronda cerrada.

    Los evaluadores aparecen como «Evaluador k», nunca por nombre ni correo.
    """
    return RoundResultsResponse.from_results(_closed_results(round_id, use_case))


def _results_export(
    kind: str, render: Callable[[RoundResults], bytes]
) -> Callable[[uuid.UUID, RoundResultsDep], Response]:
    def export(round_id: uuid.UUID, use_case: RoundResultsDep) -> Response:
        results = _closed_results(round_id, use_case)
        return _csv(render(results), results.round.name, kind)

    return export


router.add_api_route(
    "/evaluation-rounds/{round_id}/export/ficha.csv",
    _results_export("ficha", ficha_csv),
    methods=["GET"],
    summary="Ficha comparativa: una fila por reporte (ronda cerrada)",
    **_csv_doc("CSV con el orden del motor, del panel y de cada evaluador", _RESULTS_DOC),
)
router.add_api_route(
    "/evaluation-rounds/{round_id}/export/resumen.csv",
    _results_export("resumen", resumen_csv),
    methods=["GET"],
    summary="Resumen por zona y prueba entre zonas (ronda cerrada)",
    **_csv_doc("CSV con las métricas y la deduplicación por zona", _RESULTS_DOC),
)


@router.get(
    "/evaluation-rounds/{round_id}/export/reportes.csv",
    summary="Reportes de las zonas para la revisión manual de duplicados",
    **_csv_doc("CSV de los reportes de cada zona con el enlace a la foto", _NOT_FOUND_DOC),
)
def export_review_reports(round_id: uuid.UUID, use_case: RoundResultsDep) -> Response:
    """Se sirve aunque la ronda siga abierta: es para la revisión manual."""
    try:
        summary, reports = use_case.review_reports(round_id)
    except RoundNotFoundError as exc:
        raise _not_found() from exc
    return _csv(reportes_csv(reports), summary.name, "reportes")


@router.get(
    "/evaluation-rounds/{round_id}/export/avisos.csv",
    summary="Avisos de duplicado de las zonas para la revisión manual",
    **_csv_doc("CSV de los avisos con sus candidatos y la decisión del ciudadano", _NOT_FOUND_DOC),
)
def export_review_warnings(round_id: uuid.UUID, use_case: RoundResultsDep) -> Response:
    """Se sirve aunque la ronda siga abierta: es para la revisión manual."""
    try:
        summary, warnings = use_case.review_warnings(round_id)
    except RoundNotFoundError as exc:
        raise _not_found() from exc
    return _csv(avisos_csv(warnings), summary.name, "avisos")
