"""Armado de los casos de uso de reportes para cada petición."""

from datetime import timedelta
from typing import Annotated

from fastapi import Depends, Request

from app.core.dependencies import SessionDep, SettingsDep
from app.core.rate_limiting import RateLimiterDep, limit_per_client_ip
from app.modules.critical_services.infrastructure.locator import PostgisCriticalServiceLocator
from app.modules.priority.application.evaluate_report import ReportEvaluator
from app.modules.priority.infrastructure.evaluation_repository import SqlEvaluationRepository
from app.modules.priority.infrastructure.reports_reader import SqlReportsToEvaluate
from app.modules.priority.infrastructure.weights_repository import SqlWeightVersionRepository
from app.modules.reports.application.create_report import CreateReport, CreateReportPolicy
from app.modules.reports.application.find_nearby import FindPossibleDuplicates
from app.modules.reports.infrastructure.local_photo_storage import LocalPhotoStorage
from app.modules.reports.infrastructure.nearby import (
    PostgisNearbyReportFinder,
    PostgresReportCreationLock,
)
from app.modules.reports.infrastructure.pillow_photos import PillowPhotoProcessor
from app.modules.reports.infrastructure.repository import SqlReportRepository
from app.modules.reports.infrastructure.status_history import SqlStatusHistoryRecorder
from app.modules.roads.infrastructure.matcher import PostgisRoadMatcher
from app.shared.application.clock import SystemClock
from app.shared.application.rate_limit import RateLimit

_ONE_HOUR = timedelta(hours=1)


def limit_reports_per_ip(request: Request, limiter: RateLimiterDep, settings: SettingsDep) -> None:
    """Cupo por IP (propuesta 38), holgado porque muchas personas comparten IP (NAT)."""
    limit = RateLimit(max_requests=settings.reports_per_ip_per_hour, window=_ONE_HOUR)
    limit_per_client_ip("reports", limit)(request, limiter)


def get_create_report(
    session: SessionDep, settings: SettingsDep, limiter: RateLimiterDep
) -> CreateReport:
    statuses = SqlStatusHistoryRecorder(session)
    evaluator = ReportEvaluator(
        reports=SqlReportsToEvaluate(session),
        weights=SqlWeightVersionRepository(session),
        evaluations=SqlEvaluationRepository(session),
        statuses=statuses,
        road_matcher=PostgisRoadMatcher(session),
        service_locator=PostgisCriticalServiceLocator(session),
    )
    return CreateReport(
        reports=SqlReportRepository(session),
        nearby=PostgisNearbyReportFinder(session),
        creation_lock=PostgresReportCreationLock(session),
        statuses=statuses,
        evaluator=evaluator,
        photo_processor=PillowPhotoProcessor(),
        photo_storage=LocalPhotoStorage(settings.photo_storage_dir),
        rate_limiter=limiter,
        policy=CreateReportPolicy(
            service_area=settings.report_area,
            limit_per_user=RateLimit(
                max_requests=settings.reports_per_user_per_hour, window=_ONE_HOUR
            ),
        ),
        clock=SystemClock(),
        transaction=session,
    )


CreateReportDep = Annotated[CreateReport, Depends(get_create_report)]


def get_find_possible_duplicates(session: SessionDep) -> FindPossibleDuplicates:
    return FindPossibleDuplicates(PostgisNearbyReportFinder(session))


FindPossibleDuplicatesDep = Annotated[FindPossibleDuplicates, Depends(get_find_possible_duplicates)]
