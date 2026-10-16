from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

from app.modules.priority.domain.ranking import rank
from app.modules.reports.domain.severity import Severity


@dataclass(frozen=True)
class Entry:
    name: str
    urgency_score: Decimal
    severity: Severity
    confirmations: int
    created_at: datetime


def _at(day: int) -> datetime:
    return datetime(2026, 10, day, tzinfo=UTC)


def _names(entries: list[Entry]) -> list[str]:
    return [entry.name for entry in entries]


def test_higher_urgency_goes_first() -> None:
    entries = [
        Entry("baja", Decimal("3.60"), Severity.MEDIUM, 0, _at(1)),
        Entry("alta", Decimal("8.70"), Severity.HIGH, 0, _at(1)),
        Entry("media", Decimal("6.50"), Severity.MEDIUM, 0, _at(1)),
    ]

    assert _names(rank(entries)) == ["alta", "media", "baja"]


def test_tie_is_broken_by_higher_severity() -> None:
    entries = [
        Entry("media", Decimal("6.00"), Severity.MEDIUM, 9, _at(1)),
        Entry("alta", Decimal("6.00"), Severity.HIGH, 0, _at(5)),
    ]

    assert _names(rank(entries)) == ["alta", "media"]


def test_then_by_more_confirmations() -> None:
    entries = [
        Entry("pocas", Decimal("6.00"), Severity.HIGH, 1, _at(1)),
        Entry("muchas", Decimal("6.00"), Severity.HIGH, 4, _at(5)),
    ]

    assert _names(rank(entries)) == ["muchas", "pocas"]


def test_then_by_older_report() -> None:
    entries = [
        Entry("reciente", Decimal("6.00"), Severity.HIGH, 2, _at(9)),
        Entry("antiguo", Decimal("6.00"), Severity.HIGH, 2, _at(2)),
    ]

    assert _names(rank(entries)) == ["antiguo", "reciente"]


def test_confirmations_never_beat_a_higher_urgency() -> None:
    # Las confirmaciones no modifican U (guía 2.2): solo desempatan.
    entries = [
        Entry("confirmado", Decimal("6.09"), Severity.HIGH, 50, _at(1)),
        Entry("sin confirmar", Decimal("6.10"), Severity.LOW, 0, _at(9)),
    ]

    assert _names(rank(entries)) == ["sin confirmar", "confirmado"]


def test_rank_returns_a_new_list() -> None:
    entries = [Entry("único", Decimal("5.00"), Severity.LOW, 0, _at(1))]

    ranked = rank(entries)

    assert ranked == entries
    assert ranked is not entries
