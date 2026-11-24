"""Resultados de una ronda (objetivo 4, HU-09) con un lector en memoria."""

import uuid
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from app.modules.validation.application.round_results import RoundResultsService
from app.modules.validation.domain.agreement import (
    BetweenZones,
    NotComputable,
    ZoneRanking,
    between_zones,
    zone_agreement,
)
from app.modules.validation.domain.results import (
    DedupSummary,
    ReviewReport,
    ReviewWarning,
    RoundData,
    RoundStillOpenError,
    ZoneRoundData,
)
from app.modules.validation.domain.rounds import (
    RoundEntry,
    RoundNotFoundError,
    RoundStatus,
    RoundSummary,
    number_evaluators,
)
from app.modules.validation.domain.zones import Concentration

NOW = datetime(2026, 11, 23, 12, tzinfo=UTC)
ROUND_ID = uuid.UUID("00000000-0000-0000-0000-0000000000f1")
EVA_1 = uuid.UUID("00000000-0000-0000-0000-0000000000e1")
EVA_2 = uuid.UUID("00000000-0000-0000-0000-0000000000e2")
DEDUP = DedupSummary(
    reports=7,
    reports_confirmed=2,
    confirmations=3,
    warnings_total=4,
    warnings_confirmed=1,
    warnings_created_anyway=2,
    warnings_pending=1,
)


def _summary(status: RoundStatus = RoundStatus.CLOSED) -> RoundSummary:
    return RoundSummary(
        round_id=ROUND_ID,
        name="Piloto 1",
        status=status,
        sample_size=5,
        opened_at=NOW,
        closed_at=NOW if status is RoundStatus.CLOSED else None,
    )


def _zone(
    zone_id: int,
    concentration: Concentration,
    orders: Mapping[uuid.UUID, Sequence[int]],
    n: int = 5,
) -> ZoneRoundData:
    report_ids = [uuid.UUID(int=zone_id * 100 + i) for i in range(n)]
    entries = [
        RoundEntry(report_id=r, zone_id=zone_id, urgency_score=Decimal(9 - i), motor_order=i + 1)
        for i, r in enumerate(report_ids)
    ]
    return ZoneRoundData(
        zone_id=zone_id,
        name=f"Zona {zone_id}",
        concentration=concentration,
        entries=entries,
        evaluator_orders={
            evaluator: dict(zip(report_ids, positions, strict=True))
            for evaluator, positions in orders.items()
        },
        dedup=DEDUP,
    )


class FakeReader:
    def __init__(self, data: RoundData | None) -> None:
        self.data = data
        self.reports: list[ReviewReport] = []
        self.warnings: list[ReviewWarning] = []

    def summary(self, round_id: uuid.UUID) -> RoundSummary | None:
        return self.data.summary if self.data is not None else None

    def load(self, round_id: uuid.UUID) -> RoundData | None:
        return self.data

    def review_reports(self, round_id: uuid.UUID) -> list[ReviewReport]:
        return self.reports

    def review_warnings(self, round_id: uuid.UUID) -> list[ReviewWarning]:
        return self.warnings


def _service(
    *zones: ZoneRoundData, status: RoundStatus = RoundStatus.CLOSED
) -> RoundResultsService:
    data = RoundData(
        summary=_summary(status), zones=list(zones), evaluator_numbers={EVA_1: 1, EVA_2: 2}
    )
    return RoundResultsService(FakeReader(data))


HIGH = _zone(1, Concentration.HIGH, {EVA_1: [1, 2, 3, 4, 5], EVA_2: [2, 1, 3, 5, 4]})
LOW = _zone(2, Concentration.LOW, {EVA_1: [5, 4, 3, 2, 1], EVA_2: [4, 5, 1, 3, 2]})


def _ranking(zone: ZoneRoundData) -> ZoneRanking:
    return ZoneRanking(
        zone_id=zone.zone_id,
        concentration=zone.concentration,
        motor_order={e.report_id: e.motor_order for e in zone.entries},
        evaluator_orders=zone.evaluator_orders,
    )


def test_results_match_the_agreement_functions_on_the_same_data() -> None:
    results = _service(HIGH, LOW).results(ROUND_ID)

    high, low = zone_agreement(_ranking(HIGH)), zone_agreement(_ranking(LOW))
    assert high is not None
    assert low is not None
    assert [z.agreement for z in results.zones] == [high, low]
    assert results.between == between_zones([(Concentration.HIGH, high), (Concentration.LOW, low)])
    assert isinstance(results.between, BetweenZones)
    assert results.round.name == "Piloto 1"
    assert [z.dedup for z in results.zones] == [DEDUP, DEDUP]
    assert results.evaluator_numbers == {EVA_1: 1, EVA_2: 2}


def test_a_zone_without_orders_has_no_agreement_and_stays_out_of_the_test() -> None:
    silent = _zone(2, Concentration.LOW, {})

    results = _service(HIGH, silent).results(ROUND_ID)

    assert results.zones[1].agreement is None
    assert results.zones[0].agreement is not None
    # Solo queda la zona de alta: no hay con qué compararla.
    assert isinstance(results.between, NotComputable)


def test_an_open_round_has_no_results_yet() -> None:
    service = _service(HIGH, LOW, status=RoundStatus.OPEN)
    with pytest.raises(RoundStillOpenError):
        service.results(ROUND_ID)


def test_an_unknown_round_is_not_found() -> None:
    service = RoundResultsService(FakeReader(None))

    with pytest.raises(RoundNotFoundError):
        service.results(ROUND_ID)
    with pytest.raises(RoundNotFoundError):
        service.review_reports(ROUND_ID)
    with pytest.raises(RoundNotFoundError):
        service.review_warnings(ROUND_ID)


def test_the_review_files_are_allowed_while_the_round_is_open() -> None:
    reader = FakeReader(
        RoundData(summary=_summary(RoundStatus.OPEN), zones=[], evaluator_numbers={})
    )
    service = RoundResultsService(reader)

    summary, reports = service.review_reports(ROUND_ID)
    _, warnings = service.review_warnings(ROUND_ID)

    assert summary.status is RoundStatus.OPEN
    assert (reports, warnings) == ([], [])


def test_evaluators_are_numbered_by_their_first_submission() -> None:
    first = {EVA_2: NOW, EVA_1: NOW + timedelta(minutes=5)}

    assert number_evaluators(first) == {EVA_2: 1, EVA_1: 2}


def test_simultaneous_first_submissions_are_numbered_by_id() -> None:
    assert number_evaluators({EVA_2: NOW, EVA_1: NOW}) == {EVA_1: 1, EVA_2: 2}
