"""Caso de uso: crear un reporte con foto y evaluarlo (HU-02, HU-05, HU-07)."""

import logging
import uuid
from dataclasses import dataclass

from app.modules.reports.domain.duplicates import MAX_DUPLICATE_CANDIDATES, PossibleDuplicateError
from app.modules.reports.domain.entities import ReportDetails
from app.modules.reports.domain.new_report import (
    IdempotencyKeyReusedError,
    NewReport,
    clean_description,
)
from app.modules.reports.domain.photos import (
    MAX_PHOTO_BYTES,
    STORED_PHOTO_FORMAT,
    PhotoKeys,
    PhotoTooLargeError,
    StoredEvidence,
)
from app.modules.reports.domain.ports import (
    DuplicateIdempotencyKeyError,
    DuplicateWarningRecorder,
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
    # Aviso que la app mostró antes (objetivo 4); con ``create_anyway`` queda «creo_igual».
    duplicate_warning_id: uuid.UUID | None = None


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

    Cada aviso que se muestra queda registrado (objetivo 4): el de la primera verificación
    se confirma antes del 409, y el ``duplicate_warning_id`` de un ``create_anyway`` se
    resuelve como «creo_igual» en la misma transacción que crea el reporte.
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
        warnings: DuplicateWarningRecorder,
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
        self._warnings = warnings

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
        self._reject_possible_duplicates(submission, record_warning=True)
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
            # La segunda verificación (otro reporte cercano llegó en el instante entre
            # las dos) no registra aviso: es una carrera rara y registrarlo obligaría a
            # confirmar la transacción a medias.
            self._reject_possible_duplicates(submission, record_warning=False)
            report_id = self._reports.add(report)
            self._statuses.apply(report_id, initial_status_change(submission.user_id))
            self._reports.add_evidence(
                report_id,
                StoredEvidence(keys.photo, STORED_PHOTO_FORMAT, len(photo.content)),
            )
            self._evaluator.evaluate(report_id)
            self._resolve_warning(submission, report_id)
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

    def _reject_possible_duplicates(
        self, submission: ReportSubmission, *, record_warning: bool
    ) -> None:
        if submission.create_anyway:
            return
        candidates = self._nearby.find_active_within(
            submission.location,
            DEDUPLICATION_RADIUS_M,
            MAX_DUPLICATE_CANDIDATES,
            submission.user_id,
        )
        if not candidates:
            return
        warning_id = None
        if record_warning:
            # Se confirma ya: el 409 no crea nada más y el aviso debe sobrevivirlo.
            try:
                warning_id = self._warnings.record(
                    submission.user_id, submission.location, candidates
                )
                self._transaction.commit()
            except Exception:
                self._transaction.rollback()
                raise
        raise PossibleDuplicateError(candidates, warning_id)

    def _resolve_warning(self, submission: ReportSubmission, report_id: uuid.UUID) -> None:
        if not submission.create_anyway or submission.duplicate_warning_id is None:
            return
        # Un aviso ajeno, ya resuelto o inexistente devuelve False y no se toca.
        self._warnings.resolve(
            submission.duplicate_warning_id, submission.user_id, "creo_igual", report_id
        )

    def _find_replayed(self, submission: ReportSubmission) -> CreateReportResult | None:
        if submission.idempotency_key is None:
            return None
        existing = self._reports.find_by_idempotency_key(
            submission.user_id, submission.idempotency_key
        )
        if existing is None:
            return None
        details = self._details(existing)
        # La foto no se compara: se guarda recodificada y no se puede cotejar con la original.
        if (
            details.location != submission.location
            or details.severity is not submission.severity
            or details.description != clean_description(submission.description)
        ):
            raise IdempotencyKeyReusedError(str(submission.idempotency_key))
        return CreateReportResult(details, created=False)

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
