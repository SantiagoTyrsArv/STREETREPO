"""Rutas de sesión del panel web: /api/v1/auth/web (HU-10, decisión 42).

Solo entran administradores. El refresco nunca viaja en el cuerpo: va en la cookie
``sr_refresh``. La variante de la app móvil (``/auth/login``, ``/refresh``, ``/logout``)
no cambia.
"""

from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, Response, status

from app.core.dependencies import SessionDep, SettingsDep
from app.core.errors import AppError
from app.core.rate_limiting import LOGIN_LIMIT_PER_IP, limit_per_client_ip, too_many_requests
from app.modules.auth.application.errors import (
    AccountLockedError,
    InsufficientRoleError,
    InvalidCredentialsError,
    InvalidRefreshTokenError,
)
from app.modules.auth.application.login import Login, Logout, RefreshSession
from app.modules.auth.application.sessions import SessionIssuer
from app.modules.auth.domain.entities import TokenPair
from app.modules.auth.domain.lockout import DEFAULT_LOCKOUT_POLICY
from app.modules.auth.infrastructure.refresh_repository import SqlRefreshTokenRepository
from app.modules.auth.presentation.dependencies import (
    LoginAttemptsDep,
    PasswordHasherDep,
    get_session_issuer,
)
from app.modules.auth.presentation.schemas import LoginRequest, WebTokenResponse
from app.modules.auth.presentation.web_session import (
    REFRESH_COOKIE_NAME,
    clear_refresh_cookie,
    clear_refresh_cookie_header,
    require_csrf_protection,
    set_refresh_cookie,
)
from app.modules.users.domain.role import UserRole
from app.modules.users.infrastructure.repository import SqlUserRepository
from app.shared.application.clock import SystemClock

router = APIRouter(
    prefix="/auth/web",
    tags=["autenticación (panel web)"],
    dependencies=[Depends(require_csrf_protection)],
    responses={
        status.HTTP_403_FORBIDDEN: {
            "description": "Falta X-CSRF-Protection: 1 o el Origin no es el del panel "
            "(CSRF_CHECK_FAILED), o la cuenta no es de administrador (ADMIN_ROLE_REQUIRED)"
        }
    },
)

SessionIssuerDep = Annotated[SessionIssuer, Depends(get_session_issuer)]
RefreshCookie = Annotated[str | None, Cookie(alias=REFRESH_COOKIE_NAME)]


def _role_required(headers: dict[str, str] | None = None) -> AppError:
    return AppError(
        "ADMIN_ROLE_REQUIRED",
        "Esta cuenta no tiene acceso al panel.",
        status.HTTP_403_FORBIDDEN,
        headers=headers,
    )


def _web_tokens(response: Response, tokens: TokenPair, ttl_days: int) -> WebTokenResponse:
    set_refresh_cookie(response, tokens.refresh_token, ttl_days)
    return WebTokenResponse(access_token=tokens.access_token, expires_in=tokens.access_expires_in_s)


@router.post(
    "/login",
    response_model=WebTokenResponse,
    dependencies=[Depends(limit_per_client_ip("login", LOGIN_LIMIT_PER_IP))],
    responses={
        status.HTTP_401_UNAUTHORIZED: {"description": "Credenciales incorrectas"},
        status.HTTP_429_TOO_MANY_REQUESTS: {"description": "Demasiados intentos"},
    },
)
def web_login(
    body: LoginRequest,
    *,
    response: Response,
    session: SessionDep,
    settings: SettingsDep,
    hasher: PasswordHasherDep,
    sessions: SessionIssuerDep,
    attempts: LoginAttemptsDep,
) -> WebTokenResponse:
    """Inicia sesión en el panel: acceso en el cuerpo, refresco en la cookie ``sr_refresh``.

    Mismos límites que el inicio de sesión de la app. Una cuenta de ciudadano recibe 403 y
    no se emite sesión.
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
        tokens = use_case.execute(body.email, body.password, required_role=UserRole.ADMIN)
    except AccountLockedError as exc:
        raise too_many_requests(
            "TOO_MANY_LOGIN_ATTEMPTS",
            "Demasiados intentos fallidos. Espera un momento e intenta de nuevo.",
            exc.retry_after,
        ) from exc
    except InvalidCredentialsError as exc:
        raise AppError(
            "INVALID_CREDENTIALS", "Correo o contraseña incorrectos.", status.HTTP_401_UNAUTHORIZED
        ) from exc
    except InsufficientRoleError as exc:
        raise _role_required() from exc
    return _web_tokens(response, tokens, settings.refresh_token_ttl_days)


@router.post(
    "/refresh",
    response_model=WebTokenResponse,
    responses={status.HTTP_401_UNAUTHORIZED: {"description": "Sesión no válida (INVALID_SESSION)"}},
)
def web_refresh(
    response: Response,
    session: SessionDep,
    settings: SettingsDep,
    sessions: SessionIssuerDep,
    refresh_token: RefreshCookie = None,
) -> WebTokenResponse:
    """Rota la cookie de refresco y entrega un acceso nuevo; así el panel recupera la
    sesión al recargar la página. Sin cookie válida responde 401 y la borra.
    """
    use_case = RefreshSession(
        users=SqlUserRepository(session),
        refresh_tokens=SqlRefreshTokenRepository(session),
        sessions=sessions,
        clock=SystemClock(),
        transaction=session,
    )
    try:
        if not refresh_token:
            raise InvalidRefreshTokenError("Sin cookie de sesión")
        tokens = use_case.execute(refresh_token, required_role=UserRole.ADMIN)
    except InvalidRefreshTokenError as exc:
        raise AppError(
            "INVALID_SESSION",
            "Tu sesión terminó. Inicia sesión de nuevo.",
            status.HTTP_401_UNAUTHORIZED,
            headers=clear_refresh_cookie_header(),
        ) from exc
    except InsufficientRoleError as exc:
        raise _role_required(clear_refresh_cookie_header()) from exc
    return _web_tokens(response, tokens, settings.refresh_token_ttl_days)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def web_logout(session: SessionDep, refresh_token: RefreshCookie = None) -> Response:
    """Revoca la sesión de la cookie y la borra. Repetirlo no da error."""
    if refresh_token:
        Logout(refresh_tokens=SqlRefreshTokenRepository(session), transaction=session).execute(
            refresh_token
        )
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    clear_refresh_cookie(response)
    return response
