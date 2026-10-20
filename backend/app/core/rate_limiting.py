"""Límite de solicitudes por IP para rutas sensibles (guía 7.3).

Cada aplicación lleva su propio limitador en ``app.state`` (se crea en ``create_app``):
las pruebas no comparten cuentas entre sí y no hay estado global.
"""

import math
from collections.abc import Callable
from datetime import timedelta
from typing import Annotated

from fastapi import Depends, Request, status

from app.core.errors import AppError
from app.shared.application.clock import SystemClock
from app.shared.application.rate_limit import RateLimit, RateLimiter, RateLimitExceededError

# Holgado a propósito: en la universidad o en redes móviles muchos ciudadanos salen a
# internet con la misma IP (NAT). El bloqueo por cuenta es el que frena la fuerza bruta.
# El cupo de registro es configurable (`REGISTER_PER_IP_PER_HOUR`, decisión 58).
LOGIN_LIMIT_PER_IP = RateLimit(max_requests=30, window=timedelta(minutes=5))

_UNKNOWN_CLIENT = "desconocido"


def get_rate_limiter(request: Request) -> RateLimiter:
    limiter: RateLimiter = request.app.state.rate_limiter
    return limiter


RateLimiterDep = Annotated[RateLimiter, Depends(get_rate_limiter)]


def retry_after_seconds(retry_after: timedelta) -> int:
    """Segundos enteros para la cabecera ``Retry-After``, redondeados hacia arriba."""
    return max(1, math.ceil(retry_after.total_seconds()))


def too_many_requests(code: str, message: str, retry_after: timedelta) -> AppError:
    seconds = retry_after_seconds(retry_after)
    return AppError(
        code,
        message,
        status.HTTP_429_TOO_MANY_REQUESTS,
        {"retry_after_s": seconds},
        headers={"Retry-After": str(seconds)},
    )


def limit_per_client_ip(scope: str, limit: RateLimit) -> Callable[[Request, RateLimiter], None]:
    """Dependencia que cuenta la solicitud contra el cupo de la IP del cliente en ``scope``.

    Detrás de un proxy inverso, la IP real llega solo si uvicorn confía en él
    (``--proxy-headers`` y ``FORWARDED_ALLOW_IPS``); si no, todos compartirían el cupo.
    """

    def dependency(request: Request, limiter: RateLimiterDep) -> None:
        client = request.client.host if request.client else _UNKNOWN_CLIENT
        try:
            limiter.hit(f"{scope}:{client}", limit, SystemClock().now())
        except RateLimitExceededError as exc:
            raise too_many_requests(
                "RATE_LIMITED",
                "Demasiadas solicitudes desde tu conexión. Intenta de nuevo en unos minutos.",
                exc.retry_after,
            ) from exc

    return dependency
