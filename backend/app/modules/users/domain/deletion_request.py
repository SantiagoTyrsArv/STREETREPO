from enum import StrEnum


class DeletionRequestStatus(StrEnum):
    """Estado del trámite de supresión. Valores del ENUM ``estado`` de ``solicitud_supresion``."""

    PENDING = "pendiente"
    ATTENDED = "atendida"
