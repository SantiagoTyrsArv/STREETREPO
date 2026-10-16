"""Orden del ranking de priorización (guía 2.2).

Mayor U primero; en empate, mayor severidad → más confirmaciones → reporte más
antiguo. La consulta SQL del ranking (fase 6) debe reproducir este mismo orden.
"""

from collections.abc import Iterable
from datetime import datetime
from decimal import Decimal
from typing import Protocol

from app.modules.reports.domain.severity import Severity


class Rankable(Protocol):
    @property
    def urgency_score(self) -> Decimal: ...

    @property
    def severity(self) -> Severity: ...

    @property
    def confirmations(self) -> int: ...

    @property
    def created_at(self) -> datetime: ...


def ranking_key(item: Rankable) -> tuple[Decimal, int, int, datetime]:
    """Clave de orden ascendente: los criterios "mayor" van negados."""
    return (-item.urgency_score, -item.severity, -item.confirmations, item.created_at)


def rank[T: Rankable](items: Iterable[T]) -> list[T]:
    return sorted(items, key=ranking_key)
