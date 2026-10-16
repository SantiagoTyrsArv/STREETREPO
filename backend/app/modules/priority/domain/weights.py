"""Pesos del modelo de urgencia U = w1·S + w2·F + w3·P (guía 2.2)."""

from dataclasses import dataclass
from decimal import Decimal
from typing import Final

# Los pesos se guardan como NUMERIC(3, 2): dos decimales exactos, sin coma flotante.
WEIGHT_PRECISION: Final = Decimal("0.01")
_MIN_WEIGHT: Final = Decimal("0")
_MAX_WEIGHT: Final = Decimal("1")
_REQUIRED_SUM: Final = Decimal("1.00")


class InvalidWeightsError(ValueError):
    """Pesos fuera de rango, con más de dos decimales o que no suman 1,00."""


def _check_weight(name: str, value: Decimal) -> None:
    if not value.is_finite():
        raise InvalidWeightsError(f"El peso de {name} no es un número válido")
    if value.quantize(WEIGHT_PRECISION) != value:
        raise InvalidWeightsError(f"El peso de {name} admite como máximo dos decimales")
    if not _MIN_WEIGHT <= value <= _MAX_WEIGHT:
        raise InvalidWeightsError(f"El peso de {name} debe estar entre 0 y 1")


@dataclass(frozen=True, slots=True)
class Weights:
    """Pesos de severidad, flujo y proximidad. Deben sumar exactamente 1,00.

    Se validan aquí (además del ``CHECK`` de la base) para que la regla viva en el
    dominio y no solo en la interfaz (guía 2.2).
    """

    severity: Decimal
    flow: Decimal
    proximity: Decimal

    def __post_init__(self) -> None:
        _check_weight("severidad", self.severity)
        _check_weight("flujo", self.flow)
        _check_weight("proximidad", self.proximity)
        total = self.severity + self.flow + self.proximity
        if total != _REQUIRED_SUM:
            raise InvalidWeightsError(f"Los pesos deben sumar 1,00 (suman {total})")


# Pesos de la tesis: U = 0,5·S + 0,3·F + 0,2·P.
DEFAULT_WEIGHTS: Final = Weights(
    severity=Decimal("0.50"), flow=Decimal("0.30"), proximity=Decimal("0.20")
)
