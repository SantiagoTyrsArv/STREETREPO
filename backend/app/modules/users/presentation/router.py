"""Rutas del propio titular: /api/v1/me (derecho a conocer sus datos, Ley 1581)."""

from fastapi import APIRouter

from app.modules.auth.presentation.dependencies import CurrentUserDep
from app.modules.users.presentation.schemas import UserResponse

router = APIRouter(prefix="/me", tags=["mis datos"])


@router.get("", response_model=UserResponse)
def get_my_data(user: CurrentUserDep) -> UserResponse:
    """Datos personales que el sistema guarda del usuario autenticado."""
    return UserResponse.from_user(user)
