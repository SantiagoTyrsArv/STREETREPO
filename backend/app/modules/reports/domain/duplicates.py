"""Posible duplicado (HU-15, guía 2.5, propuesta 36).

Al crear un reporte se buscan reportes activos a ``DEDUPLICATION_RADIUS_M``; si los
hay, se ofrecen para confirmarlos en lugar de crear otro. El ciudadano puede crearlo
de todos modos.
"""

import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Final

from app.modules.reports.domain.address import display_address
from app.modules.reports.domain.severity import Severity
from app.modules.reports.domain.status import ReportStatus
from app.shared.domain.geo import GeoPoint

# Suficiente para la pantalla «Posible duplicado»; a 25 m no debería haber más.
MAX_DUPLICATE_CANDIDATES: Final = 10


@dataclass(frozen=True, slots=True)
class DuplicateCandidate:
    """Reporte activo cercano, sin datos del autor ni su ubicación exacta (guía 7.2).

    ``location`` es la ubicación pública (redondeada, ``public_location``) y
    ``distance_m`` se mide desde ella, para que no revele la exacta (propuesta 43).
    """

    id: uuid.UUID
    location: GeoPoint
    distance_m: float
    status: ReportStatus
    severity: Severity
    confirmations: int
    road_id: int | None
    road_name: str | None
    created_at: datetime

    @property
    def address(self) -> str:
        return display_address(has_road=self.road_id is not None, road_name=self.road_name)


class PossibleDuplicateError(Exception):
    """Hay reportes activos a 25 m y el ciudadano no pidió crearlo de todos modos."""

    def __init__(self, candidates: Sequence[DuplicateCandidate]) -> None:
        super().__init__(f"{len(candidates)} reportes activos cercanos")
        self.candidates = tuple(candidates)
