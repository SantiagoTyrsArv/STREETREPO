"""Muestreo y orden del motor de una ronda de evaluación (objetivo 4)."""

import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from app.modules.reports.domain.severity import Severity
from app.modules.validation.domain.rounds import (
    EvaluatorLabel,
    RoundCandidate,
    ZoneTooSmallError,
    sample_and_rank,
)

BASE = datetime(2026, 10, 1, tzinfo=UTC)


def _candidate(
    n: int,
    *,
    zone: int = 1,
    u: str = "5.00",
    severity: Severity = Severity.MEDIUM,
    confirmations: int = 0,
    created_at: datetime = BASE,
) -> RoundCandidate:
    return RoundCandidate(
        report_id=uuid.UUID(int=n),
        zone_id=zone,
        urgency_score=Decimal(u),
        severity=severity,
        confirmations=confirmations,
        created_at=created_at,
    )


def _zone(zone: int, count: int, first: int = 0) -> list[RoundCandidate]:
    return [_candidate(first + i, zone=zone, u=f"{1 + i / 10:.2f}") for i in range(count)]


def test_same_seed_gives_the_same_result() -> None:
    candidates = _zone(1, 30) + _zone(2, 30, first=100)

    first = sample_and_rank(candidates, 10, seed=42)
    second = sample_and_rank(list(reversed(candidates)), 10, seed=42)

    assert first == second


def test_different_seed_can_change_the_sample() -> None:
    candidates = _zone(1, 40)

    ids_a = {e.report_id for e in sample_and_rank(candidates, 10, seed=1)}
    ids_b = {e.report_id for e in sample_and_rank(candidates, 10, seed=2)}

    assert ids_a != ids_b


def test_sample_has_n_reports_per_zone_numbered_from_one() -> None:
    candidates = _zone(1, 30) + _zone(2, 12, first=100)

    entries = sample_and_rank(candidates, 10, seed=7)

    for zone in (1, 2):
        orders = [e.motor_order for e in entries if e.zone_id == zone]
        assert orders == list(range(1, 11))


def test_zone_with_fewer_than_n_but_at_least_five_enters_whole() -> None:
    entries = sample_and_rank(_zone(1, 6), 20, seed=1)

    assert len(entries) == 6


def test_zone_with_exactly_n_reports_enters_whole() -> None:
    entries = sample_and_rank(_zone(1, 10), 10, seed=1)

    assert {e.report_id for e in entries} == {c.report_id for c in _zone(1, 10)}


def test_zone_with_four_reports_is_too_small() -> None:
    zone = _zone(1, 4)
    with pytest.raises(ZoneTooSmallError) as error:
        sample_and_rank(zone, 10, seed=1)

    assert (error.value.zone_name, error.value.count) == ("1", 4)


def test_zone_without_candidates_is_too_small_when_names_are_given() -> None:
    names = {1: "Centro", 2: "Obonuco"}

    zone = _zone(1, 8)
    with pytest.raises(ZoneTooSmallError) as error:
        sample_and_rank(zone, 10, seed=1, zone_names=names)

    assert (error.value.zone_name, error.value.count) == ("Obonuco", 0)


def test_first_too_small_zone_is_reported_by_name() -> None:
    names = {1: "Zeta", 2: "Alfa"}

    with pytest.raises(ZoneTooSmallError, match="Alfa"):
        sample_and_rank([], 10, seed=1, zone_names=names)


def test_order_is_urgency_then_severity_then_confirmations_then_age() -> None:
    older = BASE - timedelta(days=1)
    candidates = [
        _candidate(1, u="6.10", severity=Severity.MEDIUM),
        _candidate(2, u="8.70"),
        _candidate(3, u="6.10", severity=Severity.HIGH),
        _candidate(4, u="6.10", severity=Severity.MEDIUM, confirmations=2),
        _candidate(5, u="6.10", severity=Severity.MEDIUM, confirmations=2, created_at=older),
    ]

    entries = sample_and_rank(candidates, 10, seed=1)

    assert [e.report_id.int for e in entries] == [2, 3, 5, 4, 1]
    assert next(e.urgency_score for e in entries) == Decimal("8.70")


def test_total_tie_is_broken_by_report_id_regardless_of_input_order() -> None:
    candidates = [_candidate(n) for n in (9, 3, 7, 1, 5)]

    forward = sample_and_rank(candidates, 10, seed=1)
    backward = sample_and_rank(list(reversed(candidates)), 10, seed=1)

    assert [e.report_id.int for e in forward] == [1, 3, 5, 7, 9]
    assert forward == backward


def test_evaluator_label_text() -> None:
    assert EvaluatorLabel(2).text == "Evaluador 2"


def test_total_tie_in_a_sampled_zone_is_ordered_by_report_id() -> None:
    candidates = [_candidate(n) for n in range(1, 21)]

    entries = sample_and_rank(candidates, 10, seed=3)

    ids = [e.report_id.int for e in entries]
    assert len(ids) == 10
    assert ids == sorted(ids)
