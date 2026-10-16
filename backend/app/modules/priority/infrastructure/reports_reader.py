import uuid
from collections.abc import Sequence
from typing import Any

from sqlalchemy import Row, Select, func, select
from sqlalchemy.orm import Session

from app.modules.priority.domain.entities import ReportToEvaluate
from app.modules.reports.domain.severity import Severity
from app.modules.reports.domain.status import ReportStatus
from app.modules.reports.infrastructure.models import ReportModel
from app.shared.domain.geo import GeoPoint


def _select_reports() -> Select[Any]:
    return select(
        ReportModel.id,
        ReportModel.severity,
        ReportModel.status,
        func.ST_X(ReportModel.location).label("lon"),
        func.ST_Y(ReportModel.location).label("lat"),
    )


def _to_entity(row: Row[Any]) -> ReportToEvaluate:
    return ReportToEvaluate(
        report_id=row.id,
        severity=Severity(row.severity),
        location=GeoPoint(longitude=row.lon, latitude=row.lat),
        status=ReportStatus(row.status),
    )


class SqlReportsToEvaluate:
    """Implementa ``ReportsToEvaluate``: lee de ``reporte`` solo lo que usa el motor."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, report_id: uuid.UUID) -> ReportToEvaluate | None:
        row = self._session.execute(
            _select_reports().where(ReportModel.id == report_id)
        ).one_or_none()
        return None if row is None else _to_entity(row)

    def list_active(self) -> Sequence[ReportToEvaluate]:
        rows = self._session.execute(
            _select_reports()
            .where(ReportModel.status != ReportStatus.REPAIRED)
            .order_by(ReportModel.created_at, ReportModel.id)
        ).all()
        return [_to_entity(row) for row in rows]
