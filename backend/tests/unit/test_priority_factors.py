from decimal import Decimal

import pytest

from app.modules.priority.domain.factors import (
    NO_ROAD_FLOW_SCORE,
    flow_score,
    proximity_score,
    round_distance,
    severity_score,
)
from app.modules.reports.domain.severity import Severity
from app.modules.roads.domain.entities import RoadMatch
from app.modules.roads.domain.road_class import RoadClass


@pytest.mark.parametrize(
    ("severity", "expected"),
    [(Severity.LOW, "3"), (Severity.MEDIUM, "6"), (Severity.HIGH, "10")],
)
def test_severity_is_normalized(severity: Severity, expected: str) -> None:
    assert severity_score(severity) == Decimal(expected)


@pytest.mark.parametrize(
    ("road_class", "flow"),
    [
        (RoadClass.PRIMARY, "10"),
        (RoadClass.SECONDARY, "7"),
        (RoadClass.TERTIARY, "5"),
        (RoadClass.RESIDENTIAL, "2"),
    ],
)
def test_flow_comes_from_the_matched_road(road_class: RoadClass, flow: str) -> None:
    road = RoadMatch(
        road_id=1, name=None, road_class=road_class, flow_factor=Decimal(flow), distance_m=12.0
    )
    assert flow_score(road) == Decimal(flow)


def test_flow_without_road_is_two() -> None:
    assert Decimal("2") == NO_ROAD_FLOW_SCORE
    assert flow_score(None) == Decimal("2")


@pytest.mark.parametrize(
    ("distance", "expected"),
    [
        ("0", "10"),
        ("99.99", "10"),
        ("100", "10"),  # borde: d = 100 m
        ("100.01", "10.00"),  # 9,99975 redondea a 10,00
        ("101", "9.98"),
        ("180", "8.00"),
        ("300", "5.00"),
        ("350", "3.75"),
        ("499.99", "0.00"),  # 0,00025 redondea a 0
        ("499", "0.03"),
        ("500", "0"),  # borde: d = 500 m
        ("750", "0"),
    ],
)
def test_proximity_decreases_linearly_between_100_and_500_m(distance: str, expected: str) -> None:
    assert proximity_score(Decimal(distance)) == Decimal(expected)


def test_proximity_without_critical_service_is_zero() -> None:
    assert proximity_score(None) == Decimal("0")


def test_proximity_rejects_negative_distances() -> None:
    with pytest.raises(ValueError, match="negativa"):
        proximity_score(Decimal("-1"))


@pytest.mark.parametrize(
    ("distance", "expected"),
    [(0.0, "0.00"), (180.004, "180.00"), (180.005, "180.01"), (349.999, "350.00")],
)
def test_distance_is_rounded_to_centimeters(distance: float, expected: str) -> None:
    assert round_distance(distance) == Decimal(expected)


def test_round_distance_rejects_negative_values() -> None:
    with pytest.raises(ValueError, match="negativa"):
        round_distance(-0.5)
