"""Rondas de evaluación (objetivo 4): muestra reproducible de reportes congelados por zona.

Una ronda congela los reportes activos de cada zona del piloto con su U y el orden que les da
el motor, para que el panel de expertos ordene el mismo conjunto fijo a ciegas.
"""

import random
import uuid
from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from app.modules.priority.domain.ranking import ranking_key
from app.modules.reports.domain.severity import Severity
from app.modules.validation.domain.parameters import MIN_REPORTS_PER_ZONE
from app.modules.validation.domain.zones import Concentration


class RoundStatus(StrEnum):
    OPEN = "abierta"
    CLOSED = "cerrada"


class ZoneTooSmallError(Exception):
    """Una zona tiene menos reportes elegibles que el mínimo del estudio."""

    def __init__(self, zone_name: str, count: int) -> None:
        super().__init__(f"La zona «{zone_name}» tiene {count} reportes elegibles.")
        self.zone_name = zone_name
        self.count = count


class NoZonesError(Exception):
    """No hay zonas de validación cargadas."""


class RoundAlreadyOpenError(Exception):
    """Ya existe una ronda abierta; solo puede haber una a la vez."""


class RoundNotFoundError(Exception):
    def __init__(self, round_id: uuid.UUID) -> None:
        super().__init__(str(round_id))
        self.round_id = round_id


class RoundAlreadyClosedError(Exception):
    def __init__(self, round_id: uuid.UUID) -> None:
        super().__init__(str(round_id))
        self.round_id = round_id


@dataclass(frozen=True, slots=True)
class RoundCandidate:
    """Reporte activo con U guardada y dentro de una zona; cumple ``Rankable``."""

    report_id: uuid.UUID
    zone_id: int
    urgency_score: Decimal
    severity: Severity
    confirmations: int
    created_at: datetime


@dataclass(frozen=True, slots=True)
class RoundEntry:
    report_id: uuid.UUID
    zone_id: int
    urgency_score: Decimal
    motor_order: int


@dataclass(frozen=True, slots=True)
class EvaluatorLabel:
    """Etiqueta anónima «Evaluador k»; nunca se expone el nombre ni el correo."""

    number: int

    @property
    def text(self) -> str:
        return f"Evaluador {self.number}"


def number_evaluators(first_submission: Mapping[uuid.UUID, datetime]) -> dict[uuid.UUID, int]:
    """Numera a los evaluadores («Evaluador k») por su primer envío en la ronda; el id
    desempata. Así el número es estable y no revela quién es quién."""
    ordered = sorted(first_submission, key=lambda user: (first_submission[user], user))
    return {user: k for k, user in enumerate(ordered, start=1)}


@dataclass(frozen=True, slots=True)
class ZoneProgress:
    zone_id: int
    name: str
    concentration: Concentration
    n_reports: int
    submitted_by: list[EvaluatorLabel]


@dataclass(frozen=True, slots=True)
class RoundSummary:
    round_id: uuid.UUID
    name: str
    status: RoundStatus
    sample_size: int
    opened_at: datetime
    closed_at: datetime | None


@dataclass(frozen=True, slots=True)
class RoundProgress:
    summary: RoundSummary
    zones: list[ZoneProgress]

    @property
    def round_id(self) -> uuid.UUID:
        return self.summary.round_id


def sample_and_rank(
    candidates: Sequence[RoundCandidate],
    sample_size: int,
    seed: int,
    zone_names: Mapping[int, str] | None = None,
) -> list[RoundEntry]:
    """Sortea la muestra de cada zona y la ordena como el motor (1..n por zona).

    Con la misma semilla y los mismos candidatos el resultado es idéntico: se parte de los
    candidatos ordenados por id y cada zona usa su propio generador (``seed + zone_id``).
    ``zone_names`` (id → nombre) incluye también las zonas sin candidatos para validarlas y
    reportar la primera, por nombre, que quede por debajo del mínimo.
    """
    by_zone: dict[int, list[RoundCandidate]] = defaultdict(list)
    for candidate in candidates:
        by_zone[candidate.zone_id].append(candidate)
    names = dict(zone_names) if zone_names is not None else {z: str(z) for z in by_zone}

    for zone_id in sorted(names, key=lambda z: names[z]):
        count = len(by_zone.get(zone_id, ()))
        if count < MIN_REPORTS_PER_ZONE:
            raise ZoneTooSmallError(names[zone_id], count)

    entries: list[RoundEntry] = []
    for zone_id in sorted(by_zone):
        pool = sorted(by_zone[zone_id], key=lambda c: c.report_id)
        if len(pool) > sample_size:
            pool = random.Random(seed + zone_id).sample(  # noqa: S311 - muestra reproducible y no criptográfica
                pool, sample_size
            )
        # El id cierra los empates totales para que el orden sea determinista.
        ordered = sorted(pool, key=lambda c: (ranking_key(c), c.report_id))
        entries.extend(
            RoundEntry(c.report_id, zone_id, c.urgency_score, position)
            for position, c in enumerate(ordered, start=1)
        )
    return entries
