"""Máquina de estados del reporte (guía 2.4).

``Registrado → Evaluado → Priorizado → Reparado``. Es la única definición de las
transiciones válidas; todo cambio produce un ``StatusChange`` para el historial.
"""

import uuid
from dataclasses import dataclass
from types import MappingProxyType

from app.modules.reports.domain.status import ReportStatus

NEXT_STATUS: MappingProxyType[ReportStatus, ReportStatus] = MappingProxyType(
    {
        ReportStatus.REGISTERED: ReportStatus.EVALUATED,
        ReportStatus.EVALUATED: ReportStatus.PRIORITIZED,
        ReportStatus.PRIORITIZED: ReportStatus.REPAIRED,
    }
)

# Registrado → Evaluado lo hace el motor de priorización, nunca una persona.
# El resto de transiciones las hace un administrador (el rol se verifica en la aplicación).
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


def next_status(current: ReportStatus) -> ReportStatus | None:
    """Siguiente estado permitido, o ``None`` si el reporte ya está reparado."""
    return NEXT_STATUS.get(current)


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
    if next_status(current) != new:
        raise InvalidStatusTransitionError(
            current, new, f"No se puede pasar de «{current}» a «{new}»"
        )
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
