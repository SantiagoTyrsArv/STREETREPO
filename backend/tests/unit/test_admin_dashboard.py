"""Caso de uso ReadDashboard: ranking, resumen por estado y mapa de calor (HU-08)."""

from collections.abc import Sequence

import pytest

from app.modules.admin.application.read_dashboard import HEATMAP_MAX_POINTS, ReadDashboard
from app.modules.admin.domain.ranking_view import (
    ACTIVE_STATUSES,
    MAX_PAGE_SIZE,
    HeatPoint,
    RankingPage,
    StatusSummary,
)
from app.modules.reports.domain.status import ReportStatus
from app.shared.domain.geo import BoundingBox

PASTO = BoundingBox(south=1.15, west=-77.35, north=1.25, east=-77.22)


class FakeReader:
    def __init__(self) -> None:
        self.ranking_calls: list[tuple[frozenset[ReportStatus], int, int]] = []
        self.heat_calls: list[tuple[BoundingBox | None, int]] = []

    def ranking(self, statuses: frozenset[ReportStatus], limit: int, offset: int) -> RankingPage:
        self.ranking_calls.append((statuses, limit, offset))
        return RankingPage(items=(), total=0)

    def summary(self) -> StatusSummary:
        return StatusSummary(active=3, evaluated=2, prioritized=1, repaired=1)

    def heat_points(self, bbox: BoundingBox | None, limit: int) -> Sequence[HeatPoint]:
        self.heat_calls.append((bbox, limit))
        return ()


def test_ranking_defaults_to_active_statuses() -> None:
    reader = FakeReader()

    ReadDashboard(reader).ranking(None, limit=20, offset=0)

    assert reader.ranking_calls == [
        (
            frozenset({ReportStatus.REGISTERED, ReportStatus.EVALUATED, ReportStatus.PRIORITIZED}),
            20,
            0,
        )
    ]
    assert ReportStatus.REPAIRED not in ACTIVE_STATUSES


def test_ranking_passes_explicit_statuses() -> None:
    reader = FakeReader()
    wanted = frozenset({ReportStatus.REPAIRED})

    ReadDashboard(reader).ranking(wanted, limit=10, offset=30)

    assert reader.ranking_calls == [(wanted, 10, 30)]


def test_ranking_with_empty_status_filter_uses_active() -> None:
    reader = FakeReader()

    ReadDashboard(reader).ranking(frozenset(), limit=20, offset=0)

    assert reader.ranking_calls[0][0] == ACTIVE_STATUSES


def test_ranking_rejects_limit_over_100() -> None:
    assert MAX_PAGE_SIZE == 100
    with pytest.raises(ValueError, match="limit"):
        ReadDashboard(FakeReader()).ranking(None, limit=MAX_PAGE_SIZE + 1, offset=0)


def test_ranking_rejects_non_positive_limit_and_negative_offset() -> None:
    with pytest.raises(ValueError, match="limit"):
        ReadDashboard(FakeReader()).ranking(None, limit=0, offset=0)
    with pytest.raises(ValueError, match="offset"):
        ReadDashboard(FakeReader()).ranking(None, limit=20, offset=-1)


def test_summary_comes_from_the_reader() -> None:
    assert ReadDashboard(FakeReader()).summary() == StatusSummary(
        active=3, evaluated=2, prioritized=1, repaired=1
    )


def test_heat_points_capped_at_5000() -> None:
    reader = FakeReader()

    ReadDashboard(reader).heat_points(PASTO)

    assert HEATMAP_MAX_POINTS == 5000
    assert reader.heat_calls == [(PASTO, 5000)]


def test_heat_points_limit_cannot_exceed_the_cap() -> None:
    reader = FakeReader()

    ReadDashboard(reader).heat_points(None, limit=HEATMAP_MAX_POINTS * 2)

    assert reader.heat_calls == [(None, HEATMAP_MAX_POINTS)]
