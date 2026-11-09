"""Armado de los casos de uso del panel administrativo para cada petición."""

from typing import Annotated

from fastapi import Depends

from app.core.dependencies import SessionDep
from app.modules.admin.application.get_admin_report import GetAdminReport
from app.modules.admin.application.read_dashboard import ReadDashboard
from app.modules.admin.infrastructure.dashboard_reader import SqlDashboardReader
from app.modules.admin.infrastructure.report_detail_reader import SqlAdminReportReader


def get_read_dashboard(session: SessionDep) -> ReadDashboard:
    return ReadDashboard(SqlDashboardReader(session))


ReadDashboardDep = Annotated[ReadDashboard, Depends(get_read_dashboard)]


def get_admin_report(session: SessionDep) -> GetAdminReport:
    return GetAdminReport(SqlAdminReportReader(session))


GetAdminReportDep = Annotated[GetAdminReport, Depends(get_admin_report)]
