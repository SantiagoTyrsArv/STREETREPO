import uuid
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class DeletionRequestStatus(StrEnum):
    """Estado del trámite de supresión. Valores del ENUM ``estado`` de ``solicitud_supresion``."""

    PENDING = "pendiente"
    ATTENDED = "atendida"


@dataclass(frozen=True, slots=True)
class DeletionRequest:
    """Constancia del trámite de supresión de datos (Ley 1581)."""

    id: uuid.UUID
    user_id: uuid.UUID
    status: DeletionRequestStatus
    requested_at: datetime
    attended_at: datetime | None
