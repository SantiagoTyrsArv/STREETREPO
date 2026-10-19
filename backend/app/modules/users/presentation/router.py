"""Rutas del propio titular: /api/v1/me (derechos de conocer, actualizar y suprimir, Ley 1581)."""

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from fastapi import APIRouter, status

from app.core.dependencies import SessionDep, SettingsDep
from app.core.errors import AppError
from app.core.rate_limiting import too_many_requests
from app.modules.auth.application.errors import (
    AccountLockedError,
    PasswordConfirmationRequiredError,
    WrongPasswordError,
)
from app.modules.auth.infrastructure.refresh_repository import SqlRefreshTokenRepository
from app.modules.auth.presentation.dependencies import CurrentUserDep, PasswordConfirmationDep
from app.modules.reports.application.photo_cleanup import PhotoFileCleanup
from app.modules.reports.infrastructure.evidence import SqlReportPhotoEraser
from app.modules.reports.infrastructure.local_photo_storage import LocalPhotoStorage
from app.modules.reports.infrastructure.text_eraser import SqlReportTextEraser
from app.modules.users.application.data_rights import (
    ProfileChanges,
    RequestDataDeletion,
    UpdateMyData,
)
from app.modules.users.domain.ports import EmailAlreadyRegisteredError
from app.modules.users.infrastructure.repository import (
    SqlDeletionRequestRepository,
    SqlUserRepository,
)
from app.modules.users.presentation.schemas import (
    DataDeletionRequestBody,
    DataDeletionResponse,
    UpdateMyDataRequest,
    UserResponse,
)
from app.shared.application.clock import SystemClock

router = APIRouter(prefix="/me", tags=["mis datos"])

_PASSWORD_CONFIRMATION_DOC: dict[int | str, dict[str, Any]] = {
    status.HTTP_403_FORBIDDEN: {"description": "La contraseña actual no es correcta"},
    status.HTTP_429_TOO_MANY_REQUESTS: {"description": "Demasiados intentos; ver Retry-After"},
}


@contextmanager
def _password_confirmation_errors() -> Iterator[None]:
    """Traduce los fallos de la confirmación de contraseña al formato de error de la API."""
    try:
        yield
    except PasswordConfirmationRequiredError as exc:
        raise AppError(
            "PASSWORD_CONFIRMATION_REQUIRED",
            "Para cambiar tu correo, confirma tu contraseña actual.",
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            {"field": "current_password"},
        ) from exc
    except WrongPasswordError as exc:
        raise AppError(
            "PASSWORD_CONFIRMATION_FAILED",
            "La contraseña actual no es correcta.",
            status.HTTP_403_FORBIDDEN,
            {"field": "current_password"},
        ) from exc
    except AccountLockedError as exc:
        raise too_many_requests(
            "TOO_MANY_LOGIN_ATTEMPTS",
            "Demasiados intentos fallidos. Espera un momento e intenta de nuevo.",
            exc.retry_after,
        ) from exc


@router.get("", response_model=UserResponse)
def get_my_data(user: CurrentUserDep) -> UserResponse:
    """Datos personales que el sistema guarda del usuario autenticado."""
    return UserResponse.from_user(user)


@router.patch(
    "",
    response_model=UserResponse,
    responses={
        status.HTTP_409_CONFLICT: {"description": "El correo ya es de otra cuenta"},
        **_PASSWORD_CONFIRMATION_DOC,
    },
)
def update_my_data(
    body: UpdateMyDataRequest,
    user: CurrentUserDep,
    session: SessionDep,
    confirmation: PasswordConfirmationDep,
) -> UserResponse:
    """Actualiza nombre o correo. Cambiar el correo exige la contraseña actual."""
    use_case = UpdateMyData(SqlUserRepository(session), confirmation, session)
    changes = ProfileChanges(
        name=body.name, email=body.email, current_password=body.current_password
    )
    try:
        with _password_confirmation_errors():
            updated = use_case.execute(user, changes)
    except EmailAlreadyRegisteredError as exc:
        raise AppError(
            "EMAIL_ALREADY_REGISTERED",
            "Ya existe una cuenta con ese correo.",
            status.HTTP_409_CONFLICT,
            {"field": "email"},
        ) from exc
    return UserResponse.from_user(updated)


@router.post(
    "/data-deletion-requests",
    response_model=DataDeletionResponse,
    status_code=status.HTTP_201_CREATED,
    responses=_PASSWORD_CONFIRMATION_DOC,
)
def request_data_deletion(
    body: DataDeletionRequestBody,
    user: CurrentUserDep,
    session: SessionDep,
    settings: SettingsDep,
    confirmation: PasswordConfirmationDep,
) -> DataDeletionResponse:
    """Suprime de inmediato los datos personales del titular (Ley 1581). Es irreversible.

    Anonimiza la cuenta, borra la descripción y las fotos de sus reportes y cierra todas
    sus sesiones. Los reportes se conservan, sin foto, como dato de la vía.
    """
    use_case = RequestDataDeletion(
        users=SqlUserRepository(session),
        deletion_requests=SqlDeletionRequestRepository(session),
        report_texts=SqlReportTextEraser(session),
        report_photos=SqlReportPhotoEraser(session),
        photo_files=PhotoFileCleanup(LocalPhotoStorage(settings.photo_storage_dir)),
        refresh_tokens=SqlRefreshTokenRepository(session),
        confirmation=confirmation,
        clock=SystemClock(),
        transaction=session,
    )
    with _password_confirmation_errors():
        request = use_case.execute(user, body.current_password)
    return DataDeletionResponse.from_request(request)
