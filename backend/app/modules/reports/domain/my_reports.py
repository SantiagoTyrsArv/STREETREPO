"""«Mis reportes»: los que el ciudadano creó y los que confirmó (decisión 49).

Los propios se ven completos; los confirmados, con la vista pública de un reporte ajeno:
sin autor, descripción ni ubicación exacta (guía 7.2, propuesta 43).
"""

import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Final

from app.modules.reports.domain.address import display_address
from app.modules.reports.domain.entities import ReportDetails
from app.modules.reports.domain.severity import Severity
from app.modules.reports.domain.status import ReportStatus
from app.shared.domain.geo import GeoPoint

DEFAULT_PAGE_SIZE: Final = 20
MAX_PAGE_SIZE: Final = 50


@dataclass(frozen=True, slots=True)
class PublicReportView:
    """Reporte ajeno: ``location`` es la ubicación pública (``public_location``)."""

    id: uuid.UUID
    location: GeoPoint
    status: ReportStatus
    severity: Severity
    confirmations: int
    road_id: int | None
    road_name: str | None
    created_at: datetime

    @property
    def address(self) -> str:
        return display_address(has_road=self.road_id is not None, road_name=self.road_name)


@dataclass(frozen=True, slots=True)
class OwnReport:
    details: ReportDetails
    confirmations: int


@dataclass(frozen=True, slots=True)
class ConfirmedReport:
    public: PublicReportView
    confirmed_at: datetime


@dataclass(frozen=True, slots=True)
class MyReportsPage:
    """Del más reciente al más antiguo según la fecha de creación o de confirmación."""

    items: Sequence[OwnReport | ConfirmedReport]
    total: int
    limit: int
    offset: int
