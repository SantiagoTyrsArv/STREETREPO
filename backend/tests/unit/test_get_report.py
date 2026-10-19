"""Caso de uso GetReport: quién ve el detalle de un reporte y con qué datos (decisión 49)."""

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from app.modules.reports.application.get_photo import PhotoViewer
from app.modules.reports.application.get_report import GetReport
from app.modules.reports.domain.entities import ReportDetails
from app.modules.reports.domain.my_reports import PublicReportView
from app.modules.reports.domain.report_view import (
    FullReportView,
    LimitedReportView,
    ReportNotVisibleError,
    StatusHistoryEntry,
)
from app.modules.reports.domain.severity import Severity
from app.modules.reports.domain.status import ReportStatus
from app.shared.domain.geo import GeoPoint

AUTHOR = uuid.UUID("00000000-0000-0000-0000-00000000000a")
CONFIRMER = uuid.UUID("00000000-0000-0000-0000-00000000000c")
STRANGER = uuid.UUID("00000000-0000-0000-0000-00000000000d")
REPORT = uuid.UUID("00000000-0000-0000-0000-0000000000e1")
CREATED = datetime(2026, 10, 10, 10, tzinfo=UTC)
CONFIRMED = datetime(2026, 10, 12, 10, tzinfo=UTC)
HISTORY = (
    StatusHistoryEntry(status=ReportStatus.REGISTERED, changed_at=CREATED, note=None),
    StatusHistoryEntry(status=ReportStatus.EVALUATED, changed_at=CREATED, note=None),
    StatusHistoryEntry(
        status=ReportStatus.PRIORITIZED, changed_at=CONFIRMED, note="Cuadrilla de Ana asignada"
    ),
)
DETAILS = ReportDetails(
    id=REPORT,
    user_id=AUTHOR,
    location=GeoPoint(longitude=-77.281137, latitude=1.213662),
    severity=Severity.HIGH,
    description="Hueco profundo",
    status=ReportStatus.PRIORITIZED,
    priority_score=Decimal("8.70"),
    road_id=1,
    road_name="Avenida Los Estudiantes",
    created_at=CREATED,
)
PUBLIC = PublicReportView(
    id=REPORT,
    location=GeoPoint(longitude=-77.2811, latitude=1.2137),
    status=ReportStatus.PRIORITIZED,
    severity=Severity.HIGH,
    confirmations=1,
    road_id=1,
    road_name="Avenida Los Estudiantes",
    created_at=CREATED,
)


class FakeReader:
    def __init__(self, *, confirmed_by: set[uuid.UUID] | None = None, exists: bool = True) -> None:
        self._confirmed_by = confirmed_by or set()
        self._exists = exists

    def get_details(self, report_id: uuid.UUID) -> ReportDetails | None:
        return DETAILS if self._exists and report_id == REPORT else None

    def public_view(self, report_id: uuid.UUID) -> PublicReportView | None:
        return PUBLIC if self._exists and report_id == REPORT else None

    def confirmed_at(self, report_id: uuid.UUID, user_id: uuid.UUID) -> datetime | None:
        return CONFIRMED if user_id in self._confirmed_by else None

    def confirmations(self, report_id: uuid.UUID) -> int:
        return len(self._confirmed_by)

    def history(self, report_id: uuid.UUID) -> Sequence[StatusHistoryEntry]:
        return HISTORY


def _citizen(user_id: uuid.UUID) -> PhotoViewer:
    return PhotoViewer(user_id=user_id, is_admin=False)


def test_author_gets_the_full_view() -> None:
    view = GetReport(FakeReader(confirmed_by={CONFIRMER})).execute(REPORT, _citizen(AUTHOR))

    assert view == FullReportView(details=DETAILS, confirmations=1, history=HISTORY)


def test_admin_gets_the_full_view_even_if_they_confirmed() -> None:
    admin = PhotoViewer(user_id=CONFIRMER, is_admin=True)

    view = GetReport(FakeReader(confirmed_by={CONFIRMER})).execute(REPORT, admin)

    assert isinstance(view, FullReportView)


def test_confirmer_gets_the_limited_view_without_notes() -> None:
    view = GetReport(FakeReader(confirmed_by={CONFIRMER})).execute(REPORT, _citizen(CONFIRMER))

    assert isinstance(view, LimitedReportView)
    assert view.public == PUBLIC
    assert view.confirmed_at == CONFIRMED
    assert [entry.status for entry in view.history] == [entry.status for entry in HISTORY]
    assert all(entry.note is None for entry in view.history)


def test_stranger_gets_not_visible() -> None:
    with pytest.raises(ReportNotVisibleError):
        GetReport(FakeReader(confirmed_by={CONFIRMER})).execute(REPORT, _citizen(STRANGER))


def test_missing_report_gets_not_visible() -> None:
    with pytest.raises(ReportNotVisibleError):
        GetReport(FakeReader(exists=False)).execute(REPORT, _citizen(AUTHOR))
