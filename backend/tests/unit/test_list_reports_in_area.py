"""Caso de uso del mapa de reportes: tope por respuesta y cupo por usuario."""

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta

import pytest

from app.modules.reports.application.list_reports_in_area import ListReportsInArea
from app.modules.reports.domain.my_reports import PublicReportView
from app.modules.reports.domain.public_map import MAX_MAP_REPORTS, MapReport
from app.modules.reports.domain.severity import Severity
from app.modules.reports.domain.status import ReportStatus
from app.shared.application.rate_limit import RateLimit, RateLimiter, RateLimitExceededError
from app.shared.domain.geo import BoundingBox, GeoPoint

NOW = datetime(2026, 11, 14, 15, 0, tzinfo=UTC)
VIEWER = uuid.uuid4()
AREA = BoundingBox(south=1.20, west=-77.29, north=1.22, east=-77.27)
LIMIT = RateLimit(max_requests=2, window=timedelta(minutes=1))


def _map_report() -> MapReport:
    return MapReport(
        public=PublicReportView(
            id=uuid.uuid4(),
            location=GeoPoint(longitude=-77.28, latitude=1.21),
            status=ReportStatus.EVALUATED,
            severity=Severity.MEDIUM,
            confirmations=0,
            road_id=None,
            road_name=None,
            created_at=NOW,
        ),
        is_mine=False,
        confirmed_by_me=False,
    )


class FakeReader:
    def __init__(self, total: int) -> None:
        self.reports = [_map_report() for _ in range(total)]
        self.calls: list[tuple[BoundingBox, ReportStatus | None, int, uuid.UUID]] = []

    def list_in_area(
        self, area: BoundingBox, status: ReportStatus | None, limit: int, viewer_id: uuid.UUID
    ) -> Sequence[MapReport]:
        self.calls.append((area, status, limit, viewer_id))
        return self.reports[:limit]


class FakeClock:
    def now(self) -> datetime:
        return NOW


class CountingLimiter:
    def __init__(self) -> None:
        self.hits: dict[str, int] = {}

    def hit(self, key: str, limit: RateLimit, now: datetime) -> None:
        if self.hits.get(key, 0) >= limit.max_requests:
            raise RateLimitExceededError(timedelta(seconds=30))
        self.hits[key] = self.hits.get(key, 0) + 1


def _use_case(reader: FakeReader, limiter: RateLimiter | None = None) -> ListReportsInArea:
    return ListReportsInArea(reader, limiter or CountingLimiter(), LIMIT, FakeClock())


def test_returns_the_reports_of_the_area_for_the_viewer() -> None:
    reader = FakeReader(total=3)

    page = _use_case(reader).execute(VIEWER, AREA, ReportStatus.EVALUATED, 10)

    assert list(page.items) == reader.reports
    assert (page.limit, page.truncated) == (10, False)
    # Pide uno de más para saber si quedaron reportes fuera.
    assert reader.calls == [(AREA, ReportStatus.EVALUATED, 11, VIEWER)]


def test_marks_the_page_as_truncated_when_the_area_has_more_reports() -> None:
    reader = FakeReader(total=5)

    page = _use_case(reader).execute(VIEWER, AREA, None, 4)

    assert len(page.items) == 4
    assert page.truncated is True


def test_exactly_the_limit_is_not_truncated() -> None:
    page = _use_case(FakeReader(total=4)).execute(VIEWER, AREA, None, 4)

    assert (len(page.items), page.truncated) == (4, False)


@pytest.mark.parametrize("limit", [0, -1, MAX_MAP_REPORTS + 1])
def test_rejects_a_limit_out_of_range(limit: int) -> None:
    reader = FakeReader(total=1)

    with pytest.raises(ValueError, match="limit"):
        _use_case(reader).execute(VIEWER, AREA, None, limit)

    assert reader.calls == []


def test_each_user_has_their_own_quota() -> None:
    reader = FakeReader(total=1)
    limiter = CountingLimiter()
    use_case = _use_case(reader, limiter)
    use_case.execute(VIEWER, AREA, None, 10)
    use_case.execute(VIEWER, AREA, None, 10)

    with pytest.raises(RateLimitExceededError):
        use_case.execute(VIEWER, AREA, None, 10)

    # La consulta rechazada no llega a la base y otro usuario conserva su cupo.
    assert len(reader.calls) == 2
    use_case.execute(uuid.uuid4(), AREA, None, 10)
    assert len(reader.calls) == 3
