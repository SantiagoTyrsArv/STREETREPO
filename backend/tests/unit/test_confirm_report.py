"""Caso de uso ConfirmReport (HU-16, propuesta 48) con dobles en memoria."""

import uuid
from datetime import UTC, datetime, timedelta

import pytest

from app.modules.confirmations.application.confirm_report import ConfirmReport
from app.modules.confirmations.domain.errors import (
    AlreadyConfirmedError,
    OwnReportConfirmationError,
    ReportNotActiveError,
    ReportNotFoundError,
)
from app.modules.confirmations.domain.ports import ConfirmationTarget
from app.modules.reports.domain.status import ReportStatus
from app.shared.application.rate_limit import RateLimit, RateLimitExceededError
from app.shared.infrastructure.memory_rate_limiter import InMemoryRateLimiter

AUTHOR = uuid.UUID("00000000-0000-0000-0000-00000000000a")
CITIZEN = uuid.UUID("00000000-0000-0000-0000-00000000000c")
REPORT = uuid.UUID("00000000-0000-0000-0000-0000000000e1")
NOW = datetime(2026, 10, 19, 12, tzinfo=UTC)
GENEROUS = RateLimit(max_requests=100, window=timedelta(hours=1))


class FakeConfirmations:
    def __init__(self, targets: dict[uuid.UUID, ConfirmationTarget]) -> None:
        self.targets = targets
        self.rows: set[tuple[uuid.UUID, uuid.UUID]] = set()

    def find_target(self, report_id: uuid.UUID) -> ConfirmationTarget | None:
        return self.targets.get(report_id)

    def add(self, report_id: uuid.UUID, user_id: uuid.UUID) -> None:
        if (report_id, user_id) in self.rows:
            raise AlreadyConfirmedError(str(report_id))
        self.rows.add((report_id, user_id))

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


def _use_case(
    status: ReportStatus = ReportStatus.EVALUATED, limit: RateLimit = GENEROUS
) -> tuple[ConfirmReport, FakeConfirmations, FakeTransaction]:
    confirmations = FakeConfirmations({REPORT: ConfirmationTarget(owner_id=AUTHOR, status=status)})
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

    assert use_case.execute(REPORT, CITIZEN) == 1
    assert confirmations.rows == {(REPORT, CITIZEN)}
    assert transaction.commits == 1


def test_unknown_report_raises_not_found() -> None:
    use_case, confirmations, transaction = _use_case()

    with pytest.raises(ReportNotFoundError):
        use_case.execute(uuid.uuid4(), CITIZEN)
    assert confirmations.rows == set()
    assert transaction.commits == 0


def test_repaired_report_cannot_be_confirmed() -> None:
    use_case, confirmations, _ = _use_case(status=ReportStatus.REPAIRED)

    with pytest.raises(ReportNotActiveError):
        use_case.execute(REPORT, CITIZEN)
    assert confirmations.rows == set()


def test_author_cannot_confirm_own_report() -> None:
    use_case, confirmations, _ = _use_case()

    with pytest.raises(OwnReportConfirmationError):
        use_case.execute(REPORT, AUTHOR)
    assert confirmations.rows == set()


def test_second_confirmation_raises_already_confirmed_and_rolls_back() -> None:
    use_case, _, transaction = _use_case()
    use_case.execute(REPORT, CITIZEN)

    with pytest.raises(AlreadyConfirmedError):
        use_case.execute(REPORT, CITIZEN)
    assert transaction.commits == 1
    assert transaction.rollbacks == 1


def test_rate_limit_applies_per_user() -> None:
    use_case, confirmations, _ = _use_case(
        limit=RateLimit(max_requests=2, window=timedelta(hours=1))
    )
    others = [uuid.uuid4() for _ in range(3)]
    for report in others:
        confirmations.targets[report] = ConfirmationTarget(
            owner_id=AUTHOR, status=ReportStatus.EVALUATED
        )
    use_case.execute(others[0], CITIZEN)
    use_case.execute(others[1], CITIZEN)

    with pytest.raises(RateLimitExceededError):
        use_case.execute(others[2], CITIZEN)
    # Otro ciudadano tiene su propio cupo.
    assert use_case.execute(others[2], uuid.uuid4()) == 1
