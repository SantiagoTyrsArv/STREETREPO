"""Rutas de autenticación: /api/v1/auth (HU-10, HU-11)."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Response, status

from app.core.dependencies import SessionDep, SettingsDep
from app.core.errors import AppError
from app.core.rate_limiting import (
    LOGIN_LIMIT_PER_IP,
    limit_per_client_ip,
    too_many_requests,
)
from app.modules.auth.application.errors import (
    AccountLockedError,
    InvalidCredentialsError,
    InvalidRefreshTokenError,
    PolicyNotAcceptedError,
    PolicyVersionMismatchError,
)
from app.modules.auth.application.login import Login, Logout, RefreshSession
from app.modules.auth.application.register import RegisterCitizen, Registration
from app.modules.auth.application.sessions import SessionIssuer
from app.modules.auth.domain.entities import TokenPair
from app.modules.auth.domain.lockout import DEFAULT_LOCKOUT_POLICY
from app.modules.auth.domain.passwords import WeakPasswordError
from app.modules.auth.infrastructure.refresh_repository import SqlRefreshTokenRepository
from app.modules.auth.presentation.dependencies import (
    LoginAttemptsDep,
    PasswordHasherDep,
    get_session_issuer,
    limit_registrations_per_ip,
)
from app.modules.auth.presentation.schemas import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
)
from app.modules.users.domain.ports import EmailAlreadyRegisteredError
from app.modules.users.infrastructure.repository import SqlUserRepository
from app.modules.users.presentation.schemas import UserResponse
from app.shared.application.clock import SystemClock

router = APIRouter(prefix="/auth", tags=["autenticación"])

SessionIssuerDep = Annotated[SessionIssuer, Depends(get_session_issuer)]

_TOO_MANY_REQUESTS_DOC: dict[int | str, dict[str, Any]] = {
    status.HTTP_429_TOO_MANY_REQUESTS: {"description": "Demasiados intentos; ver Retry-After"}
}

_INVALID_SESSION = AppError(
    "INVALID_REFRESH_TOKEN",
    "Tu sesión no es válida o venció. Inicia sesión de nuevo.",
    status.HTTP_401_UNAUTHORIZED,
)


def _token_response(tokens: TokenPair) -> TokenResponse:
    return TokenResponse(
        access_token=tokens.access_token,
        expires_in=tokens.access_expires_in_s,
        refresh_token=tokens.refresh_token,
    )


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(limit_registrations_per_ip)],
    responses={
        status.HTTP_409_CONFLICT: {"description": "Correo ya registrado o política desactualizada"},
        status.HTTP_422_UNPROCESSABLE_CONTENT: {"description": "Datos inválidos"},
        **_TOO_MANY_REQUESTS_DOC,
    },
)
def register(
    body: RegisterRequest,
    session: SessionDep,
    settings: SettingsDep,
    hasher: PasswordHasherDep,
) -> UserResponse:
    """Registra un ciudadano. Exige aceptar la versión vigente de la política de datos."""
    use_case = RegisterCitizen(
        users=SqlUserRepository(session),
        hasher=hasher,
        clock=SystemClock(),
        transaction=session,
        current_policy_version=settings.privacy_policy_version,
    )
    try:
        user = use_case.execute(
            Registration(
                name=body.name,
                email=body.email,
                password=body.password,
                accepted_policy=body.accepted_policy,
                policy_version=body.policy_version,
            )
        )
    except PolicyNotAcceptedError as exc:
        raise AppError(
            "POLICY_NOT_ACCEPTED",
            "Debes aceptar la política de tratamiento de datos para registrarte.",
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            {"field": "accepted_policy"},
        ) from exc
    except PolicyVersionMismatchError as exc:
        raise AppError(
            "POLICY_VERSION_OUTDATED",
            "La política de datos cambió. Revisa la versión vigente y acéptala de nuevo.",
            status.HTTP_409_CONFLICT,
            {"current_version": settings.privacy_policy_version},
        ) from exc
    except WeakPasswordError as exc:
        raise AppError(
            "WEAK_PASSWORD",
            str(exc) + ".",
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            {"field": "password"},
        ) from exc
    except EmailAlreadyRegisteredError as exc:
        raise AppError(
            "EMAIL_ALREADY_REGISTERED",
            "Ya existe una cuenta con ese correo. Inicia sesión o recupera tu acceso.",
            status.HTTP_409_CONFLICT,
            {"field": "email"},
        ) from exc
    return UserResponse.from_user(user)


@router.post(
    "/login",
    response_model=TokenResponse,
    dependencies=[Depends(limit_per_client_ip("login", LOGIN_LIMIT_PER_IP))],
    responses={
        status.HTTP_401_UNAUTHORIZED: {"description": "Credenciales incorrectas"},
        **_TOO_MANY_REQUESTS_DOC,
    },
)
def login(
    body: LoginRequest,
    session: SessionDep,
    hasher: PasswordHasherDep,
    sessions: SessionIssuerDep,
    attempts: LoginAttemptsDep,
) -> TokenResponse:
    """Inicia sesión: token de acceso corto y token de refresco de un solo uso.

    Tras 5 fallos seguidos con el mismo correo, bloquea los intentos de forma progresiva
    (1, 2, 4, 8 y hasta 15 min) y responde 429 con ``Retry-After``.
    """
    use_case = Login(
        users=SqlUserRepository(session),
        hasher=hasher,
        sessions=sessions,
        clock=SystemClock(),
        transaction=session,
        attempts=attempts,
        lockout=DEFAULT_LOCKOUT_POLICY,
    )
    try:
        tokens = use_case.execute(body.email, body.password)
    except AccountLockedError as exc:
        raise too_many_requests(
            "TOO_MANY_LOGIN_ATTEMPTS",
            "Demasiados intentos fallidos. Espera un momento e intenta de nuevo.",
            exc.retry_after,
        ) from exc
    except InvalidCredentialsError as exc:
        raise AppError(
            "INVALID_CREDENTIALS",
            "Correo o contraseña incorrectos.",
            status.HTTP_401_UNAUTHORIZED,
        ) from exc
    return _token_response(tokens)


@router.post(
    "/refresh",
    response_model=TokenResponse,
    responses={status.HTTP_401_UNAUTHORIZED: {"description": "Sesión no válida o vencida"}},
)
def refresh(body: RefreshRequest, session: SessionDep, sessions: SessionIssuerDep) -> TokenResponse:
    """Cambia un token de refresco por un par nuevo; el usado deja de servir."""
    use_case = RefreshSession(
        users=SqlUserRepository(session),
        refresh_tokens=SqlRefreshTokenRepository(session),
        sessions=sessions,
        clock=SystemClock(),
        transaction=session,
    )
    try:
        tokens = use_case.execute(body.refresh_token)
    except InvalidRefreshTokenError as exc:
        raise _INVALID_SESSION from exc
    return _token_response(tokens)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(body: RefreshRequest, session: SessionDep) -> Response:
    """Cierra la sesión del token de refresco. Repetirlo no da error."""
    Logout(refresh_tokens=SqlRefreshTokenRepository(session), transaction=session).execute(
        body.refresh_token
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
