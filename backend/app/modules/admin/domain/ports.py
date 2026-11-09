"""Puertos de lectura del panel administrativo."""

from collections.abc import Sequence
from typing import Protocol

from app.modules.admin.domain.ranking_view import HeatPoint, RankingPage, StatusSummary
from app.modules.reports.domain.status import ReportStatus
from app.shared.domain.geo import BoundingBox


class DashboardReader(Protocol):
    def ranking(self, statuses: frozenset[ReportStatus], limit: int, offset: int) -> RankingPage:
        """Reportes evaluados con esos estados, en el orden de ``ranking_key``."""
        ...

    def summary(self) -> StatusSummary: ...

    def heat_points(self, bbox: BoundingBox | None, limit: int) -> Sequence[HeatPoint]:
        """Reportes activos evaluados, opcionalmente dentro del rectángulo."""
        ...
