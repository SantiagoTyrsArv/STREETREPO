"""Detalle de un reporte según quién lo pide (decisión 49).

El autor y los administradores ven el reporte completo; quien lo confirmó, la vista
pública y el historial sin observaciones (pueden mencionar datos del autor); nadie más.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

from app.modules.reports.domain.entities import ReportDetails
from app.modules.reports.domain.my_reports import PublicReportView
from app.modules.reports.domain.status import ReportStatus


@dataclass(frozen=True, slots=True)
class StatusHistoryEntry:
    status: ReportStatus
    changed_at: datetime
    note: str | None


@dataclass(frozen=True, slots=True)
class FullReportView:
    details: ReportDetails
    confirmations: int
    history: Sequence[StatusHistoryEntry]


@dataclass(frozen=True, slots=True)
class LimitedReportView:
    public: PublicReportView
    confirmed_at: datetime
    history: Sequence[StatusHistoryEntry]


class ReportNotVisibleError(Exception):
    """El reporte no existe o el usuario no puede verlo.

    Los dos casos son el mismo error a propósito: la respuesta no revela si existe un
    reporte ajeno (IDOR, guía 7.1).
    """
