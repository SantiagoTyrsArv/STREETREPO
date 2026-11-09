"""Caso de uso ChangeReportStatus: el administrador cambia el estado con historial (HU-12)."""

import uuid

import pytest

from app.modules.admin.application.change_report_status import ChangeReportStatus
from app.modules.admin.domain.errors import ReportNotFoundError
from app.modules.reports.domain.status import ReportStatus
from app.modules.reports.domain.status_machine import (
    InvalidStatusTransitionError,
    StatusChange,
)

REPORT_ID = uuid.UUID("00000000-0000-0000-0000-0000000000aa")
ADMIN_ID = uuid.UUID("00000000-0000-0000-0000-0000000000ad")


class FakeLock:
    def __init__(self, status: ReportStatus | None) -> None:
        self.status = status
        self.locked: list[uuid.UUID] = []

    def lock_status(self, report_id: uuid.UUID) -> ReportStatus | None:
        self.locked.append(report_id)
        return self.status


class FakeRecorder:
    def __init__(self) -> None:
        self.applied: list[tuple[uuid.UUID, StatusChange]] = []

    def apply(self, report_id: uuid.UUID, change: StatusChange) -> None:
        self.applied.append((report_id, change))


class FakeTransaction:
    def __init__(self) -> None:
        self.commits = 0
        self.rollbacks = 0

    def commit(self) -> None:
        self.commits += 1

    def rollback(self) -> None:
        self.rollbacks += 1


def _run(
    current: ReportStatus | None, new: ReportStatus, note: str | None = None
) -> tuple[StatusChange, FakeRecorder, FakeTransaction]:
    recorder, transaction = FakeRecorder(), FakeTransaction()
    use_case = ChangeReportStatus(FakeLock(current), recorder, transaction)
    try:
        change = use_case.execute(REPORT_ID, new, ADMIN_ID, note)
    except Exception:
        assert transaction.commits == 0
        assert transaction.rollbacks == 1
        assert recorder.applied == []
        raise
    return change, recorder, transaction


def test_change_records_history_and_commits() -> None:
    change, recorder, transaction = _run(
        ReportStatus.EVALUATED, ReportStatus.PRIORITIZED, "  Cuadrilla asignada  "
    )

    expected = StatusChange(
        previous=ReportStatus.EVALUATED,
        new=ReportStatus.PRIORITIZED,
        changed_by=ADMIN_ID,
        note="Cuadrilla asignada",
    )
    assert change == expected
    assert recorder.applied == [(REPORT_ID, expected)]
    assert (transaction.commits, transaction.rollbacks) == (1, 0)


def test_skip_to_repaired_is_allowed() -> None:
    change, _, _ = _run(ReportStatus.EVALUATED, ReportStatus.REPAIRED)

    assert change.new is ReportStatus.REPAIRED


def test_invalid_transition_rolls_back() -> None:
    with pytest.raises(InvalidStatusTransitionError) as error:
        _run(ReportStatus.REPAIRED, ReportStatus.PRIORITIZED)

    assert error.value.current is ReportStatus.REPAIRED


def test_admin_cannot_do_system_transition() -> None:
    with pytest.raises(InvalidStatusTransitionError, match="motor"):
        _run(ReportStatus.REGISTERED, ReportStatus.EVALUATED)


def test_blank_note_saved_as_none() -> None:
    change, _, _ = _run(ReportStatus.PRIORITIZED, ReportStatus.REPAIRED, "   ")

    assert change.note is None


def test_unknown_report_raises_not_found() -> None:
    with pytest.raises(ReportNotFoundError):
        _run(None, ReportStatus.PRIORITIZED)


def test_storage_failure_rolls_back() -> None:
    class BrokenRecorder(FakeRecorder):
        def apply(self, report_id: uuid.UUID, change: StatusChange) -> None:
            raise RuntimeError("base caída")

    transaction = FakeTransaction()
    use_case = ChangeReportStatus(FakeLock(ReportStatus.EVALUATED), BrokenRecorder(), transaction)

    with pytest.raises(RuntimeError):
        use_case.execute(REPORT_ID, ReportStatus.PRIORITIZED, ADMIN_ID, None)

    assert (transaction.commits, transaction.rollbacks) == (0, 1)
