from decimal import Decimal

import pytest

from app.modules.priority.domain.weights import DEFAULT_WEIGHTS, InvalidWeightsError, Weights


def _weights(severity: str, flow: str, proximity: str) -> Weights:
    return Weights(Decimal(severity), Decimal(flow), Decimal(proximity))


def test_default_weights_are_the_thesis_weights() -> None:
    assert _weights("0.50", "0.30", "0.20") == DEFAULT_WEIGHTS


@pytest.mark.parametrize(
    ("severity", "flow", "proximity"),
    [("1", "0", "0"), ("0", "0", "1"), ("0.34", "0.33", "0.33"), ("0.6", "0.25", "0.15")],
)
def test_weights_that_sum_one_are_valid(severity: str, flow: str, proximity: str) -> None:
    weights = _weights(severity, flow, proximity)
    assert weights.severity + weights.flow + weights.proximity == Decimal("1")


@pytest.mark.parametrize(
    ("severity", "flow", "proximity"),
    [
        ("0.50", "0.30", "0.30"),  # suman 1,10
        ("0.50", "0.30", "0.10"),  # suman 0,90
        ("0.33", "0.33", "0.33"),  # suman 0,99
        ("0", "0", "0"),
    ],
)
def test_weights_that_do_not_sum_one_are_rejected(severity: str, flow: str, proximity: str) -> None:
    with pytest.raises(InvalidWeightsError, match="sumar 1,00"):
        _weights(severity, flow, proximity)


@pytest.mark.parametrize(
    ("severity", "flow", "proximity"),
    [("1.20", "-0.10", "-0.10"), ("-0.50", "0.75", "0.75")],
)
def test_weights_out_of_range_are_rejected(severity: str, flow: str, proximity: str) -> None:
    with pytest.raises(InvalidWeightsError, match="entre 0 y 1"):
        _weights(severity, flow, proximity)


def test_weights_with_more_than_two_decimals_are_rejected() -> None:
    with pytest.raises(InvalidWeightsError, match="dos decimales"):
        _weights("0.505", "0.295", "0.20")


@pytest.mark.parametrize("value", ["NaN", "Infinity"])
def test_non_finite_weights_are_rejected(value: str) -> None:
    with pytest.raises(InvalidWeightsError, match="no es un número"):
        _weights(value, "0.30", "0.20")


def test_weights_are_immutable() -> None:
    with pytest.raises(AttributeError):
        DEFAULT_WEIGHTS.severity = Decimal("1")  # type: ignore[misc]
