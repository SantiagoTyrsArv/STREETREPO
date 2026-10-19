"""Caso de uso: crear un reporte con foto y evaluarlo (HU-02, HU-05, HU-07)."""

import logging
import uuid
from dataclasses import dataclass

from app.modules.reports.domain.duplicates import MAX_DUPLICATE_CANDIDATES, PossibleDuplicateError
from app.modules.reports.domain.entities import ReportDetails
from app.modules.reports.domain.new_report import NewReport
from app.modules.reports.domain.photos import (
    MAX_PHOTO_BYTES,
    STORED_PHOTO_FORMAT,
    PhotoKeys,
    PhotoTooLargeError,
    StoredEvidence,
)
from app.modules.reports.domain.ports import (
    DuplicateIdempotencyKeyError,
    NearbyReportFinder,
    PhotoProcessor,
    PhotoStorage,
    PriorityEvaluator,
    ReportCreationLock,
    ReportRepository,
    StatusHistoryRecorder,
)
from app.modules.reports.domain.severity import Severity
from app.modules.reports.domain.status_machine import initial_status_change
from app.shared.application.clock import Clock
from app.shared.application.rate_limit import RateLimit, RateLimiter
from app.shared.application.transaction import TransactionManager
from app.shared.domain.geo import BoundingBox, GeoPoint
from app.shared.domain.geo_parameters import DEDUPLICATION_RADIUS_M

logger = logging.getLogger(__name__)


class ReportVanishedError(Exception):
    """El reporte recién guardado o el de la clave de idempotencia no se pudo leer."""


@dataclass(frozen=True, slots=True)
class ReportSubmission:
    user_id: uuid.UUID
    location: GeoPoint
    severity: Severity
    description: str | None
    idempotency_key: uuid.UUID | None
    photo: bytes
    # El ciudadano vio los posibles duplicados y decidió crear el reporte (guía 2.5).
    create_anyway: bool = False


@dataclass(frozen=True, slots=True)
class CreateReportResult:
    report: ReportDetails
    # False = reintento con una clave de idempotencia ya usada: se devuelve el existente.
    created: bool


@dataclass(frozen=True, slots=True)
class CreateReportPolicy:
    service_area: BoundingBox
    limit_per_user: RateLimit


class CreateReport:
    """Guarda el reporte, su foto, el historial y la evaluación del motor en una transacción.

    Registrado → Evaluado ocurre aquí mismo por el motor (guía 2.4). Los archivos de
    la foto se escriben antes de la transacción y se borran si esta no se confirma.

    Si hay reportes activos a 25 m y el ciudadano no pidió crearlo de todos modos, lanza
    ``PossibleDuplicateError`` (propuesta 36). La verificación se repite dentro de la
    transacción que inserta, con el candado de creación tomado.
    """

    def __init__(
        self,
        *,
        reports: ReportRepository,
        nearby: NearbyReportFinder,
        creation_lock: ReportCreationLock,
        statuses: StatusHistoryRecorder,
        evaluator: PriorityEvaluator,
        photo_processor: PhotoProcessor,
        photo_storage: PhotoStorage,
        rate_limiter: RateLimiter,
        policy: CreateReportPolicy,
        clock: Clock,
        transaction: TransactionManager,
    ) -> None:
        self._reports = reports
        self._nearby = nearby
        self._creation_lock = creation_lock
        self._statuses = statuses
        self._evaluator = evaluator
        self._photo_processor = photo_processor
        self._photo_storage = photo_storage
        self._rate_limiter = rate_limiter
        self._policy = policy
        self._clock = clock
        self._transaction = transaction

    def execute(self, submission: ReportSubmission) -> CreateReportResult:
        # Un reintento de la app (red móvil inestable) devuelve el reporte ya creado
        # sin consumir cupo ni procesar otra vez la foto. Va antes de buscar duplicados:
        # si no, el reintento encontraría su propio reporte a 0 m.
        replayed = self._find_replayed(submission)
        if replayed is not None:
            return replayed

        report = NewReport.create(
            user_id=submission.user_id,
            location=submission.location,
            severity=submission.severity,
            description=submission.description,
            idempotency_key=submission.idempotency_key,
            service_area=self._policy.service_area,
        )
        if len(submission.photo) > MAX_PHOTO_BYTES:
            raise PhotoTooLargeError("La foto supera el tamaño máximo permitido")
        # Primera verificación, sin candado: avisa del duplicado sin consumir cupo.
        self._reject_possible_duplicates(submission)
        self._rate_limiter.hit(
            f"reports:user:{submission.user_id}", self._policy.limit_per_user, self._clock.now()
        )
        photo = self._photo_processor.process(submission.photo)

        keys = PhotoKeys.new()
        try:
            self._photo_storage.save(keys.photo, photo.content)
            self._photo_storage.save(keys.thumbnail, photo.thumbnail)
            # Con el candado, nadie más crea reportes hasta confirmar esta transacción:
            # lo que se verifica aquí sigue siendo cierto al insertar.
            self._creation_lock.acquire()
            replayed = self._find_replayed(submission)
            if replayed is not None:
                self._undo(keys)
                return replayed
            self._reject_possible_duplicates(submission)
            report_id = self._reports.add(report)
            self._statuses.apply(report_id, initial_status_change(submission.user_id))
            self._reports.add_evidence(
                report_id,
                StoredEvidence(keys.photo, STORED_PHOTO_FORMAT, len(photo.content)),
            )
            self._evaluator.evaluate(report_id)
            self._transaction.commit()
        except DuplicateIdempotencyKeyError:
            # Dos envíos simultáneos con la misma clave: gana el primero.
            self._undo(keys)
            replayed = self._find_replayed(submission)
            if replayed is None:
                raise
            return replayed
        except Exception:
            self._undo(keys)
            raise
        return CreateReportResult(self._details(report_id), created=True)

    def _reject_possible_duplicates(self, submission: ReportSubmission) -> None:
        if submission.create_anyway:
            return
        candidates = self._nearby.find_active_within(
            submission.location,
            DEDUPLICATION_RADIUS_M,
            MAX_DUPLICATE_CANDIDATES,
            submission.user_id,
        )
        if candidates:
            raise PossibleDuplicateError(candidates)

    def _find_replayed(self, submission: ReportSubmission) -> CreateReportResult | None:
        if submission.idempotency_key is None:
            return None
        existing = self._reports.find_by_idempotency_key(
            submission.user_id, submission.idempotency_key
        )
        if existing is None:
            return None
        return CreateReportResult(self._details(existing), created=False)

    def _details(self, report_id: uuid.UUID) -> ReportDetails:
        details = self._reports.get_details(report_id)
        if details is None:
            raise ReportVanishedError(f"No se pudo leer el reporte {report_id}")
        return details

    def _undo(self, keys: PhotoKeys) -> None:
        self._transaction.rollback()
        for key in (keys.photo, keys.thumbnail):
            try:
                self._photo_storage.delete(key)
            except OSError:
                # No debe ocultar el error original; queda un archivo huérfano sin
                # referencia en la base, que no se sirve a nadie.
                logger.exception("No se pudo borrar la foto huérfana %s", key)
