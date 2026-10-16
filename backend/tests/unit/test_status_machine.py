import uuid

import pytest

from app.modules.reports.domain.status import ReportStatus
from app.modules.reports.domain.status_machine import (
    InvalidStatusTransitionError,
    StatusChange,
    allowed_next_statuses,
    change_status,
    initial_status_change,
)

ADMIN_ID = uuid.UUID("00000000-0000-0000-0000-00000000000a")
CITIZEN_ID = uuid.UUID("00000000-0000-0000-0000-00000000000c")

REGISTERED = ReportStatus.REGISTERED
EVALUATED = ReportStatus.EVALUATED
PRIORITIZED = ReportStatus.PRIORITIZED
REPAIRED = ReportStatus.REPAIRED


@pytest.mark.parametrize(
    ("current", "expected"),
    [
        (REGISTERED, (EVALUATED,)),
        (EVALUATED, (PRIORITIZED, REPAIRED)),
        (PRIORITIZED, (REPAIRED,)),
        (REPAIRED, ()),
    ],
)
def test_allowed_next_statuses_only_move_forward(
    current: ReportStatus, expected: tuple[ReportStatus, ...]
) -> None:
    assert allowed_next_statuses(current) == expected


def test_initial_record_has_no_previous_status() -> None:
    assert initial_status_change(CITIZEN_ID) == StatusChange(
        previous=None, new=REGISTERED, changed_by=CITIZEN_ID, note=None
    )


def test_system_evaluates_a_registered_report() -> None:
    change = change_status(REGISTERED, EVALUATED, changed_by=None)

    assert change == StatusChange(previous=REGISTERED, new=EVALUATED, changed_by=None, note=None)


@pytest.mark.parametrize(
    ("current", "new"),
    [
        (EVALUATED, PRIORITIZED),
        (PRIORITIZED, REPAIRED),
        (EVALUATED, REPAIRED),  # salto: reparado antes de formalizar la prioridad
    ],
)
def test_admin_moves_the_report_forward(current: ReportStatus, new: ReportStatus) -> None:
    change = change_status(current, new, changed_by=ADMIN_ID, note="Cuadrilla asignada")

    assert change == StatusChange(
        previous=current, new=new, changed_by=ADMIN_ID, note="Cuadrilla asignada"
    )


@pytest.mark.parametrize(
    ("current", "new"),
    [
        (EVALUATED, REGISTERED),  # retrocede
        (PRIORITIZED, EVALUATED),
        (PRIORITIZED, REGISTERED),
        (REPAIRED, PRIORITIZED),
        (REPAIRED, EVALUATED),
        (REPAIRED, REPAIRED),  # sin cambio
        (EVALUATED, EVALUATED),
        (REGISTERED, REGISTERED),
    ],
)
def test_invalid_transitions_are_rejected(current: ReportStatus, new: ReportStatus) -> None:
    with pytest.raises(InvalidStatusTransitionError, match="No se puede pasar") as error:
        change_status(current, new, changed_by=ADMIN_ID)

    assert error.value.current is current
    assert error.value.new is new


@pytest.mark.parametrize("new", [PRIORITIZED, REPAIRED])
def test_a_registered_report_cannot_skip_the_evaluation(new: ReportStatus) -> None:
    with pytest.raises(InvalidStatusTransitionError, match="primero lo evalúa el motor"):
        change_status(REGISTERED, new, changed_by=ADMIN_ID)


def test_a_person_cannot_mark_a_report_as_evaluated() -> None:
    with pytest.raises(InvalidStatusTransitionError, match="motor de priorización"):
        change_status(REGISTERED, EVALUATED, changed_by=ADMIN_ID)


@pytest.mark.parametrize(
    ("current", "new"), [(EVALUATED, PRIORITIZED), (PRIORITIZED, REPAIRED), (EVALUATED, REPAIRED)]
)
def test_the_system_cannot_make_administrative_transitions(
    current: ReportStatus, new: ReportStatus
) -> None:
    with pytest.raises(InvalidStatusTransitionError, match="administrador"):
        change_status(current, new, changed_by=None)


@pytest.mark.parametrize(
    ("note", "expected"),
    [("  Bacheo programado  ", "Bacheo programado"), ("   ", None), (None, None)],
)
def test_note_is_trimmed_and_blank_notes_are_dropped(
    note: str | None, expected: str | None
) -> None:
    change = change_status(EVALUATED, PRIORITIZED, changed_by=ADMIN_ID, note=note)

    assert change.note == expected
