"""Sesión del panel web (decisión 42, ADR 0004): cookie del refresco y defensa CSRF.

El token de acceso vive solo en la memoria del navegador. El de refresco viaja en una
cookie ``HttpOnly`` (el JavaScript no la lee), ``Secure`` y ``SameSite=Strict``, limitada
a las rutas ``/auth/web``. Como el navegador la envía sola, esas rutas exigen además una
cabecera propia (``X-CSRF-Protection: 1``, que un formulario de otro sitio no puede poner
sin pasar por el preflight de CORS) y un ``Origin`` de la lista de ``CORS_ORIGINS``.
"""

from typing import Final

from fastapi import Request, Response, status

from app.core.dependencies import SettingsDep
from app.core.errors import AppError

REFRESH_COOKIE_NAME: Final = "sr_refresh"
REFRESH_COOKIE_PATH: Final = "/api/v1/auth/web"
REFRESH_COOKIE_SAMESITE: Final = "strict"
CSRF_HEADER: Final = "X-CSRF-Protection"
CSRF_HEADER_VALUE: Final = "1"
_SECONDS_PER_DAY: Final = 86_400


def require_csrf_protection(request: Request, settings: SettingsDep) -> None:
    """Rechaza con 403 las peticiones sin la cabecera anti-CSRF o de un origen ajeno."""
    origin = request.headers.get("origin")
    if (
        request.headers.get(CSRF_HEADER) != CSRF_HEADER_VALUE
        or origin is None
        or origin not in settings.cors_origin_list
    ):
        raise AppError(
            "CSRF_CHECK_FAILED",
            "No se pudo verificar el origen de la solicitud.",
            status.HTTP_403_FORBIDDEN,
        )


def set_refresh_cookie(response: Response, token: str, ttl_days: int) -> None:
    response.set_cookie(
        REFRESH_COOKIE_NAME,
        token,
        max_age=ttl_days * _SECONDS_PER_DAY,
        path=REFRESH_COOKIE_PATH,
        secure=True,
        httponly=True,
        samesite=REFRESH_COOKIE_SAMESITE,
    )


def clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(
        REFRESH_COOKIE_NAME,
        path=REFRESH_COOKIE_PATH,
        secure=True,
        httponly=True,
        samesite=REFRESH_COOKIE_SAMESITE,
    )


def clear_refresh_cookie_header() -> dict[str, str]:
    """Cabecera ``Set-Cookie`` que borra la cookie, para las respuestas de error."""
    response = Response()
    clear_refresh_cookie(response)
    return {"Set-Cookie": response.headers["set-cookie"]}
