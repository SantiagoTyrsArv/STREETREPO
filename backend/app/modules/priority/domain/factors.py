"""Normalización de los factores S, F y P a la escala 0-10 (guía 2.2).

Cada regla es una función intercambiable (patrón Strategy): si el panel de
expertos ajusta una normalización, se reemplaza la función sin tocar el modelo.
"""

from decimal import ROUND_HALF_UP, Decimal
from types import MappingProxyType
from typing import Final

from app.modules.reports.domain.severity import Severity
from app.modules.roads.domain.classification import flow_factor
from app.modules.roads.domain.entities import RoadMatch
from app.modules.roads.domain.road_class import RoadClass
from app.shared.domain.geo_parameters import (
    PROXIMITY_FULL_SCORE_RADIUS_M,
    PROXIMITY_MAX_RADIUS_M,
)

# Puntajes y distancias se guardan con dos decimales (NUMERIC(4, 2) y (8, 2)).
SCORE_PRECISION: Final = Decimal("0.01")
DISTANCE_PRECISION: Final = Decimal("0.01")

MAX_SCORE: Final = Decimal("10")
MIN_SCORE: Final = Decimal("0")

SEVERITY_SCORES: MappingProxyType[Severity, Decimal] = MappingProxyType(
    {
        Severity.LOW: Decimal("3"),
        Severity.MEDIUM: Decimal("6"),
        Severity.HIGH: Decimal("10"),
    }
)

# Sin vía OSM a 30 m se asume el flujo más bajo (F = 2) y se marca "Revisar vía".
NO_ROAD_FLOW_SCORE: Final = flow_factor(RoadClass.RESIDENTIAL)

_FULL_SCORE_RADIUS: Final = Decimal(str(PROXIMITY_FULL_SCORE_RADIUS_M))
_MAX_RADIUS: Final = Decimal(str(PROXIMITY_MAX_RADIUS_M))


def round_score(value: Decimal) -> Decimal:
    return value.quantize(SCORE_PRECISION, rounding=ROUND_HALF_UP)


def round_distance(distance_m: float) -> Decimal:
    """Distancia en metros con dos decimales, tal como se guarda en la evaluación."""
    if distance_m < 0:
        raise ValueError("La distancia no puede ser negativa")
    return Decimal(str(distance_m)).quantize(DISTANCE_PRECISION, rounding=ROUND_HALF_UP)


def severity_score(severity: Severity) -> Decimal:
    """S: baja = 3, media = 6, alta = 10."""
    return SEVERITY_SCORES[severity]


def flow_score(road: RoadMatch | None) -> Decimal:
    """F: factor de flujo de la vía asociada, o 2 si no hay vía a 30 m."""
    if road is None:
        return NO_ROAD_FLOW_SCORE
    return road.flow_factor


def proximity_score(distance_m: Decimal | None) -> Decimal:
    """P: 10 hasta 100 m, decrece linealmente y vale 0 desde 500 m.

    ``None`` significa que no hay servicio crítico dentro del radio máximo.
    Recibe la distancia ya redondeada para que P se pueda reproducir con los
    valores guardados en la evaluación.
    """
    if distance_m is None or distance_m >= _MAX_RADIUS:
        return MIN_SCORE
    if distance_m < 0:
        raise ValueError("La distancia no puede ser negativa")
    if distance_m <= _FULL_SCORE_RADIUS:
        return MAX_SCORE
    span = _MAX_RADIUS - _FULL_SCORE_RADIUS
    return round_score(MAX_SCORE * (_MAX_RADIUS - distance_m) / span)
