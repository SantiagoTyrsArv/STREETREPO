"""Armado de los casos de uso del panel administrativo para cada petición."""

from typing import Annotated

from fastapi import Depends

from app.core.dependencies import SessionDep
from app.modules.admin.application.change_report_status import ChangeReportStatus
from app.modules.admin.application.get_admin_report import GetAdminReport
from app.modules.admin.application.manage_weights import ManageWeights
from app.modules.admin.application.read_dashboard import ReadDashboard
from app.modules.admin.infrastructure.dashboard_reader import SqlDashboardReader
from app.modules.admin.infrastructure.report_detail_reader import SqlAdminReportReader
from app.modules.admin.infrastructure.weights_reader import SqlWeightVersionsReader
from app.modules.priority.application.update_weights import UpdateWeights
from app.modules.priority.infrastructure.reports_reader import SqlReportsToEvaluate
from app.modules.priority.infrastructure.weights_repository import (
    SqlWeightVersionRepository,
)
from app.modules.priority.presentation.dependencies import build_report_evaluator
from app.modules.reports.infrastructure.status_history import (
    SqlReportStatusLock,
    SqlStatusHistoryRecorder,
)


def get_read_dashboard(session: SessionDep) -> ReadDashboard:
    return ReadDashboard(SqlDashboardReader(session))


ReadDashboardDep = Annotated[ReadDashboard, Depends(get_read_dashboard)]


def get_admin_report(session: SessionDep) -> GetAdminReport:
    return GetAdminReport(SqlAdminReportReader(session))


GetAdminReportDep = Annotated[GetAdminReport, Depends(get_admin_report)]


def get_change_report_status(session: SessionDep) -> ChangeReportStatus:
    return ChangeReportStatus(
        SqlReportStatusLock(session), SqlStatusHistoryRecorder(session), transaction=session
    )


ChangeReportStatusDep = Annotated[ChangeReportStatus, Depends(get_change_report_status)]


def get_manage_weights(session: SessionDep) -> ManageWeights:
    update = UpdateWeights(
        weights=SqlWeightVersionRepository(session),
        reports=SqlReportsToEvaluate(session),
        evaluator=build_report_evaluator(session),
        transaction=session,
    )
    return ManageWeights(SqlWeightVersionsReader(session), update)


ManageWeightsDep = Annotated[ManageWeights, Depends(get_manage_weights)]
