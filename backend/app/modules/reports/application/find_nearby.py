"""Caso de uso: reportes activos a 25 m para la pantalla «Posible duplicado» (HU-15)."""

from collections.abc import Sequence

from app.modules.reports.domain.duplicates import MAX_DUPLICATE_CANDIDATES, DuplicateCandidate
from app.modules.reports.domain.ports import NearbyReportFinder
from app.shared.domain.geo import GeoPoint
from app.shared.domain.geo_parameters import DEDUPLICATION_RADIUS_M


class FindPossibleDuplicates:
    def __init__(self, nearby: NearbyReportFinder) -> None:
        self._nearby = nearby

    def execute(self, location: GeoPoint) -> Sequence[DuplicateCandidate]:
        return self._nearby.find_active_within(
            location, DEDUPLICATION_RADIUS_M, MAX_DUPLICATE_CANDIDATES
        )
