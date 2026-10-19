"""Caso de uso CreateReport con dobles en memoria."""

import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from app.modules.reports.application.create_report import (
    CreateReport,
    CreateReportPolicy,
    ReportSubmission,
)
from app.modules.reports.domain.duplicates import DuplicateCandidate, PossibleDuplicateError
from app.modules.reports.domain.entities import ReportDetails
from app.modules.reports.domain.new_report import LocationOutsideServiceAreaError, NewReport
from app.modules.reports.domain.photos import (
    MAX_PHOTO_BYTES,
    STORED_PHOTO_FORMAT,
    PhotoKeys,
    PhotoTooLargeError,
    ProcessedPhoto,
    StoredEvidence,
    UnsupportedPhotoTypeError,
)
from app.modules.reports.domain.ports import DuplicateIdempotencyKeyError, PhotoProcessor
from app.modules.reports.domain.severity import Severity
from app.modules.reports.domain.status import ReportStatus
from app.modules.reports.domain.status_machine import StatusChange
from app.shared.application.rate_limit import RateLimit, RateLimitExceededError
from app.shared.domain.geo import BoundingBox, GeoPoint
from app.shared.domain.geo_parameters import DEDUPLICATION_RADIUS_M
from app.shared.infrastructure.memory_rate_limiter import InMemoryRateLimiter

USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
PASTO = GeoPoint(longitude=-77.2811, latitude=1.2136)
BOGOTA = GeoPoint(longitude=-74.0721, latitude=4.7110)
NOW = datetime(2026, 10, 19, 12, tzinfo=UTC)
TWO_PER_HOUR = RateLimit(max_requests=2, window=timedelta(hours=1))
PROCESSED = ProcessedPhoto(content=b"jpeg-recodificado", thumbnail=b"miniatura")


class FakeReports:
    def __init__(self) -> None:
        self.saved: dict[uuid.UUID, NewReport] = {}
        self.evidence: dict[uuid.UUID, StoredEvidence] = {}
        self.pending: dict[uuid.UUID, NewReport] = {}
        # Simula otro envío simultáneo con la misma clave que se confirma primero.
        self.race_winner: uuid.UUID | None = None

    def find_by_idempotency_key(self, user_id: uuid.UUID, key: uuid.UUID) -> uuid.UUID | None:
        return next(
            (
                report_id
                for report_id, report in self.saved.items()
                if report.user_id == user_id and report.idempotency_key == key
            ),
            None,
        )

    def add(self, report: NewReport) -> uuid.UUID:
        if self.race_winner is not None:
            self.saved[self.race_winner] = report
            raise DuplicateIdempotencyKeyError(str(report.idempotency_key))
        report_id = uuid.uuid4()
        self.pending[report_id] = report
        return report_id

    def add_evidence(self, report_id: uuid.UUID, evidence: StoredEvidence) -> None:
        self.evidence[report_id] = evidence

    def get_details(self, report_id: uuid.UUID) -> ReportDetails | None:
        report = self.saved.get(report_id)
        if report is None:
            return None
        return ReportDetails(
            id=report_id,
            user_id=report.user_id,
            location=report.location,
            severity=report.severity,
            description=report.description,
            status=ReportStatus.EVALUATED,
            priority_score=Decimal("8.70"),
            road_id=1,
            road_name="Avenida Los Estudiantes",
            created_at=NOW,
        )

    def commit(self) -> None:
        self.saved |= self.pending
        self.pending = {}


class FakeTransaction:
    def __init__(self, reports: FakeReports) -> None:
        self._reports = reports
        self.commits = 0
        self.rollbacks = 0

    def commit(self) -> None:
        self.commits += 1
        self._reports.commit()

    def rollback(self) -> None:
        self.rollbacks += 1
        self._reports.pending = {}


class FakeStatuses:
    def __init__(self) -> None:
        self.changes: list[tuple[uuid.UUID, StatusChange]] = []

    def apply(self, report_id: uuid.UUID, change: StatusChange) -> None:
        self.changes.append((report_id, change))


class FakeEvaluator:
    def __init__(self, fail: bool = False) -> None:
        self.evaluated: list[uuid.UUID] = []
        self._fail = fail

    def evaluate(self, report_id: uuid.UUID) -> object:
        if self._fail:
            raise RuntimeError("fallo del motor")
        self.evaluated.append(report_id)
        return object()


class FakeProcessor:
    def __init__(self, error: Exception | None = None) -> None:
        self.calls = 0
        self._error = error

    def process(self, raw: bytes) -> ProcessedPhoto:
        self.calls += 1
        if self._error is not None:
            raise self._error
        return PROCESSED


class FakeStorage:
    def __init__(self) -> None:
        self.files: dict[str, bytes] = {}
        self.deleted: list[str] = []

    def save(self, key: str, content: bytes) -> None:
        self.files[key] = content

    def delete(self, key: str) -> None:
        self.deleted.append(key)
        self.files.pop(key, None)


def candidate(distance_m: float = 12.5) -> DuplicateCandidate:
    return DuplicateCandidate(
        id=uuid.uuid4(),
        location=GeoPoint(longitude=-77.28111, latitude=1.21366),
        distance_m=distance_m,
        status=ReportStatus.EVALUATED,
        severity=Severity.MEDIUM,
        confirmations=3,
        road_id=1,
        road_name="Carrera 27",
        created_at=NOW,
    )


class FakeNearby:
    """Responde en orden lo que haya en ``responses``; después, ``default``."""

    def __init__(self) -> None:
        self.default: list[DuplicateCandidate] = []
        self.responses: list[list[DuplicateCandidate]] = []
        self.calls: list[tuple[GeoPoint, float]] = []

    def find_active_within(
        self, point: GeoPoint, radius_m: float, limit: int
    ) -> list[DuplicateCandidate]:
        self.calls.append((point, radius_m))
        return self.responses.pop(0) if self.responses else self.default


class FakeLock:
    def __init__(self, events: list[str], on_acquire: object = None) -> None:
        self._events = events
        self.on_acquire = on_acquire

    def acquire(self) -> None:
        self._events.append("lock")
        if callable(self.on_acquire):
            self.on_acquire()


class FixedClock:
    def now(self) -> datetime:
        return NOW


class Harness:
    def __init__(
        self, *, evaluator: FakeEvaluator | None = None, processor: PhotoProcessor | None = None
    ) -> None:
        self.reports = FakeReports()
        self.events: list[str] = []
        self.nearby = FakeNearby()
        self.lock = FakeLock(self.events)
        self.transaction = FakeTransaction(self.reports)
        self.statuses = FakeStatuses()
        self.evaluator = evaluator or FakeEvaluator()
        self.processor = processor or FakeProcessor()
        self.storage = FakeStorage()
        self.limiter = InMemoryRateLimiter()
        self.use_case = CreateReport(
            reports=self.reports,
            nearby=self.nearby,
            creation_lock=self.lock,
            statuses=self.statuses,
            evaluator=self.evaluator,
            photo_processor=self.processor,
            photo_storage=self.storage,
            rate_limiter=self.limiter,
            policy=CreateReportPolicy(
                service_area=BoundingBox.parse("1.16,-77.33,1.25,-77.23"),
                limit_per_user=TWO_PER_HOUR,
            ),
            clock=FixedClock(),
            transaction=self.transaction,
        )


def _submission(
    *,
    location: GeoPoint = PASTO,
    key: uuid.UUID | None = None,
    photo: bytes = b"foto-original",
    create_anyway: bool = False,
) -> ReportSubmission:
    return ReportSubmission(
        user_id=USER_ID,
        location=location,
        severity=Severity.HIGH,
        description="  Hueco profundo  ",
        idempotency_key=key,
        photo=photo,
        create_anyway=create_anyway,
    )


def test_creates_the_report_with_photo_history_and_evaluation() -> None:
    harness = Harness()

    result = harness.use_case.execute(_submission())

    assert result.created
    report_id = result.report.id
    saved = harness.reports.saved[report_id]
    assert saved.description == "Hueco profundo"
    # El historial empieza en «registrado», hecho por el ciudadano.
    assert harness.statuses.changes == [
        (report_id, StatusChange(None, ReportStatus.REGISTERED, USER_ID, None))
    ]
    assert harness.evaluator.evaluated == [report_id]
    assert harness.transaction.commits == 1
    # Se guarda la foto recodificada, nunca la original, y su miniatura.
    evidence = harness.reports.evidence[report_id]
    keys = PhotoKeys.from_photo_key(evidence.photo_key)
    assert harness.storage.files == {keys.photo: PROCESSED.content, keys.thumbnail: b"miniatura"}
    assert evidence == StoredEvidence(keys.photo, STORED_PHOTO_FORMAT, len(PROCESSED.content))


def test_retry_with_the_same_key_returns_the_existing_report() -> None:
    harness = Harness()
    key = uuid.uuid4()
    first = harness.use_case.execute(_submission(key=key))

    second = harness.use_case.execute(_submission(key=key))

    assert not second.created
    assert second.report.id == first.report.id
    assert len(harness.reports.saved) == 1
    # El reintento no procesa otra vez la foto ni consume cupo.
    assert harness.processor.calls == 1
    harness.use_case.execute(_submission())


def test_the_same_key_from_another_user_is_a_different_report() -> None:
    harness = Harness()
    key = uuid.uuid4()
    harness.use_case.execute(_submission(key=key))

    other = ReportSubmission(
        user_id=uuid.uuid4(),
        location=PASTO,
        severity=Severity.LOW,
        description=None,
        idempotency_key=key,
        photo=b"foto",
    )

    assert harness.use_case.execute(other).created


def test_concurrent_retry_returns_the_report_that_won_and_removes_the_photo() -> None:
    harness = Harness()
    key = uuid.uuid4()
    harness.reports.race_winner = uuid.uuid4()

    result = harness.use_case.execute(_submission(key=key))

    assert not result.created
    assert result.report.id == harness.reports.race_winner
    assert harness.transaction.rollbacks == 1
    assert harness.storage.files == {}


def test_location_outside_the_area_is_rejected_without_using_the_quota() -> None:
    harness = Harness()

    with pytest.raises(LocationOutsideServiceAreaError):
        harness.use_case.execute(_submission(location=BOGOTA))

    assert harness.processor.calls == 0
    for _ in range(TWO_PER_HOUR.max_requests):
        harness.use_case.execute(_submission())


def test_photo_over_the_size_limit_is_rejected_before_processing() -> None:
    harness = Harness()

    with pytest.raises(PhotoTooLargeError):
        harness.use_case.execute(_submission(photo=b"x" * (MAX_PHOTO_BYTES + 1)))

    assert harness.processor.calls == 0


def test_user_over_the_hourly_limit_is_rejected() -> None:
    harness = Harness()
    for _ in range(TWO_PER_HOUR.max_requests):
        harness.use_case.execute(_submission())

    with pytest.raises(RateLimitExceededError) as exceeded:
        harness.use_case.execute(_submission())

    assert exceeded.value.retry_after == timedelta(hours=1)
    assert len(harness.reports.saved) == TWO_PER_HOUR.max_requests


def test_invalid_photo_creates_nothing() -> None:
    harness = Harness(processor=FakeProcessor(UnsupportedPhotoTypeError("gif")))

    with pytest.raises(UnsupportedPhotoTypeError):
        harness.use_case.execute(_submission())

    assert harness.reports.saved == {}
    assert harness.storage.files == {}


def test_failure_during_the_transaction_rolls_back_and_removes_the_files() -> None:
    harness = Harness(evaluator=FakeEvaluator(fail=True))

    with pytest.raises(RuntimeError, match="motor"):
        harness.use_case.execute(_submission())

    assert harness.transaction.rollbacks == 1
    assert harness.transaction.commits == 0
    assert harness.reports.saved == {}
    assert harness.storage.files == {}
    assert len(harness.storage.deleted) == 2


def test_a_failed_cleanup_does_not_hide_the_original_error() -> None:
    harness = Harness(evaluator=FakeEvaluator(fail=True))

    def broken_delete(key: str) -> None:
        raise OSError("disco no disponible")

    harness.storage.delete = broken_delete  # type: ignore[method-assign]

    with pytest.raises(RuntimeError, match="motor"):
        harness.use_case.execute(_submission())


# --- Posible duplicado a 25 m (propuesta 36) -------------------------------------


def test_active_report_nearby_is_offered_instead_of_creating_another() -> None:
    harness = Harness()
    existing = candidate()
    harness.nearby.default = [existing]

    with pytest.raises(PossibleDuplicateError) as duplicate:
        harness.use_case.execute(_submission())

    assert duplicate.value.candidates == (existing,)
    assert harness.nearby.calls == [(PASTO, DEDUPLICATION_RADIUS_M)]
    # Se avisa antes de procesar la foto y sin consumir cupo.
    assert harness.processor.calls == 0
    assert harness.reports.saved == {}
    harness.nearby.default = []
    for _ in range(TWO_PER_HOUR.max_requests):
        harness.use_case.execute(_submission())


def test_create_anyway_creates_the_report_next_to_the_existing_one() -> None:
    harness = Harness()
    harness.nearby.default = [candidate()]

    result = harness.use_case.execute(_submission(create_anyway=True))

    assert result.created
    assert harness.nearby.calls == []


def test_retry_of_a_created_report_is_not_taken_as_its_own_duplicate() -> None:
    harness = Harness()
    key = uuid.uuid4()
    first = harness.use_case.execute(_submission(key=key))
    # Ahora el reporte recién creado está a 0 m del punto del reintento.
    harness.nearby.default = [candidate(distance_m=0.0)]

    retry = harness.use_case.execute(_submission(key=key))

    assert not retry.created
    assert retry.report.id == first.report.id


def test_the_check_is_repeated_inside_the_transaction_with_the_lock_held() -> None:
    harness = Harness()
    # Libre en la primera consulta; otro ciudadano crea uno cercano antes del candado.
    harness.nearby.responses = [[], [candidate(distance_m=4.0)]]

    with pytest.raises(PossibleDuplicateError):
        harness.use_case.execute(_submission())

    assert harness.events == ["lock"]
    assert len(harness.nearby.calls) == 2
    assert harness.transaction.rollbacks == 1
    assert harness.reports.saved == {}
    assert harness.storage.files == {}


def test_lock_is_taken_before_inserting() -> None:
    harness = Harness()
    inserted_before_lock: list[bool] = []
    harness.lock.on_acquire = lambda: inserted_before_lock.append(bool(harness.reports.pending))

    harness.use_case.execute(_submission())

    assert inserted_before_lock == [False]


def test_same_key_saved_by_a_concurrent_request_while_waiting_for_the_lock() -> None:
    harness = Harness()
    key = uuid.uuid4()
    winner = uuid.uuid4()

    def other_request_commits() -> None:
        harness.reports.saved[winner] = NewReport.create(
            user_id=USER_ID,
            location=PASTO,
            severity=Severity.HIGH,
            description=None,
            idempotency_key=key,
            service_area=BoundingBox.parse("1.16,-77.33,1.25,-77.23"),
        )
        # Para este envío, el ganador sería un duplicado a 0 m.
        harness.nearby.default = [candidate(distance_m=0.0)]

    harness.lock.on_acquire = other_request_commits

    result = harness.use_case.execute(_submission(key=key))

    assert not result.created
    assert result.report.id == winner
    assert harness.storage.files == {}
    assert harness.transaction.commits == 0
