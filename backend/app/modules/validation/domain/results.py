"""Resultados de una ronda cerrada y datos para la ficha comparativa (objetivo 4, HU-09).

Los datos crudos salen de la base (``RoundResultsReader``); las cifras, de las funciones
puras de ``agreement``. Los evaluadores solo aparecen como «Evaluador k» (Ley 1581).
"""

import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal

from app.modules.reports.domain.status import ReportStatus
from app.modules.validation.domain.agreement import BetweenZones, NotComputable, ZoneAgreement
from app.modules.validation.domain.rounds import RoundEntry, RoundSummary
from app.modules.validation.domain.warnings import WarningDecision
from app.modules.validation.domain.zones import Concentration


class RoundStillOpenError(Exception):
    """Los resultados de una ronda se calculan cuando ya no recibe órdenes."""

    def __init__(self, round_id: uuid.UUID) -> None:
        super().__init__(str(round_id))
        self.round_id = round_id


@dataclass(frozen=True, slots=True)
class DedupSummary:
    """Deduplicación de una zona: todos sus reportes, no solo la muestra de la ronda.

    Los avisos son los de «Posible duplicado» cuyo punto cayó en la zona (diseño, 8.1);
    ``warnings_pending`` son los que siguen «sin decisión».
    """

    reports: int
    reports_confirmed: int
    confirmations: int
    warnings_total: int
    warnings_confirmed: int
    warnings_created_anyway: int
    warnings_pending: int


@dataclass(frozen=True, slots=True)
class ZoneRoundData:
    """Una zona de la ronda: sus reportes congelados con el orden del motor y los órdenes
    que envió cada evaluador (1 = más urgente)."""

    zone_id: int
    name: str
    concentration: Concentration
    entries: Sequence[RoundEntry]
    evaluator_orders: Mapping[uuid.UUID, Mapping[uuid.UUID, int]]
    dedup: DedupSummary
    # Vía de cada reporte, para que el administrador lo reconozca; None = sin vía asociada.
    road_names: Mapping[uuid.UUID, str | None] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class RoundData:
    summary: RoundSummary
    zones: Sequence[ZoneRoundData]
    # Número de «Evaluador k» de cada evaluador, el mismo del avance de la ronda.
    evaluator_numbers: Mapping[uuid.UUID, int]


@dataclass(frozen=True, slots=True)
class ZoneResult:
    zone: ZoneRoundData
    # None si ningún evaluador envió el orden de esta zona.
    agreement: ZoneAgreement | None

    @property
    def dedup(self) -> DedupSummary:
        return self.zone.dedup


@dataclass(frozen=True, slots=True)
class RoundResults:
    round: RoundSummary
    zones: Sequence[ZoneResult]
    between: BetweenZones | NotComputable
    evaluator_numbers: Mapping[uuid.UUID, int]


@dataclass(frozen=True, slots=True)
class ReviewReport:
    """Fila de la revisión manual de duplicados: un reporte de una zona de la ronda."""

    report_id: uuid.UUID
    zone_name: str
    created_at: datetime
    road_name: str | None
    status: ReportStatus
    confirmations: int


@dataclass(frozen=True, slots=True)
class WarningCandidate:
    report_id: uuid.UUID
    distance_m: Decimal


@dataclass(frozen=True, slots=True)
class ReviewWarning:
    """Fila de la revisión manual: un aviso mostrado en una zona y qué decidió el ciudadano."""

    warning_id: uuid.UUID
    zone_name: str
    shown_at: datetime
    decision: WarningDecision
    resulting_report_id: uuid.UUID | None
    candidates: Sequence[WarningCandidate]
