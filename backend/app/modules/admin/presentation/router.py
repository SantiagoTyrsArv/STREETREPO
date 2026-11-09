"""Rutas del panel administrativo: /api/v1/admin/... (HU-08).

Todo el router exige el rol de administrador en el servidor (guía 7.1), aunque la interfaz
oculte lo que un ciudadano no puede usar.
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.core.errors import AppError
from app.modules.admin.domain.errors import ReportNotFoundError
from app.modules.admin.domain.ranking_view import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE
from app.modules.admin.presentation.dependencies import GetAdminReportDep, ReadDashboardDep
from app.modules.admin.presentation.schemas import (
    AdminReportResponse,
    HeatmapResponse,
    RankingResponse,
    SummaryResponse,
)
from app.modules.auth.presentation.dependencies import require_admin
from app.modules.reports.domain.status import ReportStatus
from app.shared.domain.geo import BoundingBox, InvalidGeometryError

router = APIRouter(prefix="/admin", tags=["administración"], dependencies=[Depends(require_admin)])

_BBOX_PARTS = 4


def _report_not_found() -> AppError:
    return AppError("REPORT_NOT_FOUND", "No encontramos ese reporte.", status.HTTP_404_NOT_FOUND)


def parse_bbox(raw: str) -> BoundingBox:
    """Lee ``min_lon,min_lat,max_lon,max_lat`` (orden de Leaflet ``toBBoxString``)."""
    parts = raw.split(",")
    if len(parts) != _BBOX_PARTS:
        raise InvalidGeometryError("Se esperan cuatro valores")
    try:
        min_lon, min_lat, max_lon, max_lat = (float(part) for part in parts)
    except ValueError as exc:
        raise InvalidGeometryError("Los valores deben ser números") from exc
    return BoundingBox(south=min_lat, west=min_lon, north=max_lat, east=max_lon)


@router.get("/ranking", response_model=RankingResponse)
def get_ranking(
    use_case: ReadDashboardDep,
    status_filter: Annotated[list[ReportStatus] | None, Query(alias="status")] = None,
    limit: Annotated[int, Query(ge=1, le=MAX_PAGE_SIZE)] = DEFAULT_PAGE_SIZE,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> RankingResponse:
    """Reportes evaluados en el orden del modelo de priorización (guía 2.2): U desc →
    severidad → confirmaciones → antigüedad. Sin ``status``, los activos (todo salvo
    Reparado). La miniatura se pide a ``/reports/{id}/photo/thumbnail``.
    """
    statuses = frozenset(status_filter) if status_filter else None
    page = use_case.ranking(statuses, limit, offset)
    return RankingResponse.from_page(page, limit, offset)


@router.get("/summary", response_model=SummaryResponse)
def get_summary(use_case: ReadDashboardDep) -> SummaryResponse:
    """Indicadores del encabezado: Activos · Evaluados · Priorizados · Reparados."""
    return SummaryResponse.from_summary(use_case.summary())


@router.get(
    "/heatmap",
    response_model=HeatmapResponse,
    responses={422: {"description": "Rectángulo mal formado (INVALID_BBOX)"}},
)
def get_heatmap(
    use_case: ReadDashboardDep,
    bbox: Annotated[
        str | None,
        Query(description="min_lon,min_lat,max_lon,max_lat en grados WGS 84"),
    ] = None,
) -> HeatmapResponse:
    """Puntos (lat, lon, U) de los reportes activos evaluados, con coordenadas exactas."""
    area = None
    if bbox is not None:
        try:
            area = parse_bbox(bbox)
        except InvalidGeometryError as exc:
            raise AppError(
                "INVALID_BBOX",
                "El área del mapa no es válida.",
                status.HTTP_422_UNPROCESSABLE_CONTENT,
                {"bbox": "min_lon,min_lat,max_lon,max_lat"},
            ) from exc
    return HeatmapResponse.from_points(use_case.heat_points(area))


@router.get(
    "/reports/{report_id}",
    response_model=AdminReportResponse,
    responses={404: {"description": "El reporte no existe (REPORT_NOT_FOUND)"}},
)
def get_admin_report(report_id: uuid.UUID, use_case: GetAdminReportDep) -> AdminReportResponse:
    """Detalle para la pantalla «Detalle y estado»: vía OSM, servicio crítico más cercano,
    desglose del cálculo con los pesos de su versión, reportante e historial con su autor.
    La foto se pide a ``/reports/{id}/photo``.
    """
    try:
        detail = use_case.execute(report_id)
    except ReportNotFoundError as exc:
        raise _report_not_found() from exc
    return AdminReportResponse.from_detail(detail)
