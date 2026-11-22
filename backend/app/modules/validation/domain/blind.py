"""Evaluación a ciegas (objetivo 4): lo que ve el evaluador y cómo se valida su orden.

El evaluador ordena los reportes congelados de cada zona sin ninguna información del motor
de priorización. Las estructuras de este módulo son la frontera: lo que no está aquí no
sale por la API del evaluador (U, S, F, P, jerarquía vial, distancias, confirmaciones,
estado, fechas, autor, orden del motor ni órdenes de otros evaluadores).
"""

import random
import uuid
from collections.abc import Collection, Sequence
from dataclasses import dataclass

from app.modules.critical_services.domain.service_type import CriticalServiceType
from app.modules.reports.domain.severity import Severity
from app.shared.domain.geo import GeoPoint


class NoOpenRoundError(Exception):
    """No hay una ronda de evaluación abierta."""


class ZoneNotInRoundError(Exception):
    """La zona no existe o no forma parte de la ronda abierta."""

    def __init__(self, zone_id: int) -> None:
        super().__init__(str(zone_id))
        self.zone_id = zone_id


class InvalidOrderError(ValueError):
    """El orden enviado no es exactamente el conjunto de reportes de la zona."""


class OrderAlreadySubmittedError(Exception):
    """El evaluador ya envió su orden para esa zona; no se puede cambiar."""


class BlindPhotoNotAvailableError(Exception):
    """El reporte no está en la ronda abierta o no tiene foto (misma respuesta, sin pistas)."""


@dataclass(frozen=True, slots=True)
class OpenRoundRef:
    round_id: uuid.UUID
    name: str
    # Semilla de la ronda: hace reproducible el orden inicial de cada evaluador.
    seed: int


@dataclass(frozen=True, slots=True)
class BlindZone:
    """Zona tal como la ve el evaluador: sin la concentración (insinuaría la hipótesis)."""

    id: int
    name: str
    n_reports: int


@dataclass(frozen=True, slots=True)
class EvaluatorZone:
    zone: BlindZone
    submitted: bool


@dataclass(frozen=True, slots=True)
class ServicePoint:
    """Servicio crítico cercano para el minimapa; sin la distancia calculada."""

    name: str | None
    type: CriticalServiceType
    location: GeoPoint


@dataclass(frozen=True, slots=True)
class BlindCard:
    """Tarjeta a ciegas de un reporte. No agregar campos sin revisar la vista a ciegas."""

    report_id: uuid.UUID
    description: str | None
    road_name: str | None
    severity: Severity
    location: GeoPoint
    nearby_services: list[ServicePoint]


@dataclass(frozen=True, slots=True)
class CurrentRoundView:
    round_id: uuid.UUID
    name: str
    zones: list[EvaluatorZone]


@dataclass(frozen=True, slots=True)
class ZoneView:
    zone: BlindZone
    cards: list[BlindCard]
    submitted: bool


def shuffle_for(
    report_ids: Collection[uuid.UUID], round_seed: int, evaluator_id: uuid.UUID
) -> list[uuid.UUID]:
    """Orden inicial de las tarjetas para un evaluador: aleatorio, distinto por evaluador y
    estable entre llamadas (no depende del orden en que lleguen los ids)."""
    ordered = sorted(report_ids)
    # Barajado reproducible, no criptográfico: solo evita sugerir un orden.
    random.Random(f"{round_seed}:{evaluator_id}").shuffle(ordered)  # noqa: S311
    return ordered


def validate_order(expected: Collection[uuid.UUID], submitted: Sequence[uuid.UUID]) -> None:
    """Lanza ``InvalidOrderError`` si ``submitted`` no es exactamente ``expected`` sin repetidos."""
    if not submitted:
        raise InvalidOrderError("El orden está vacío.")
    if len(set(submitted)) != len(submitted):
        raise InvalidOrderError("El orden repite reportes.")
    if set(submitted) != set(expected):
        raise InvalidOrderError("El orden no tiene exactamente los reportes de la zona.")
