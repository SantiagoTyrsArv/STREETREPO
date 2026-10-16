import uuid
from typing import Protocol

from app.modules.reports.domain.status_machine import StatusChange


class StatusHistoryRecorder(Protocol):
    def apply(self, report_id: uuid.UUID, change: StatusChange) -> None:
        """Cambia el estado del reporte y deja el registro en el historial."""
        ...
