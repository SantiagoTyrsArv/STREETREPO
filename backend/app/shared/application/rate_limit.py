"""Puerto de límite de solicitudes por ventana deslizante (guía 7.3, anti abuso)."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Protocol


@dataclass(frozen=True, slots=True)
class RateLimit:
    """Como máximo ``max_requests`` solicitudes dentro de cualquier ventana de ``window``."""

    max_requests: int
    window: timedelta

    def __post_init__(self) -> None:
        if self.max_requests < 1:
            raise ValueError("max_requests debe ser al menos 1")
        if self.window <= timedelta(0):
            raise ValueError("window debe ser positiva")


class RateLimitExceededError(Exception):
    """Se superó el límite; ``retry_after`` dice cuánto falta para que se libere un cupo."""

    def __init__(self, retry_after: timedelta) -> None:
        super().__init__(f"Límite superado; reintentar en {retry_after}")
        self.retry_after = retry_after


class RateLimiter(Protocol):
    def hit(self, key: str, limit: RateLimit, now: datetime) -> None:
        """Cuenta una solicitud de ``key``. Lanza ``RateLimitExceededError`` si no hay cupo;
        una solicitud rechazada no consume cupo."""
        ...
