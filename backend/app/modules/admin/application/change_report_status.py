"""Caso de uso: un administrador cambia el estado del reporte con observación (HU-12).

El estado actual se lee con un candado de fila: si otro administrador lo cambió entre que
se cargó la pantalla y se guardó, la máquina de estados valida contra el estado real y
responde que la transición ya no es válida, en vez de sobrescribirlo.
"""

import uuid

from app.modules.admin.domain.errors import ReportNotFoundError
from app.modules.reports.domain.ports import ReportStatusLock, StatusHistoryRecorder
from app.modules.reports.domain.status import ReportStatus
from app.modules.reports.domain.status_machine import StatusChange, change_status
from app.shared.application.transaction import TransactionManager


class ChangeReportStatus:
    def __init__(
        self,
        lock: ReportStatusLock,
        recorder: StatusHistoryRecorder,
        transaction: TransactionManager,
    ) -> None:
        self._lock = lock
        self._recorder = recorder
        self._transaction = transaction

    def execute(
        self, report_id: uuid.UUID, new: ReportStatus, admin_id: uuid.UUID, note: str | None
    ) -> StatusChange:
        """Lanza ``ReportNotFoundError`` o ``InvalidStatusTransitionError``; en todo error
        revierte la transacción.
        """
        try:
            current = self._lock.lock_status(report_id)
            if current is None:
                raise ReportNotFoundError(str(report_id))
            change = change_status(current, new, changed_by=admin_id, note=note)
            self._recorder.apply(report_id, change)
            self._transaction.commit()
        except Exception:
            self._transaction.rollback()
            raise
        return change
