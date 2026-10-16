"""Máquina de estados del reporte (guía 2.4, decisión 12).

``Registrado → Evaluado → Priorizado → Reparado``. Es la única definición de las
transiciones válidas; todo cambio produce un ``StatusChange`` para el historial.

Se permiten avances con salto (p. ej. Evaluado → Reparado, si una cuadrilla
repara el daño antes de formalizar la prioridad) y nunca retrocesos.
"""

import uuid
from dataclasses import dataclass

from app.modules.reports.domain.status import ReportStatus

LIFECYCLE: tuple[ReportStatus, ...] = (
    ReportStatus.REGISTERED,
    ReportStatus.EVALUATED,
    ReportStatus.PRIORITIZED,
    ReportStatus.REPAIRED,
)

# Registrado → Evaluado lo hace el motor de priorización, nunca una persona.
# Un reporte registrado no puede saltar estados: primero lo evalúa el motor. El resto
# de transiciones las hace un administrador (el rol se verifica en la aplicación).
SYSTEM_TRANSITIONS: frozenset[tuple[ReportStatus, ReportStatus]] = frozenset(
    {(ReportStatus.REGISTERED, ReportStatus.EVALUATED)}
)


class InvalidStatusTransitionError(ValueError):
    """Cambio de estado no permitido por la máquina de estados."""

    def __init__(self, current: ReportStatus, new: ReportStatus, reason: str) -> None:
        super().__init__(reason)
        self.current = current
        self.new = new


@dataclass(frozen=True, slots=True)
class StatusChange:
    """Registro del historial: quién, qué transición y con qué observación.

    ``changed_by`` es ``None`` cuando el cambio lo hizo el sistema; ``previous``
    es ``None`` solo en el registro inicial del reporte.
    """

    previous: ReportStatus | None
    new: ReportStatus
    changed_by: uuid.UUID | None
    note: str | None


def allowed_next_statuses(current: ReportStatus) -> tuple[ReportStatus, ...]:
    """Estados a los que puede avanzar el reporte; vacío si ya está reparado."""
    if current is ReportStatus.REGISTERED:
        return (ReportStatus.EVALUATED,)
    return LIFECYCLE[LIFECYCLE.index(current) + 1 :]


def _clean_note(note: str | None) -> str | None:
    if note is None:
        return None
    return note.strip() or None


def initial_status_change(created_by: uuid.UUID) -> StatusChange:
    """Primer registro del historial al crear el reporte."""
    return StatusChange(
        previous=None, new=ReportStatus.REGISTERED, changed_by=created_by, note=None
    )


def change_status(
    current: ReportStatus,
    new: ReportStatus,
    *,
    changed_by: uuid.UUID | None,
    note: str | None = None,
) -> StatusChange:
    """Valida la transición y devuelve el registro para el historial.

    ``changed_by=None`` indica una transición automática del sistema.
    """
    if new not in allowed_next_statuses(current):
        reason = (
            "Un reporte registrado primero lo evalúa el motor de priorización"
            if current is ReportStatus.REGISTERED and LIFECYCLE.index(new) > 0
            else f"No se puede pasar de «{current}» a «{new}»"
        )
        raise InvalidStatusTransitionError(current, new, reason)
    by_system = changed_by is None
    if (current, new) in SYSTEM_TRANSITIONS and not by_system:
        raise InvalidStatusTransitionError(
            current, new, "El paso a «evaluado» lo hace el motor de priorización"
        )
    if (current, new) not in SYSTEM_TRANSITIONS and by_system:
        raise InvalidStatusTransitionError(
            current, new, f"El paso a «{new}» debe hacerlo un administrador"
        )
    return StatusChange(previous=current, new=new, changed_by=changed_by, note=_clean_note(note))
