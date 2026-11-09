"""Armado de los casos de uso de reportes para cada petición."""

from datetime import timedelta
from typing import Annotated

from fastapi import Depends, Request

from app.core.dependencies import SessionDep, SettingsDep
from app.core.rate_limiting import RateLimiterDep, limit_per_client_ip
from app.modules.priority.presentation.dependencies import build_report_evaluator
from app.modules.reports.application.create_report import CreateReport, CreateReportPolicy
from app.modules.reports.application.find_nearby import (
    FindPossibleDuplicates,
    NearbyPolicy,
)
from app.modules.reports.application.get_photo import GetReportPhoto
from app.modules.reports.application.get_report import GetReport
from app.modules.reports.application.list_my_reports import ListMyReports
from app.modules.reports.infrastructure.evidence import SqlReportPhotoLookup
from app.modules.reports.infrastructure.local_photo_storage import LocalPhotoStorage
from app.modules.reports.infrastructure.my_reports import SqlMyReportsReader
from app.modules.reports.infrastructure.nearby import (
    PostgisNearbyReportFinder,
    PostgresReportCreationLock,
)
from app.modules.reports.infrastructure.pillow_photos import PillowPhotoProcessor
from app.modules.reports.infrastructure.report_view import SqlReportViewReader
from app.modules.reports.infrastructure.repository import SqlReportRepository
from app.modules.reports.infrastructure.status_history import SqlStatusHistoryRecorder
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
    return CreateReport(
        reports=SqlReportRepository(session),
        nearby=PostgisNearbyReportFinder(session),
        creation_lock=PostgresReportCreationLock(session),
        statuses=SqlStatusHistoryRecorder(session),
        evaluator=build_report_evaluator(session),
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


def get_find_possible_duplicates(
    session: SessionDep, settings: SettingsDep, limiter: RateLimiterDep
) -> FindPossibleDuplicates:
    return FindPossibleDuplicates(
        PostgisNearbyReportFinder(session),
        limiter,
        NearbyPolicy(
            service_area=settings.report_area,
            # Mismo valor que el de crear reportes (propuesta 43), con cuenta aparte.
            limit_per_user=RateLimit(
                max_requests=settings.reports_per_user_per_hour, window=_ONE_HOUR
            ),
        ),
        SystemClock(),
    )


FindPossibleDuplicatesDep = Annotated[FindPossibleDuplicates, Depends(get_find_possible_duplicates)]


def get_report_photo(session: SessionDep, settings: SettingsDep) -> GetReportPhoto:
    return GetReportPhoto(
        SqlReportPhotoLookup(session), LocalPhotoStorage(settings.photo_storage_dir)
    )


GetReportPhotoDep = Annotated[GetReportPhoto, Depends(get_report_photo)]


def get_list_my_reports(session: SessionDep) -> ListMyReports:
    return ListMyReports(SqlMyReportsReader(session))


ListMyReportsDep = Annotated[ListMyReports, Depends(get_list_my_reports)]


def get_get_report(session: SessionDep) -> GetReport:
    return GetReport(SqlReportViewReader(session))


GetReportDep = Annotated[GetReport, Depends(get_get_report)]
