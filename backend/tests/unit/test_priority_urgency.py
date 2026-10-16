"""Modelo U con los reportes de ejemplo del diseño (guía 8.3).

Los ejemplos son fixtures ilustrativos, no datos reales. La distancia de cada
uno se eligió para producir la P del diseño. En "Carrera 27" el diseño muestra
P = 3,8 redondeado: U = 7,25 corresponde a P = 3,75 (d = 350 m).
"""

from dataclasses import dataclass
from decimal import Decimal

import pytest

from app.modules.critical_services.domain.entities import NearestCriticalService
from app.modules.critical_services.domain.service_type import CriticalServiceType
from app.modules.priority.domain.urgency import (
    EvaluationInput,
    FactorRules,
    PriorityModel,
)
from app.modules.priority.domain.weights import DEFAULT_WEIGHTS, Weights
from app.modules.reports.domain.severity import Severity
from app.modules.roads.domain.classification import flow_factor
from app.modules.roads.domain.entities import RoadMatch
from app.modules.roads.domain.road_class import RoadClass

ROAD_ID = 7
SERVICE_ID = 3


def _road(road_class: RoadClass) -> RoadMatch:
    return RoadMatch(
        road_id=ROAD_ID,
        name="Vía de prueba",
        road_class=road_class,
        flow_factor=flow_factor(road_class),
        distance_m=8.0,
    )


def _service(distance_m: float) -> NearestCriticalService:
    return NearestCriticalService(
        service_id=SERVICE_ID,
        name="Servicio de prueba",
        service_type=CriticalServiceType.HOSPITAL,
        distance_m=distance_m,
    )


@dataclass(frozen=True)
class DesignExample:
    name: str
    data: EvaluationInput
    s: str
    f: str
    p: str
    u: str


DESIGN_EXAMPLES = [
    DesignExample(
        "Av. Los Estudiantes",
        EvaluationInput(Severity.HIGH, _road(RoadClass.SECONDARY), _service(180.0)),
        "10", "7", "8.00", "8.70",
    ),
    DesignExample(
        "Calle 16 con Panamericana",
        EvaluationInput(Severity.MEDIUM, _road(RoadClass.PRIMARY), _service(60.0)),
        "6", "10", "10", "8.00",
    ),
    DesignExample(
        "Carrera 27",
        EvaluationInput(Severity.HIGH, _road(RoadClass.TERTIARY), _service(350.0)),
        "10", "5", "3.75", "7.25",
    ),
    DesignExample(
        "Calle 18 con Carrera 27",
        EvaluationInput(Severity.MEDIUM, _road(RoadClass.TERTIARY), _service(90.0)),
        "6", "5", "10", "6.50",
    ),
    DesignExample(
        "Carrera 22",
        EvaluationInput(Severity.MEDIUM, _road(RoadClass.SECONDARY), _service(300.0)),
        "6", "7", "5.00", "6.10",
    ),
    DesignExample(
        "Sector Obonuco (sin vía)",
        EvaluationInput(Severity.MEDIUM, road=None, nearest_service=None),
        "6", "2", "0", "3.60",
    ),
]  # fmt: skip


@pytest.mark.parametrize("example", DESIGN_EXAMPLES, ids=lambda example: example.name)
def test_design_examples_produce_the_expected_urgency(example: DesignExample) -> None:
    result = PriorityModel(DEFAULT_WEIGHTS).evaluate(example.data)

    assert result.severity_score == Decimal(example.s)
    assert result.flow_score == Decimal(example.f)
    assert result.proximity_score == Decimal(example.p)
    assert result.urgency_score == Decimal(example.u)


def test_report_without_road_is_marked_for_review() -> None:
    result = PriorityModel(DEFAULT_WEIGHTS).evaluate(DESIGN_EXAMPLES[-1].data)

    assert result.needs_road_review is True
    assert result.road_id is None
    assert result.service_id is None
    assert result.service_distance_m is None


def test_evaluation_keeps_the_data_needed_to_reproduce_it() -> None:
    result = PriorityModel(DEFAULT_WEIGHTS).evaluate(DESIGN_EXAMPLES[0].data)

    assert result.needs_road_review is False
    assert result.road_id == ROAD_ID
    assert result.service_id == SERVICE_ID
    assert result.service_distance_m == Decimal("180.00")
    assert result.weights == DEFAULT_WEIGHTS
    w = result.weights
    recomputed = (
        w.severity * result.severity_score
        + w.flow * result.flow_score
        + w.proximity * result.proximity_score
    )
    assert recomputed == result.urgency_score


def test_proximity_uses_the_stored_rounded_distance() -> None:
    # 349,996 m se guarda como 350,00 m; P debe salir de ese valor (3,75), no de 349,996.
    data = EvaluationInput(Severity.HIGH, _road(RoadClass.TERTIARY), _service(349.996))
    result = PriorityModel(DEFAULT_WEIGHTS).evaluate(data)

    assert result.service_distance_m == Decimal("350.00")
    assert result.proximity_score == Decimal("3.75")


def test_other_weights_change_the_urgency() -> None:
    severity_only = Weights(Decimal("1"), Decimal("0"), Decimal("0"))
    result = PriorityModel(severity_only).evaluate(DESIGN_EXAMPLES[0].data)

    assert result.urgency_score == Decimal("10.00")


def test_urgency_stays_within_zero_and_ten() -> None:
    model = PriorityModel(DEFAULT_WEIGHTS)
    highest = model.evaluate(
        EvaluationInput(Severity.HIGH, _road(RoadClass.PRIMARY), _service(0.0))
    )
    lowest = model.evaluate(EvaluationInput(Severity.LOW, road=None, nearest_service=None))

    assert highest.urgency_score == Decimal("10.00")
    assert lowest.urgency_score == Decimal("2.10")


def test_evaluation_is_deterministic() -> None:
    model = PriorityModel(DEFAULT_WEIGHTS)
    data = DESIGN_EXAMPLES[2].data

    first_result = model.evaluate(data)
    second_result = model.evaluate(data)

    assert first_result == second_result


def test_factor_rules_can_be_replaced() -> None:
    # Strategy: un ajuste del panel de expertos cambia una regla sin tocar el modelo.
    rules = FactorRules(severity=lambda _: Decimal("8"))
    result = PriorityModel(DEFAULT_WEIGHTS, rules).evaluate(DESIGN_EXAMPLES[0].data)

    assert result.severity_score == Decimal("8")
    assert result.urgency_score == Decimal("7.70")
