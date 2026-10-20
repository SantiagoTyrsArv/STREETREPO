"""Inyección de dependencias de autenticación y control de acceso por rol (guía 7.1)."""

from datetime import timedelta
from typing import Annotated

from fastapi import Depends, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.dependencies import SessionDep, SettingsDep
from app.core.errors import AppError
from app.core.rate_limiting import RateLimiterDep, limit_per_client_ip
from app.modules.auth.application.reauthentication import PasswordConfirmation
from app.modules.auth.application.sessions import SessionIssuer
from app.modules.auth.domain.lockout import DEFAULT_LOCKOUT_POLICY
from app.modules.auth.domain.ports import InvalidAccessTokenError, LoginAttemptStore
from app.modules.auth.infrastructure.jwt_tokens import JwtAccessTokenService
from app.modules.auth.infrastructure.passwords import Argon2PasswordHasher
from app.modules.auth.infrastructure.refresh_repository import SqlRefreshTokenRepository
from app.modules.users.domain.entities import User
from app.modules.users.domain.role import UserRole
from app.modules.users.infrastructure.repository import SqlUserRepository
from app.shared.application.clock import SystemClock
from app.shared.application.rate_limit import RateLimit

_bearer = HTTPBearer(auto_error=False, description="Token de acceso (JWT) de /auth/login")
_password_hasher = Argon2PasswordHasher()

_WWW_AUTHENTICATE = {"WWW-Authenticate": "Bearer"}


def limit_registrations_per_ip(
    request: Request, limiter: RateLimiterDep, settings: SettingsDep
) -> None:
    """Cupo de registros por IP (decisión 25), configurable por el CGNAT (decisión 58)."""
    limit = RateLimit(max_requests=settings.register_per_ip_per_hour, window=timedelta(hours=1))
    limit_per_client_ip("register", limit)(request, limiter)


def get_password_hasher() -> Argon2PasswordHasher:
    return _password_hasher


def get_access_token_service(settings: SettingsDep) -> JwtAccessTokenService:
    return JwtAccessTokenService(settings.jwt_secret_key, settings.access_token_ttl_minutes)


AccessTokensDep = Annotated[JwtAccessTokenService, Depends(get_access_token_service)]
PasswordHasherDep = Annotated[Argon2PasswordHasher, Depends(get_password_hasher)]


def get_login_attempts(request: Request) -> LoginAttemptStore:
    attempts: LoginAttemptStore = request.app.state.login_attempts
    return attempts


LoginAttemptsDep = Annotated[LoginAttemptStore, Depends(get_login_attempts)]


def get_password_confirmation(
    hasher: PasswordHasherDep, attempts: LoginAttemptsDep
) -> PasswordConfirmation:
    return PasswordConfirmation(hasher, attempts, DEFAULT_LOCKOUT_POLICY, SystemClock())


PasswordConfirmationDep = Annotated[PasswordConfirmation, Depends(get_password_confirmation)]


def get_session_issuer(
    session: SessionDep, settings: SettingsDep, access_tokens: AccessTokensDep
) -> SessionIssuer:
    return SessionIssuer(
        access_tokens=access_tokens,
        refresh_tokens=SqlRefreshTokenRepository(session),
        refresh_ttl=timedelta(days=settings.refresh_token_ttl_days),
    )


def _unauthorized(code: str, message: str) -> AppError:
    return AppError(code, message, status.HTTP_401_UNAUTHORIZED, headers=_WWW_AUTHENTICATE)


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    session: SessionDep,
    access_tokens: AccessTokensDep,
) -> User:
    """Usuario del token de acceso. Se lee de la base en cada petición: una cuenta
    desactivada o anonimizada pierde el acceso de inmediato, sin esperar a que venza el JWT.
    """
    if credentials is None:
        raise _unauthorized("UNAUTHORIZED", "Debes iniciar sesión para continuar.")
    try:
        claims = access_tokens.verify(credentials.credentials)
    except InvalidAccessTokenError as exc:
        raise _unauthorized("INVALID_TOKEN", "Tu sesión no es válida o venció.") from exc
    user = SqlUserRepository(session).get_by_id(claims.user_id)
    if user is None or not user.is_active:
        raise _unauthorized("INVALID_TOKEN", "Tu sesión no es válida o venció.")
    return user


CurrentUserDep = Annotated[User, Depends(get_current_user)]


def require_admin(user: CurrentUserDep) -> User:
    """Toda ruta administrativa verifica el rol en el servidor (guía 7.1)."""
    if user.role is not UserRole.ADMIN:
        raise AppError(
            "FORBIDDEN",
            "No tienes permiso para realizar esta acción.",
            status.HTTP_403_FORBIDDEN,
        )
    return user


AdminUserDep = Annotated[User, Depends(require_admin)]
