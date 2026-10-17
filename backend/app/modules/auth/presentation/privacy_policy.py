"""Ruta pública de la política de datos: /api/v1/privacy-policy (HU-11, propuesta 27)."""

from fastapi import APIRouter

from app.core.dependencies import SettingsDep
from app.modules.auth.presentation.schemas import PrivacyPolicyResponse

router = APIRouter(prefix="/privacy-policy", tags=["política de datos"])


@router.get("", response_model=PrivacyPolicyResponse)
def get_privacy_policy(settings: SettingsDep) -> PrivacyPolicyResponse:
    """Versión vigente de la política y dónde leerla; el registro exige aceptar esta versión."""
    url = settings.privacy_policy_url
    return PrivacyPolicyResponse(
        version=settings.privacy_policy_version,
        url=str(url) if url is not None else None,
    )
