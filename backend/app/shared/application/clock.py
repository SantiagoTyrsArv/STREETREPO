"""Reloj inyectable: los casos de uso no llaman a ``datetime.now()`` directamente."""

from datetime import UTC, datetime
from typing import Protocol


class Clock(Protocol):
    def now(self) -> datetime:
        """Fecha y hora actual con zona horaria (UTC)."""
        ...


class SystemClock:
    def now(self) -> datetime:
        return datetime.now(UTC)
