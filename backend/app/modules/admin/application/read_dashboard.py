"""Caso de uso: lectura del tablero de priorización (HU-08)."""

from collections.abc import Sequence
from typing import Final

from app.modules.admin.domain.ports import DashboardReader
from app.modules.admin.domain.ranking_view import (
    ACTIVE_STATUSES,
    MAX_PAGE_SIZE,
    HeatPoint,
    RankingPage,
    StatusSummary,
)
from app.modules.reports.domain.status import ReportStatus
from app.shared.domain.geo import BoundingBox

# Tope de puntos del mapa de calor: protege la respuesta si la base crece (guía 11).
HEATMAP_MAX_POINTS: Final = 5000


class ReadDashboard:
    def __init__(self, reader: DashboardReader) -> None:
        self._reader = reader

    def ranking(
        self, statuses: frozenset[ReportStatus] | None, limit: int, offset: int
    ) -> RankingPage:
        """Sin filtro (``None`` o vacío) se listan los reportes activos (decisión 13)."""
        if not 1 <= limit <= MAX_PAGE_SIZE:
            raise ValueError(f"limit debe estar entre 1 y {MAX_PAGE_SIZE}")
        if offset < 0:
            raise ValueError("offset no puede ser negativo")
        return self._reader.ranking(statuses or ACTIVE_STATUSES, limit, offset)

    def summary(self) -> StatusSummary:
        return self._reader.summary()

    def heat_points(
        self, bbox: BoundingBox | None, limit: int = HEATMAP_MAX_POINTS
    ) -> Sequence[HeatPoint]:
        return self._reader.heat_points(bbox, min(limit, HEATMAP_MAX_POINTS))
