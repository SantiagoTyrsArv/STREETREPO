"""Armado del motor de priorización para los casos de uso que lo necesitan."""

from sqlalchemy.orm import Session

from app.modules.critical_services.infrastructure.locator import PostgisCriticalServiceLocator
from app.modules.priority.application.evaluate_report import ReportEvaluator
from app.modules.priority.infrastructure.evaluation_repository import SqlEvaluationRepository
from app.modules.priority.infrastructure.reports_reader import SqlReportsToEvaluate
from app.modules.priority.infrastructure.weights_repository import SqlWeightVersionRepository
from app.modules.reports.infrastructure.status_history import SqlStatusHistoryRecorder
from app.modules.roads.infrastructure.matcher import PostgisRoadMatcher


def build_report_evaluator(session: Session) -> ReportEvaluator:
    """Motor con map-matching y proximidad locales sobre PostGIS (guía 3.1)."""
    return ReportEvaluator(
        reports=SqlReportsToEvaluate(session),
        weights=SqlWeightVersionRepository(session),
        evaluations=SqlEvaluationRepository(session),
        statuses=SqlStatusHistoryRecorder(session),
        road_matcher=PostgisRoadMatcher(session),
        service_locator=PostgisCriticalServiceLocator(session),
    )
