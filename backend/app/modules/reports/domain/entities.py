import uuid
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from app.modules.reports.domain.address import display_address
from app.modules.reports.domain.severity import Severity
from app.modules.reports.domain.status import ReportStatus
from app.shared.domain.geo import GeoPoint


@dataclass(frozen=True, slots=True)
class ReportDetails:
    """Reporte tal como lo ve su autor: con la ubicación exacta (propuesta 40)."""

    id: uuid.UUID
    user_id: uuid.UUID
    location: GeoPoint
    severity: Severity
    description: str | None
    status: ReportStatus
    # None mientras el motor no lo haya evaluado.
    priority_score: Decimal | None
    road_id: int | None
    road_name: str | None
    created_at: datetime

    @property
    def needs_road_review(self) -> bool:
        """Evaluado sin vía OSM a 30 m: marca «Revisar vía» (guía 2.2)."""
        return self.priority_score is not None and self.road_id is None

    @property
    def address(self) -> str:
        return display_address(has_road=self.road_id is not None, road_name=self.road_name)
