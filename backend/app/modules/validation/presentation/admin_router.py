"""Rutas administrativas del estudio de validación: /api/v1/admin/... (objetivo 4).

Exigen el rol de administrador en el servidor (guía 7.1); los evaluadores no entran.
"""

from fastapi import APIRouter, Depends

from app.modules.auth.presentation.dependencies import require_admin
from app.modules.validation.presentation.dependencies import ListZonesDep
from app.modules.validation.presentation.schemas import ZonesResponse

router = APIRouter(prefix="/admin", tags=["validación"], dependencies=[Depends(require_admin)])


@router.get("/zones", response_model=ZonesResponse)
def list_zones(use_case: ListZonesDep) -> ZonesResponse:
    """Zonas del piloto con sus reportes activos (todo salvo Reparado) y totales."""
    return ZonesResponse.from_summaries(use_case.execute())
