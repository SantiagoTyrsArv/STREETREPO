"""Caso de uso SeedDemo con dobles en memoria (decisión 76)."""

import uuid
from collections import Counter
from collections.abc import Sequence
from datetime import UTC, datetime

import pytest

from app.modules.admin.application.demo_seed import SeedDemo
from app.modules.admin.domain.demo import (
    DEMO_ADMIN_EMAIL,
    DEMO_CITIZEN_EMAIL,
    DEMO_CREDENTIAL_MARKER,
    DEMO_DESCRIPTION,
    DEMO_NEAR_SERVICE_COUNT,
    DEMO_OFF_ROAD_COUNT,
    DEMO_PRIORITIZED_COUNT,
    DEMO_REPAIRED_COUNT,
    DEMO_REPORT_COUNT,
    DEMO_ROAD_QUOTAS,
    DemoPoint,
    DemoRemoval,
    NotEnoughOsmDataError,
)
from app.modules.admin.infrastructure.demo_points import (
    MIN_SEPARATION_M,
    _distance_m,
    _Selection,
)
from app.modules.reports.domain.new_report import NewReport
from app.modules.reports.domain.photos import PhotoKeys, ProcessedPhoto, StoredEvidence
from app.modules.reports.domain.severity import Severity
from app.modules.reports.domain.status import ReportStatus
from app.modules.reports.domain.status_machine import StatusChange
from app.modules.users.domain.entities import NewUser, User
from app.modules.users.domain.role import UserRole
from app.shared.domain.geo import BoundingBox, GeoPoint

PASTO_AREA = BoundingBox(south=1.16, west=-77.33, north=1.25, east=-77.23)
SEVERITIES = (Severity.LOW, Severity.MEDIUM, Severity.HIGH)


def _points(count: int = DEMO_REPORT_COUNT) -> list[DemoPoint]:
    return [
        DemoPoint(GeoPoint(longitude=-77.30 + index * 0.001, latitude=1.20), SEVERITIES[index % 3])
        for index in range(count)
    ]


class FakeUsers:
    def __init__(self) -> None:
        self.by_email: dict[str, User] = {}

    def get_by_email(self, email: str) -> User | None:
        return self.by_email.get(email)

    def add(self, user: NewUser) -> User:
        created = User(
            id=uuid.uuid4(),
            name=user.name,
            email=user.email,
            password_hash=user.password_hash,
            role=user.role,
            is_active=True,
            consent=user.consent,
            registered_at=datetime(2026, 11, 11, tzinfo=UTC),
        )
        self.by_email[user.email] = created
        return created


class FakePoints:
    def __init__(self, points: Sequence[DemoPoint]) -> None:
        self.points = points
        self.areas: list[BoundingBox] = []

    def pick(self, area: BoundingBox) -> Sequence[DemoPoint]:
        self.areas.append(area)
        return self.points


class FakeReports:
    def __init__(self) -> None:
        self.added: dict[uuid.UUID, NewReport] = {}
        self.evidence: dict[uuid.UUID, StoredEvidence] = {}

    def add(self, report: NewReport) -> uuid.UUID:
        report_id = uuid.uuid4()
        self.added[report_id] = report
        return report_id

    def add_evidence(self, report_id: uuid.UUID, evidence: StoredEvidence) -> None:
        self.evidence[report_id] = evidence


class FakeStatuses:
    def __init__(self) -> None:
        self.changes: dict[uuid.UUID, list[StatusChange]] = {}

    def apply(self, report_id: uuid.UUID, change: StatusChange) -> None:
        self.changes.setdefault(report_id, []).append(change)

    def final_statuses(self) -> Counter[ReportStatus]:
        return Counter(changes[-1].new for changes in self.changes.values())


class FakeEvaluator:
    """Como el motor real: evalúa y pasa el reporte de registrado a evaluado."""

    def __init__(self, statuses: FakeStatuses, fail_at: int | None = None) -> None:
        self._statuses = statuses
        self._fail_at = fail_at
        self.evaluated: list[uuid.UUID] = []

    def evaluate(self, report_id: uuid.UUID) -> object:
        if self._fail_at == len(self.evaluated):
            raise RuntimeError("el motor falló")
        self.evaluated.append(report_id)
        self._statuses.apply(
            report_id,
            StatusChange(
                ReportStatus.REGISTERED, ReportStatus.EVALUATED, changed_by=None, note=None
            ),
        )
        return None


class FakeProcessor:
    def __init__(self) -> None:
        self.processed: list[bytes] = []

    def process(self, raw: bytes) -> ProcessedPhoto:
        self.processed.append(raw)
        return ProcessedPhoto(content=b"jpeg:" + raw, thumbnail=b"min:" + raw)


class FakeStorage:
    def __init__(self) -> None:
        self.files: dict[str, bytes] = {}

    def save(self, key: str, content: bytes) -> None:
        self.files[key] = content

    def delete(self, key: str) -> None:
        self.files.pop(key, None)


class FakePhotoFiles:
    def __init__(self, storage: FakeStorage, log: list[str]) -> None:
        self._storage = storage
        self._log = log

    def remove(self, photo_keys: Sequence[str]) -> Sequence[str]:
        self._log.append("archivos")
        for photo_key in photo_keys:
            keys = PhotoKeys.from_photo_key(photo_key)
            self._storage.delete(keys.photo)
            self._storage.delete(keys.thumbnail)
        return []


class FakeDemoData:
    def __init__(self, removal: DemoRemoval, log: list[str]) -> None:
        self._removal = removal
        self._log = log

    def delete_all(self) -> DemoRemoval:
        self._log.append("filas")
        return self._removal


class FakeTransaction:
    def __init__(self, log: list[str]) -> None:
        self._log = log
        self.commits = 0
        self.rollbacks = 0

    def commit(self) -> None:
        self._log.append("commit")
        self.commits += 1

    def rollback(self) -> None:
        self.rollbacks += 1


class Scenario:
    def __init__(
        self,
        points: Sequence[DemoPoint] | None = None,
        *,
        evaluator_fails_at: int | None = None,
        removal: DemoRemoval | None = None,
        photos: Sequence[bytes] = (b"a", b"b", b"c"),
    ) -> None:
        self.log: list[str] = []
        self.users = FakeUsers()
        self.points = FakePoints(_points() if points is None else points)
        self.reports = FakeReports()
        self.statuses = FakeStatuses()
        self.evaluator = FakeEvaluator(self.statuses, evaluator_fails_at)
        self.processor = FakeProcessor()
        self.storage = FakeStorage()
        self.transaction = FakeTransaction(self.log)
        self.seed = SeedDemo(
            users=self.users,
            points=self.points,
            reports=self.reports,
            statuses=self.statuses,
            evaluator=self.evaluator,
            photo_processor=self.processor,
            photo_storage=self.storage,
            photo_files=FakePhotoFiles(self.storage, self.log),
            demo_data=FakeDemoData(removal or DemoRemoval(0, 0, ()), self.log),
            photos=photos,
            service_area=PASTO_AREA,
            transaction=self.transaction,
        )


def test_demo_counts_add_up() -> None:
    assert (
        sum(DEMO_ROAD_QUOTAS.values()) + DEMO_NEAR_SERVICE_COUNT + DEMO_OFF_ROAD_COUNT
        == DEMO_REPORT_COUNT
    )


def test_seed_creates_one_report_per_point() -> None:
    scenario = Scenario()

    assert scenario.seed.execute() == DEMO_REPORT_COUNT

    assert scenario.points.areas == [PASTO_AREA]
    citizen = scenario.users.by_email[DEMO_CITIZEN_EMAIL]
    reports = list(scenario.reports.added.values())
    assert [(report.location, report.severity) for report in reports] == [
        (point.location, point.severity) for point in _points()
    ]
    assert {report.user_id for report in reports} == {citizen.id}
    assert {report.description for report in reports} == {DEMO_DESCRIPTION}
    assert scenario.transaction.commits == 1


def test_seed_is_idempotent() -> None:
    scenario = Scenario()
    scenario.seed.execute()

    assert scenario.seed.execute() == 0

    assert len(scenario.reports.added) == DEMO_REPORT_COUNT
    assert len(scenario.evaluator.evaluated) == DEMO_REPORT_COUNT
    assert scenario.transaction.commits == 1


def test_seed_uses_engine_evaluation() -> None:
    scenario = Scenario()

    scenario.seed.execute()

    assert scenario.evaluator.evaluated == list(scenario.reports.added)


def test_seed_accounts_cannot_log_in() -> None:
    scenario = Scenario()

    scenario.seed.execute()

    citizen = scenario.users.by_email[DEMO_CITIZEN_EMAIL]
    admin = scenario.users.by_email[DEMO_ADMIN_EMAIL]
    assert (citizen.role, admin.role) == (UserRole.CITIZEN, UserRole.ADMIN)
    assert {citizen.password_hash, admin.password_hash} == {DEMO_CREDENTIAL_MARKER}


def test_seed_moves_some_reports_forward_signed_by_the_demo_admin() -> None:
    scenario = Scenario()

    scenario.seed.execute()

    assert scenario.statuses.final_statuses() == {
        ReportStatus.EVALUATED: DEMO_REPORT_COUNT - DEMO_PRIORITIZED_COUNT - DEMO_REPAIRED_COUNT,
        ReportStatus.PRIORITIZED: DEMO_PRIORITIZED_COUNT,
        ReportStatus.REPAIRED: DEMO_REPAIRED_COUNT,
    }
    admin = scenario.users.by_email[DEMO_ADMIN_EMAIL]
    citizen = scenario.users.by_email[DEMO_CITIZEN_EMAIL]
    for changes in scenario.statuses.changes.values():
        assert changes[0] == StatusChange(None, ReportStatus.REGISTERED, citizen.id, None)
        assert changes[1].changed_by is None
        for change in changes[2:]:
            assert change.changed_by == admin.id
            assert change.note is not None
            assert change.note.startswith("Demostración")
    # Cada estado recibe las tres severidades: el ranking filtrado no queda de un solo tipo.
    reports = scenario.reports.added
    for status in (ReportStatus.PRIORITIZED, ReportStatus.REPAIRED):
        severities = {
            reports[report_id].severity
            for report_id, changes in scenario.statuses.changes.items()
            if changes[-1].new is status
        }
        assert severities == set(SEVERITIES)


def test_seed_gives_each_report_its_own_photo_files() -> None:
    scenario = Scenario()

    scenario.seed.execute()

    # Las fotos de origen se procesan una sola vez y se reparten en ciclo.
    assert scenario.processor.processed == [b"a", b"b", b"c"]
    evidence = list(scenario.reports.evidence.values())
    assert len({item.photo_key for item in evidence}) == DEMO_REPORT_COUNT
    assert len(scenario.storage.files) == 2 * DEMO_REPORT_COUNT
    for index, item in enumerate(evidence):
        source = (b"a", b"b", b"c")[index % 3]
        keys = PhotoKeys.from_photo_key(item.photo_key)
        assert scenario.storage.files[keys.photo] == b"jpeg:" + source
        assert scenario.storage.files[keys.thumbnail] == b"min:" + source
        assert item.size_bytes == len(b"jpeg:" + source)


def test_seed_without_enough_points_writes_nothing() -> None:
    scenario = Scenario(_points(DEMO_REPORT_COUNT - 1))

    with pytest.raises(NotEnoughOsmDataError, match="osm-import"):
        scenario.seed.execute()

    assert scenario.users.by_email == {}
    assert scenario.reports.added == {}
    assert scenario.storage.files == {}
    assert scenario.transaction.commits == 0


def test_seed_failure_rolls_back_and_removes_the_saved_photos() -> None:
    scenario = Scenario(evaluator_fails_at=5)

    with pytest.raises(RuntimeError, match="el motor falló"):
        scenario.seed.execute()

    assert scenario.transaction.commits == 0
    assert scenario.transaction.rollbacks == 1
    assert scenario.storage.files == {}


def test_seed_requires_photos() -> None:
    with pytest.raises(ValueError, match="foto"):
        Scenario(photos=())


def test_remove_deletes_rows_then_files_after_commit() -> None:
    keys = PhotoKeys.for_name("ab12")
    scenario = Scenario(removal=DemoRemoval(reports=32, users=2, photo_keys=(keys.photo,)))
    scenario.storage.save(keys.photo, b"foto")
    scenario.storage.save(keys.thumbnail, b"miniatura")

    assert scenario.seed.remove() == 32

    assert scenario.log == ["filas", "commit", "archivos"]
    assert scenario.storage.files == {}


class FailingDemoData:
    def delete_all(self) -> DemoRemoval:
        raise RuntimeError("la base falló")


def test_remove_failure_rolls_back_and_keeps_the_files() -> None:
    keys = PhotoKeys.for_name("ab12")
    scenario = Scenario()
    scenario.storage.save(keys.photo, b"foto")
    scenario.seed = SeedDemo(
        users=scenario.users,
        points=scenario.points,
        reports=scenario.reports,
        statuses=scenario.statuses,
        evaluator=scenario.evaluator,
        photo_processor=scenario.processor,
        photo_storage=scenario.storage,
        photo_files=FakePhotoFiles(scenario.storage, scenario.log),
        demo_data=FailingDemoData(),
        photos=(b"a",),
        service_area=PASTO_AREA,
        transaction=scenario.transaction,
    )

    with pytest.raises(RuntimeError, match="la base falló"):
        scenario.seed.remove()

    assert scenario.transaction.rollbacks == 1
    assert scenario.log == []
    assert scenario.storage.files == {keys.photo: b"foto"}


def test_selection_skips_repeated_roads_close_points_and_points_outside() -> None:
    selection = _Selection(PASTO_AREA)
    first = GeoPoint(longitude=-77.30, latitude=1.20)
    # 0,0003° ≈ 33 m: dentro de la separación mínima.
    too_close = GeoPoint(longitude=-77.3003, latitude=1.20)
    same_road = GeoPoint(longitude=-77.29, latitude=1.20)
    outside = GeoPoint(longitude=-77.50, latitude=1.20)
    second = GeoPoint(longitude=-77.28, latitude=1.20)
    extra = GeoPoint(longitude=-77.27, latitude=1.20)

    selection.take(
        [(1, first), (2, too_close), (1, same_road), (3, outside), (4, second), (5, extra)], 2
    )

    assert selection.locations == [first, second]


def test_distance_between_points_is_close_to_the_geodesic() -> None:
    a = GeoPoint(longitude=-77.30, latitude=1.20)
    # 0,001° de latitud ≈ 110,57 m cerca del ecuador.
    assert _distance_m(a, GeoPoint(longitude=-77.30, latitude=1.201)) == pytest.approx(111.2, abs=1)
    assert MIN_SEPARATION_M == 50
