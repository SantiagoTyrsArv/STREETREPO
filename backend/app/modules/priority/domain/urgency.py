"""Modelo de urgencia U = w1·S + w2·F + w3·P en escala 0-10 (guía 2.2)."""

from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal

from app.modules.critical_services.domain.entities import NearestCriticalService
from app.modules.priority.domain import factors
from app.modules.priority.domain.weights import Weights
from app.modules.reports.domain.severity import Severity
from app.modules.roads.domain.entities import RoadMatch


@dataclass(frozen=True, slots=True)
class FactorRules:
    """Estrategias de normalización de cada factor; por defecto, las de la tesis."""

    severity: Callable[[Severity], Decimal] = factors.severity_score
    flow: Callable[[RoadMatch | None], Decimal] = factors.flow_score
    proximity: Callable[[Decimal | None], Decimal] = factors.proximity_score


@dataclass(frozen=True, slots=True)
class EvaluationInput:
    """Datos de un reporte necesarios para calcular su urgencia."""

    severity: Severity
    # None = no hay vía OSM a 30 m.
    road: RoadMatch | None
    # None = no hay servicio crítico a 500 m.
    nearest_service: NearestCriticalService | None


@dataclass(frozen=True, slots=True)
class UrgencyEvaluation:
    """Resultado reproducible: factores, pesos usados y U (guía 4.5)."""

    severity_score: Decimal
    flow_score: Decimal
    proximity_score: Decimal
    urgency_score: Decimal
    weights: Weights
    road_id: int | None
    service_id: int | None
    service_distance_m: Decimal | None

    @property
    def needs_road_review(self) -> bool:
        """Marca "Revisar vía": no se encontró vía OSM a 30 m y se asumió F = 2."""
        return self.road_id is None


class PriorityModel:
    """Calcula la urgencia de un reporte con unos pesos y reglas dados.

    Es puro y determinista: los mismos datos producen siempre el mismo resultado.
    Las confirmaciones no intervienen (guía 2.2): solo sirven para desempatar.
    """

    def __init__(self, weights: Weights, rules: FactorRules | None = None) -> None:
        self._weights = weights
        self._rules = rules or FactorRules()

    @property
    def weights(self) -> Weights:
        return self._weights

    def evaluate(self, data: EvaluationInput) -> UrgencyEvaluation:
        service = data.nearest_service
        distance = None if service is None else factors.round_distance(service.distance_m)
        s = self._rules.severity(data.severity)
        f = self._rules.flow(data.road)
        p = self._rules.proximity(distance)
        w = self._weights
        u = factors.round_score(w.severity * s + w.flow * f + w.proximity * p)
        return UrgencyEvaluation(
            severity_score=s,
            flow_score=f,
            proximity_score=p,
            urgency_score=u,
            weights=w,
            road_id=None if data.road is None else data.road.road_id,
            service_id=None if service is None else service.service_id,
            service_distance_m=distance,
        )
