import uuid
from typing import Protocol

from app.modules.reports.domain.entities import ReportDetails
from app.modules.reports.domain.new_report import NewReport
from app.modules.reports.domain.photos import ProcessedPhoto, StoredEvidence
from app.modules.reports.domain.status_machine import StatusChange


class StatusHistoryRecorder(Protocol):
    def apply(self, report_id: uuid.UUID, change: StatusChange) -> None:
        """Cambia el estado del reporte y deja el registro en el historial."""
        ...


class DuplicateIdempotencyKeyError(Exception):
    """Otro envío del mismo usuario con la misma clave se guardó primero."""


class ReportRepository(Protocol):
    def find_by_idempotency_key(self, user_id: uuid.UUID, key: uuid.UUID) -> uuid.UUID | None:
        """Reporte que el usuario ya creó con esa clave, si existe."""
        ...

    def add(self, report: NewReport) -> uuid.UUID:
        """Guarda el reporte en estado registrado; lanza ``DuplicateIdempotencyKeyError``
        si la clave ya la usó el mismo usuario."""
        ...

    def add_evidence(self, report_id: uuid.UUID, evidence: StoredEvidence) -> None: ...

    def get_details(self, report_id: uuid.UUID) -> ReportDetails | None: ...


class PriorityEvaluator(Protocol):
    """Motor de priorización (módulo ``priority``); no confirma la transacción."""

    def evaluate(self, report_id: uuid.UUID) -> object: ...


class PhotoProcessor(Protocol):
    def process(self, raw: bytes) -> ProcessedPhoto:
        """Valida el tipo real y recodifica. Lanza ``UnsupportedPhotoTypeError`` o
        ``InvalidPhotoError``."""
        ...


class PhotoStorage(Protocol):
    """Archivos fuera de la base de datos, con la clave relativa en ``evidencia`` (guía 11)."""

    def save(self, key: str, content: bytes) -> None: ...

    def delete(self, key: str) -> None:
        """Borra el archivo; no falla si ya no existe."""
        ...
