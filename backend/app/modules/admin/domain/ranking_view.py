"""Vistas de lectura del panel administrativo: ranking, resumen y mapa de calor (HU-08).

Son proyecciones de datos ya calculados por el motor de priorización: aquí no se calcula U
ni se decide el orden (lo fija ``priority/domain/ranking.py`` y la consulta SQL lo reproduce).
"""

import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Final

from app.modules.reports.domain.address import display_address
from app.modules.reports.domain.severity import Severity
from app.modules.reports.domain.status import ReportStatus

DEFAULT_PAGE_SIZE: Final = 20
MAX_PAGE_SIZE: Final = 100

# «Activo» = todo estado salvo Reparado (decisión 13).
ACTIVE_STATUSES: Final = frozenset(set(ReportStatus) - {ReportStatus.REPAIRED})


@dataclass(frozen=True, slots=True)
class RankingItem:
    """Fila del ranking. Cumple el protocolo ``Rankable`` del módulo de priorización."""

    report_id: uuid.UUID
    status: ReportStatus
    severity: Severity
    severity_score: Decimal
    flow_score: Decimal
    proximity_score: Decimal
    urgency_score: Decimal
    road_id: int | None
    road_name: str | None
    confirmations: int
    created_at: datetime

    @property
    def needs_road_review(self) -> bool:
        """Sin vía OSM a 30 m: F = 2 y el chip «Revisar vía» (guía 2.2)."""
        return self.road_id is None

    @property
    def address(self) -> str:
        return display_address(has_road=self.road_id is not None, road_name=self.road_name)


@dataclass(frozen=True, slots=True)
class RankingPage:
    items: Sequence[RankingItem]
    total: int


@dataclass(frozen=True, slots=True)
class StatusSummary:
    """Indicadores del encabezado: Activos · Evaluados · Priorizados · Reparados (propuesta 75)."""

    active: int
    evaluated: int
    prioritized: int
    repaired: int


@dataclass(frozen=True, slots=True)
class HeatPoint:
    """Punto del mapa de calor: coordenadas exactas (ruta solo para administradores)."""

    lat: float
    lon: float
    urgency_score: Decimal
