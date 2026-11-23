import uuid
from collections.abc import Sequence
from datetime import datetime
from typing import Literal, Protocol

from app.modules.reports.domain.duplicates import DuplicateCandidate
from app.modules.reports.domain.entities import ReportDetails
from app.modules.reports.domain.my_reports import MyReportsPage, PublicReportView
from app.modules.reports.domain.new_report import NewReport
from app.modules.reports.domain.photos import ProcessedPhoto, ReportPhoto, StoredEvidence
from app.modules.reports.domain.public_map import MapReport
from app.modules.reports.domain.report_view import StatusHistoryEntry
from app.modules.reports.domain.status import ReportStatus
from app.modules.reports.domain.status_machine import StatusChange
from app.shared.domain.geo import BoundingBox, GeoPoint


class StatusHistoryRecorder(Protocol):
    def apply(self, report_id: uuid.UUID, change: StatusChange) -> None:
        """Cambia el estado del reporte y deja el registro en el historial."""
        ...


class ReportStatusLock(Protocol):
    def lock_status(self, report_id: uuid.UUID) -> ReportStatus | None:
        """Estado actual con la fila bloqueada hasta el fin de la transacción; None si no existe."""
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


class NearbyReportFinder(Protocol):
    def find_active_within(
        self, point: GeoPoint, radius_m: float, limit: int, viewer_id: uuid.UUID
    ) -> Sequence[DuplicateCandidate]:
        """Reportes activos (todo estado salvo reparado) a ``radius_m``, del más cercano
        al más lejano; marca los de ``viewer_id`` con ``is_mine``."""
        ...


# Lo que decidió el ciudadano ante el aviso; el aviso nace «pendiente».
WarningDecision = Literal["confirmo", "creo_igual"]


class DuplicateWarningRecorder(Protocol):
    """Registro de los avisos de «Posible duplicado» (objetivo 4, HU-09).

    Vive aquí y no en ``validation`` para que ``reports`` no dependa de ese módulo. Ninguno
    de los dos métodos confirma la transacción: la controla el caso de uso que los llama.
    """

    def record(
        self, user_id: uuid.UUID, location: GeoPoint, candidates: Sequence[DuplicateCandidate]
    ) -> uuid.UUID:
        """Guarda un aviso ``pendiente`` con sus candidatos y devuelve su id.

        Guarda la zona que cubre ``location``, no el punto (minimización, guía 7.2)."""
        ...

    def resolve(
        self,
        warning_id: uuid.UUID,
        user_id: uuid.UUID,
        decision: WarningDecision,
        report_id: uuid.UUID,
    ) -> bool:
        """Anota la decisión si el aviso es de ``user_id`` y sigue ``pendiente``; para
        ``confirmo``, además ``report_id`` debe estar entre sus candidatos.

        Devuelve False si no aplica, sin error: un aviso inválido nunca rompe la acción
        del ciudadano."""
        ...


class PublicReportsReader(Protocol):
    def list_in_area(
        self,
        area: BoundingBox,
        status: ReportStatus | None,
        limit: int,
        viewer_id: uuid.UUID,
    ) -> Sequence[MapReport]:
        """Reportes cuya ubicación **pública** cae en ``area``, del más reciente al más
        antiguo; ``status`` filtra por estado. Marca los de ``viewer_id`` y los que confirmó."""
        ...


class ReportCreationLock(Protocol):
    def acquire(self) -> None:
        """Bloquea hasta el fin de la transacción: dos reportes no se crean a la vez, así
        la verificación de duplicados y la inserción no se cruzan entre envíos simultáneos."""
        ...


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


class PhotoInventory(Protocol):
    def list_keys(self, *, modified_before: datetime) -> Sequence[str]:
        """Claves de todos los archivos guardados (fotos y miniaturas) anteriores a la fecha."""
        ...


class EvidenceKeys(Protocol):
    def referenced_photo_keys(self) -> Sequence[str]:
        """Claves de foto que alguna fila de ``evidencia`` referencia."""
        ...


class PhotoNotStoredError(Exception):
    """El archivo de la foto no está en el almacenamiento."""


class PhotoReader(Protocol):
    def read(self, key: str) -> bytes:
        """Contenido del archivo; lanza ``PhotoNotStoredError`` si no existe."""
        ...


class ReportPhotoLookup(Protocol):
    def find_photo(self, report_id: uuid.UUID) -> ReportPhoto | None:
        """Dueño del reporte y clave de su foto más reciente; ``None`` si el reporte no existe."""
        ...


class MyReportsReader(Protocol):
    def list_for_user(self, user_id: uuid.UUID, limit: int, offset: int) -> MyReportsPage:
        """Reportes que el usuario creó o confirmó, del más reciente al más antiguo."""
        ...


class ReportViewReader(Protocol):
    def get_details(self, report_id: uuid.UUID) -> ReportDetails | None: ...

    def public_view(self, report_id: uuid.UUID) -> PublicReportView | None:
        """Vista pública: ubicación redondeada, sin autor ni descripción."""
        ...

    def confirmed_at(self, report_id: uuid.UUID, user_id: uuid.UUID) -> datetime | None:
        """Cuándo confirmó el usuario el reporte; ``None`` si no lo confirmó."""
        ...

    def confirmations(self, report_id: uuid.UUID) -> int: ...

    def history(self, report_id: uuid.UUID) -> Sequence[StatusHistoryEntry]:
        """Todos los cambios de estado, del más antiguo al más reciente."""
        ...
