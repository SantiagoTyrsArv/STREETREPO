"""Detalle del reporte para el administrador (pantalla «Detalle y estado», HU-08 y HU-12).

Reúne la evidencia, la vía OSM, el servicio crítico más cercano, el desglose del cálculo
con los pesos de la versión usada y el historial con su autor. El nombre del reportante
solo se muestra en el panel (guía 7.2 y 10.3).
"""

import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from app.modules.reports.domain.address import display_address
from app.modules.reports.domain.severity import Severity
from app.modules.reports.domain.status import ReportStatus
from app.modules.reports.domain.status_machine import SYSTEM_TRANSITIONS, allowed_next_statuses
from app.shared.domain.geo import GeoPoint


def admin_next_statuses(current: ReportStatus) -> tuple[ReportStatus, ...]:
    """Estados a los que un administrador puede llevar el reporte.

    Sale de la máquina de estados sin las transiciones que solo hace el sistema
    (Registrado → Evaluado), para que el panel no ofrezca opciones que el servidor rechaza.
    """
    return tuple(
        new for new in allowed_next_statuses(current) if (current, new) not in SYSTEM_TRANSITIONS
    )


@dataclass(frozen=True, slots=True)
class RoadInfo:
    name: str | None
    highway: str


@dataclass(frozen=True, slots=True)
class NearestService:
    name: str | None
    service_type: str
    distance_m: Decimal


@dataclass(frozen=True, slots=True)
class EvaluationBreakdown:
    """Evaluación vigente: S, F, P y U con los pesos de la versión con que se calculó."""

    severity_score: Decimal
    flow_score: Decimal
    proximity_score: Decimal
    urgency_score: Decimal
    w_severity: Decimal
    w_flow: Decimal
    w_proximity: Decimal
    config_id: int
    # None = ningún servicio crítico a menos de 500 m (P = 0).
    service: NearestService | None
    calculated_at: datetime


@dataclass(frozen=True, slots=True)
class AdminHistoryEntry:
    previous_status: ReportStatus | None
    status: ReportStatus
    changed_at: datetime
    note: str | None
    # None = el cambio lo hizo el sistema (o la cuenta se suprimió).
    changed_by_name: str | None


@dataclass(frozen=True, slots=True)
class AdminReportDetail:
    id: uuid.UUID
    status: ReportStatus
    severity: Severity
    description: str | None
    location: GeoPoint
    road: RoadInfo | None
    reporter_name: str
    created_at: datetime
    confirmations: int
    # None = el motor aún no lo evaluó.
    evaluation: EvaluationBreakdown | None
    history: Sequence[AdminHistoryEntry]

    @property
    def allowed_next_statuses(self) -> tuple[ReportStatus, ...]:
        return admin_next_statuses(self.status)

    @property
    def needs_road_review(self) -> bool:
        return self.road is None

    @property
    def address(self) -> str:
        return display_address(
            has_road=self.road is not None, road_name=self.road.name if self.road else None
        )
