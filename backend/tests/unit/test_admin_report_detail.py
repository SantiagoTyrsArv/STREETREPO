"""Detalle del reporte para el administrador: transiciones ofrecidas y reporte inexistente."""

import uuid
from datetime import UTC, datetime

import pytest

from app.modules.admin.application.get_admin_report import GetAdminReport
from app.modules.admin.domain.errors import ReportNotFoundError
from app.modules.admin.domain.report_detail import AdminReportDetail, admin_next_statuses
from app.modules.reports.domain.severity import Severity
from app.modules.reports.domain.status import ReportStatus
from app.shared.domain.geo import GeoPoint

REPORT_ID = uuid.UUID("00000000-0000-0000-0000-0000000000aa")


def _detail(status: ReportStatus) -> AdminReportDetail:
    return AdminReportDetail(
        id=REPORT_ID,
        status=status,
        severity=Severity.HIGH,
        description=None,
        location=GeoPoint(longitude=-77.28, latitude=1.21),
        road=None,
        reporter_name="Ana",
        created_at=datetime(2026, 10, 1, tzinfo=UTC),
        confirmations=0,
        evaluation=None,
        history=(),
    )


class FakeReader:
    def __init__(self, detail: AdminReportDetail | None) -> None:
        self._detail = detail

    def get(self, report_id: uuid.UUID) -> AdminReportDetail | None:
        return self._detail if self._detail and self._detail.id == report_id else None


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        (ReportStatus.REGISTERED, ()),
        (ReportStatus.EVALUATED, (ReportStatus.PRIORITIZED, ReportStatus.REPAIRED)),
        (ReportStatus.PRIORITIZED, (ReportStatus.REPAIRED,)),
        (ReportStatus.REPAIRED, ()),
    ],
)
def test_allowed_next_statuses_exclude_system_transition(
    status: ReportStatus, expected: tuple[ReportStatus, ...]
) -> None:
    assert admin_next_statuses(status) == expected
    assert _detail(status).allowed_next_statuses == expected


def test_detail_without_road_shows_no_road_address() -> None:
    detail = _detail(ReportStatus.EVALUATED)

    assert detail.address == "Sin vía asociada"
    assert detail.needs_road_review is True


def test_returns_the_detail() -> None:
    detail = _detail(ReportStatus.EVALUATED)

    assert GetAdminReport(FakeReader(detail)).execute(REPORT_ID) is detail


def test_missing_report_raises_not_found() -> None:
    with pytest.raises(ReportNotFoundError):
        GetAdminReport(FakeReader(None)).execute(REPORT_ID)
