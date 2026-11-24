"""Límite global de solicitudes por IP (decisión 30c, guía 7.3).

Frena a un solo cliente que inunde la API, sea cual sea la ruta. Es holgado a propósito:
muchos ciudadanos salen a internet con la misma IP (CGNAT de los operadores móviles, red
de la universidad) y el panel pide varias miniaturas por pantalla. Los límites por ruta
(login, registro, reportes, mapa) siguen siendo los que frenan el abuso de cada función.

Las sondas de Docker (``/health``, ``/ready``) y la documentación nunca se limitan: un
contenedor sano no debe marcarse como enfermo porque su IP agotó el cupo.
"""

import json
from typing import Final

from starlette.types import ASGIApp, Receive, Scope, Send

from app.core.errors import error_body
from app.core.rate_limiting import retry_after_seconds
from app.shared.application.clock import Clock
from app.shared.application.rate_limit import RateLimit, RateLimiter, RateLimitExceededError

GLOBAL_RATE_LIMIT_EXEMPT_PATHS: Final[frozenset[str]] = frozenset(
    {"/health", "/ready", "/docs", "/openapi.json"}
)
_UNKNOWN_CLIENT: Final = "desconocido"
_MESSAGE: Final = "Demasiadas solicitudes desde tu conexión. Intenta de nuevo en unos minutos."


class GlobalRateLimitMiddleware:
    """Cuenta cada solicitud HTTP contra el cupo de la IP del cliente."""

    def __init__(
        self,
        app: ASGIApp,
        *,
        limiter: RateLimiter,
        limit: RateLimit,
        clock: Clock,
        exempt_paths: frozenset[str] = GLOBAL_RATE_LIMIT_EXEMPT_PATHS,
    ) -> None:
        self._app = app
        self._limiter = limiter
        self._limit = limit
        self._clock = clock
        self._exempt_paths = exempt_paths

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope["path"] in self._exempt_paths:
            await self._app(scope, receive, send)
            return
        client = scope.get("client")
        host = client[0] if client else _UNKNOWN_CLIENT
        try:
            self._limiter.hit(f"global:{host}", self._limit, self._clock.now())
        except RateLimitExceededError as exc:
            await _reply_too_many(send, retry_after_seconds(exc.retry_after))
            return
        await self._app(scope, receive, send)


async def _reply_too_many(send: Send, seconds: int) -> None:
    body = json.dumps(
        error_body("RATE_LIMITED", _MESSAGE, {"retry_after_s": seconds}), ensure_ascii=False
    ).encode()
    await send(
        {
            "type": "http.response.start",
            "status": 429,
            "headers": [
                (b"content-type", b"application/json"),
                (b"content-length", str(len(body)).encode()),
                (b"retry-after", str(seconds).encode()),
            ],
        }
    )
    await send({"type": "http.response.body", "body": body})
