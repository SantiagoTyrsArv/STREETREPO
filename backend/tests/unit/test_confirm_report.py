"""Caso de uso ConfirmReport (HU-16, propuesta 48) con dobles en memoria."""

import uuid
from datetime import UTC, datetime, timedelta

import pytest

from app.modules.confirmations.application.confirm_report import ConfirmReport
from app.modules.confirmations.domain.errors import (
    AlreadyConfirmedError,
    ConfirmationTooFarError,
    OwnReportConfirmationError,
    ReportNotActiveError,
    ReportNotFoundError,
)
from app.modules.confirmations.domain.ports import ConfirmationTarget
from app.modules.reports.domain.status import ReportStatus
from app.shared.application.rate_limit import RateLimit, RateLimitExceededError
from app.shared.domain.geo import GeoPoint
from app.shared.domain.geo_parameters import CONFIRMATION_RADIUS_M
from app.shared.infrastructure.memory_rate_limiter import InMemoryRateLimiter

AUTHOR = uuid.UUID("00000000-0000-0000-0000-00000000000a")
CITIZEN = uuid.UUID("00000000-0000-0000-0000-00000000000c")
REPORT = uuid.UUID("00000000-0000-0000-0000-0000000000e1")
NOW = datetime(2026, 10, 19, 12, tzinfo=UTC)
GENEROUS = RateLimit(max_requests=100, window=timedelta(hours=1))
HERE = GeoPoint(longitude=-77.2806, latitude=1.2125)


class FakeConfirmations:
    def __init__(self, targets: dict[uuid.UUID, ConfirmationTarget]) -> None:
        self.targets = targets
        self.rows: set[tuple[uuid.UUID, uuid.UUID]] = set()
        self.distances: dict[tuple[uuid.UUID, uuid.UUID], float] = {}
        self.asked_from: list[GeoPoint] = []

    def find_target(self, report_id: uuid.UUID, location: GeoPoint) -> ConfirmationTarget | None:
        self.asked_from.append(location)
        return self.targets.get(report_id)

    def add(self, report_id: uuid.UUID, user_id: uuid.UUID, distance_m: float) -> None:
        if (report_id, user_id) in self.rows:
            raise AlreadyConfirmedError(str(report_id))
        self.rows.add((report_id, user_id))
        self.distances[(report_id, user_id)] = distance_m

    def count(self, report_id: uuid.UUID) -> int:
        return sum(1 for row in self.rows if row[0] == report_id)


class FakeTransaction:
    def __init__(self) -> None:
        self.commits = 0
        self.rollbacks = 0

    def commit(self) -> None:
        self.commits += 1

    def rollback(self) -> None:
        self.rollbacks += 1


class FixedClock:
    def now(self) -> datetime:
        return NOW


def _target(
    status: ReportStatus = ReportStatus.EVALUATED, distance_m: float = 12.5
) -> ConfirmationTarget:
    return ConfirmationTarget(owner_id=AUTHOR, status=status, distance_m=distance_m)


def _use_case(
    status: ReportStatus = ReportStatus.EVALUATED,
    limit: RateLimit = GENEROUS,
    distance_m: float = 12.5,
) -> tuple[ConfirmReport, FakeConfirmations, FakeTransaction]:
    confirmations = FakeConfirmations({REPORT: _target(status, distance_m)})
    transaction = FakeTransaction()
    use_case = ConfirmReport(
        confirmations=confirmations,
        rate_limiter=InMemoryRateLimiter(),
        limit_per_user=limit,
        clock=FixedClock(),
        transaction=transaction,
    )
    return use_case, confirmations, transaction


def test_confirming_returns_the_new_total() -> None:
    use_case, confirmations, transaction = _use_case()

    assert use_case.execute(REPORT, CITIZEN, HERE) == 1
    assert confirmations.rows == {(REPORT, CITIZEN)}
    assert transaction.commits == 1


def test_unknown_report_raises_not_found() -> None:
    use_case, confirmations, transaction = _use_case()

    with pytest.raises(ReportNotFoundError):
        use_case.execute(uuid.uuid4(), CITIZEN, HERE)
    assert confirmations.rows == set()
    assert transaction.commits == 0


def test_repaired_report_cannot_be_confirmed() -> None:
    use_case, confirmations, _ = _use_case(status=ReportStatus.REPAIRED)

    with pytest.raises(ReportNotActiveError):
        use_case.execute(REPORT, CITIZEN, HERE)
    assert confirmations.rows == set()


def test_author_cannot_confirm_own_report() -> None:
    use_case, confirmations, _ = _use_case()

    with pytest.raises(OwnReportConfirmationError):
        use_case.execute(REPORT, AUTHOR, HERE)
    assert confirmations.rows == set()


def test_second_confirmation_raises_already_confirmed_and_rolls_back() -> None:
    use_case, _, transaction = _use_case()
    use_case.execute(REPORT, CITIZEN, HERE)

    with pytest.raises(AlreadyConfirmedError):
        use_case.execute(REPORT, CITIZEN, HERE)
    assert transaction.commits == 1
    assert transaction.rollbacks == 1


def test_rate_limit_applies_per_user() -> None:
    use_case, confirmations, _ = _use_case(
        limit=RateLimit(max_requests=2, window=timedelta(hours=1))
    )
    others = [uuid.uuid4() for _ in range(3)]
    for report in others:
        confirmations.targets[report] = _target()
    use_case.execute(others[0], CITIZEN, HERE)
    use_case.execute(others[1], CITIZEN, HERE)

    with pytest.raises(RateLimitExceededError):
        use_case.execute(others[2], CITIZEN, HERE)
    # Otro ciudadano tiene su propio cupo.
    assert use_case.execute(others[2], uuid.uuid4(), HERE) == 1


def test_confirmation_stores_the_distance_and_asks_from_the_citizens_point() -> None:
    use_case, confirmations, _ = _use_case(distance_m=12.5)

    use_case.execute(REPORT, CITIZEN, HERE)

    assert confirmations.asked_from == [HERE]
    assert confirmations.distances == {(REPORT, CITIZEN): 12.5}


def test_confirmation_exactly_at_the_radius_is_accepted() -> None:
    use_case, confirmations, _ = _use_case(distance_m=CONFIRMATION_RADIUS_M)

    assert use_case.execute(REPORT, CITIZEN, HERE) == 1
    assert confirmations.rows == {(REPORT, CITIZEN)}


def test_confirmation_beyond_the_radius_is_rejected_without_saving() -> None:
    use_case, confirmations, transaction = _use_case(distance_m=CONFIRMATION_RADIUS_M + 0.01)

    with pytest.raises(ConfirmationTooFarError):
        use_case.execute(REPORT, CITIZEN, HERE)
    assert confirmations.rows == set()
    assert transaction.commits == 0


def test_own_report_is_reported_before_the_distance() -> None:
    # El autor lejos de su reporte recibe el motivo de fondo, no «acércate».
    use_case, _, _ = _use_case(distance_m=5000.0)

    with pytest.raises(OwnReportConfirmationError):
        use_case.execute(REPORT, AUTHOR, HERE)
