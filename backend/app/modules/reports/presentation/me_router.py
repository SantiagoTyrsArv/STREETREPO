"""Ruta «Mis reportes»: /api/v1/me/reports (decisión 49)."""

from typing import Annotated

from fastapi import APIRouter, Query

from app.modules.auth.presentation.dependencies import CurrentUserDep
from app.modules.reports.domain.my_reports import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE
from app.modules.reports.presentation.dependencies import ListMyReportsDep
from app.modules.reports.presentation.schemas import MyReportsResponse

router = APIRouter(prefix="/me/reports", tags=["mis reportes"])


@router.get("", response_model=MyReportsResponse)
def list_my_reports(
    user: CurrentUserDep,
    use_case: ListMyReportsDep,
    limit: Annotated[int, Query(ge=1, le=MAX_PAGE_SIZE)] = DEFAULT_PAGE_SIZE,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> MyReportsResponse:
    """Reportes que el usuario creó (``relation: own``, completos) o confirmó
    (``relation: confirmed``, vista pública sin autor, descripción ni ubicación exacta),
    del más reciente al más antiguo por fecha de creación o de confirmación.

    La miniatura de los propios se pide a ``/reports/{id}/photo/thumbnail``.
    """
    return MyReportsResponse.from_page(use_case.execute(user.id, limit, offset))
