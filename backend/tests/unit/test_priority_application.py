"""Motor de priorización y actualización de pesos con dobles en memoria."""

import uuid
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from app.modules.critical_services.domain.entities import NearestCriticalService
from app.modules.critical_services.domain.service_type import CriticalServiceType
from app.modules.priority.application.evaluate_report import (
    ReportEvaluator,
    ReportNotFoundError,
    WeightsNotConfiguredError,
)
from app.modules.priority.application.update_weights import UpdateWeights
from app.modules.priority.domain.entities import ReportToEvaluate, WeightVersion
from app.modules.priority.domain.urgency import UrgencyEvaluation
from app.modules.priority.domain.weights import DEFAULT_WEIGHTS, Weights
from app.modules.reports.domain.severity import Severity
from app.modules.reports.domain.status import ReportStatus
from app.modules.reports.domain.status_machine import StatusChange
from app.modules.roads.domain.entities import RoadMatch
from app.modules.roads.domain.road_class import RoadClass
from app.shared.domain.geo import GeoPoint
from app.shared.domain.geo_parameters import PROXIMITY_MAX_RADIUS_M, ROAD_MATCHING_RADIUS_M

ADMIN_ID = uuid.UUID("00000000-0000-0000-0000-00000000000a")
PASTO = GeoPoint(longitude=-77.2811, latitude=1.2136)
NOW = datetime(2026, 10, 16, tzinfo=UTC)
NEW_WEIGHTS = Weights(Decimal("0.40"), Decimal("0.40"), Decimal("0.20"))


def _report(status: ReportStatus = ReportStatus.REGISTERED) -> ReportToEvaluate:
    return ReportToEvaluate(
        report_id=uuid.uuid4(), severity=Severity.HIGH, location=PASTO, status=status
    )


class FakeWeights:
    def __init__(self, current: Weights | None = DEFAULT_WEIGHTS) -> None:
        self.versions: list[WeightVersion] = []
        if current is not None:
            self.add_current(current, created_by=None)

    def get_current(self) -> WeightVersion | None:
        return next((v for v in self.versions if v.is_current), None)

    def list_versions(self, limit: int, offset: int) -> Sequence[WeightVersion]:
        return list(reversed(self.versions))[offset : offset + limit]

    def add_current(self, weights: Weights, created_by: uuid.UUID | None) -> WeightVersion:
        self.versions = [
            WeightVersion(v.id, v.weights, v.created_by, v.created_at, is_current=False)
            for v in self.versions
        ]
        version = WeightVersion(len(self.versions) + 1, weights, created_by, NOW, is_current=True)
        self.versions.append(version)
        return version


class FakeReports:
    def __init__(self, *reports: ReportToEvaluate) -> None:
        self.reports = {report.report_id: report for report in reports}

    def get(self, report_id: uuid.UUID) -> ReportToEvaluate | None:
        return self.reports.get(report_id)

    def list_active(self) -> Sequence[ReportToEvaluate]:
        return [r for r in self.reports.values() if r.status is not ReportStatus.REPAIRED]


@dataclass
class FakeEvaluations:
    fail_on_call: int | None = None
    saved: list[tuple[uuid.UUID, UrgencyEvaluation, int]] = field(default_factory=list)

    def add(self, report_id: uuid.UUID, evaluation: UrgencyEvaluation, config_id: int) -> None:
        if self.fail_on_call == len(self.saved) + 1:
            raise RuntimeError("fallo al guardar")
        self.saved.append((report_id, evaluation, config_id))


@dataclass
class FakeStatuses:
    applied: list[tuple[uuid.UUID, StatusChange]] = field(default_factory=list)

    def apply(self, report_id: uuid.UUID, change: StatusChange) -> None:
        self.applied.append((report_id, change))


@dataclass
class FakeRoadMatcher:
    road: RoadMatch | None
    radii: list[float] = field(default_factory=list)

    def find_nearest(self, point: GeoPoint, max_distance_m: float) -> RoadMatch | None:
        self.radii.append(max_distance_m)
        return self.road


@dataclass
class FakeServiceLocator:
    service: NearestCriticalService | None
    radii: list[float] = field(default_factory=list)

    def find_nearest(self, point: GeoPoint, max_distance_m: float) -> NearestCriticalService | None:
        self.radii.append(max_distance_m)
        return self.service


@dataclass
class FakeTransaction:
    commits: int = 0
    rollbacks: int = 0

    def commit(self) -> None:
        self.commits += 1

    def rollback(self) -> None:
        self.rollbacks += 1


SECONDARY_ROAD = RoadMatch(
    road_id=7, name=None, road_class=RoadClass.SECONDARY, flow_factor=Decimal("7"), distance_m=5.0
)
HOSPITAL_180_M = NearestCriticalService(
    service_id=3, name=None, service_type=CriticalServiceType.HOSPITAL, distance_m=180.0
)


@dataclass
class Engine:
    reports: FakeReports
    weights: FakeWeights
    evaluations: FakeEvaluations
    statuses: FakeStatuses
    roads: FakeRoadMatcher
    services: FakeServiceLocator
    evaluator: ReportEvaluator


def _engine(
    *reports: ReportToEvaluate,
    weights: FakeWeights | None = None,
    evaluations: FakeEvaluations | None = None,
    road: RoadMatch | None = SECONDARY_ROAD,
    service: NearestCriticalService | None = HOSPITAL_180_M,
) -> Engine:
    fake_reports = FakeReports(*reports)
    fake_weights = weights or FakeWeights()
    fake_evaluations = evaluations or FakeEvaluations()
    statuses = FakeStatuses()
    roads = FakeRoadMatcher(road)
    services = FakeServiceLocator(service)
    evaluator = ReportEvaluator(
        reports=fake_reports,
        weights=fake_weights,
        evaluations=fake_evaluations,
        statuses=statuses,
        road_matcher=roads,
        service_locator=services,
    )
    return Engine(
        fake_reports, fake_weights, fake_evaluations, statuses, roads, services, evaluator
    )


def test_evaluate_saves_the_evaluation_with_the_current_version() -> None:
    report = _report()
    engine = _engine(report)

    result = engine.evaluator.evaluate(report.report_id)

    assert result.urgency_score == Decimal("8.70")  # Av. Los Estudiantes
    assert engine.evaluations.saved == [(report.report_id, result, 1)]


def test_evaluate_uses_the_named_geographic_radii() -> None:
    report = _report()
    engine = _engine(report)

    engine.evaluator.evaluate(report.report_id)

    assert engine.roads.radii == [ROAD_MATCHING_RADIUS_M]
    assert engine.services.radii == [PROXIMITY_MAX_RADIUS_M]


def test_registered_report_becomes_evaluated_by_the_system() -> None:
    report = _report(ReportStatus.REGISTERED)
    engine = _engine(report)

    engine.evaluator.evaluate(report.report_id)

    assert engine.statuses.applied == [
        (
            report.report_id,
            StatusChange(
                previous=ReportStatus.REGISTERED,
                new=ReportStatus.EVALUATED,
                changed_by=None,
                note=None,
            ),
        )
    ]


@pytest.mark.parametrize("status", [ReportStatus.EVALUATED, ReportStatus.PRIORITIZED])
def test_reevaluation_keeps_the_status(status: ReportStatus) -> None:
    report = _report(status)
    engine = _engine(report)

    engine.evaluator.evaluate(report.report_id)

    assert engine.statuses.applied == []


def test_report_without_road_is_evaluated_with_flow_two() -> None:
    report = _report()
    engine = _engine(report, road=None, service=None)

    result = engine.evaluator.evaluate(report.report_id)

    assert result.needs_road_review is True
    assert result.flow_score == Decimal("2")


def test_evaluate_unknown_report_fails() -> None:
    engine = _engine()

    with pytest.raises(ReportNotFoundError):
        engine.evaluator.evaluate(uuid.uuid4())


def test_evaluate_without_current_weights_fails() -> None:
    report = _report()
    engine = _engine(report, weights=FakeWeights(current=None))

    with pytest.raises(WeightsNotConfiguredError):
        engine.evaluator.evaluate(report.report_id)
    assert engine.evaluations.saved == []


def _update_weights(engine: Engine, transaction: FakeTransaction) -> UpdateWeights:
    return UpdateWeights(
        weights=engine.weights,
        reports=engine.reports,
        evaluator=engine.evaluator,
        transaction=transaction,
    )


def test_update_weights_creates_a_version_and_recalculates_active_reports() -> None:
    active = [_report(ReportStatus.EVALUATED), _report(ReportStatus.PRIORITIZED)]
    repaired = _report(ReportStatus.REPAIRED)
    engine = _engine(*active, repaired)
    transaction = FakeTransaction()

    result = _update_weights(engine, transaction).execute(NEW_WEIGHTS, ADMIN_ID)

    assert result.recalculated_reports == 2
    assert result.version.weights == NEW_WEIGHTS
    assert result.version.created_by == ADMIN_ID
    assert engine.weights.get_current() == result.version
    assert {saved[0] for saved in engine.evaluations.saved} == {r.report_id for r in active}
    # 0,4·10 + 0,4·7 + 0,2·8 = 8,40
    assert all(saved[1].urgency_score == Decimal("8.40") for saved in engine.evaluations.saved)
    assert all(saved[2] == result.version.id for saved in engine.evaluations.saved)
    assert transaction == FakeTransaction(commits=1, rollbacks=0)


def test_previous_versions_are_kept() -> None:
    engine = _engine()

    _update_weights(engine, FakeTransaction()).execute(NEW_WEIGHTS, ADMIN_ID)

    versions = engine.weights.list_versions(limit=10, offset=0)
    assert [v.weights for v in versions] == [NEW_WEIGHTS, DEFAULT_WEIGHTS]
    assert [v.is_current for v in versions] == [True, False]


def test_update_weights_rolls_back_if_a_recalculation_fails() -> None:
    engine = _engine(_report(), _report(), evaluations=FakeEvaluations(fail_on_call=2))
    transaction = FakeTransaction()

    with pytest.raises(RuntimeError, match="fallo al guardar"):
        _update_weights(engine, transaction).execute(NEW_WEIGHTS, ADMIN_ID)

    assert transaction == FakeTransaction(commits=0, rollbacks=1)


def test_update_weights_without_active_reports_still_creates_the_version() -> None:
    engine = _engine()
    transaction = FakeTransaction()

    result = _update_weights(engine, transaction).execute(NEW_WEIGHTS, ADMIN_ID)

    assert result.recalculated_reports == 0
    assert transaction.commits == 1
