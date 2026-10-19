"""Caso de uso: reportes activos a 25 m para la pantalla «Posible duplicado» (HU-15)."""

import uuid
from collections.abc import Sequence
from dataclasses import dataclass

from app.modules.reports.domain.duplicates import MAX_DUPLICATE_CANDIDATES, DuplicateCandidate
from app.modules.reports.domain.new_report import ensure_in_service_area
from app.modules.reports.domain.ports import NearbyReportFinder
from app.shared.application.clock import Clock
from app.shared.application.rate_limit import RateLimit, RateLimiter
from app.shared.domain.geo import BoundingBox, GeoPoint
from app.shared.domain.geo_parameters import DEDUPLICATION_RADIUS_M


@dataclass(frozen=True, slots=True)
class NearbyPolicy:
    service_area: BoundingBox
    limit_per_user: RateLimit


class FindPossibleDuplicates:
    """Consulta acotada (propuesta 43): solo dentro del área de servicio y con cupo por
    usuario, para que no sirva para barrer la ciudad sondeando el borde de los 25 m."""

    def __init__(
        self,
        nearby: NearbyReportFinder,
        rate_limiter: RateLimiter,
        policy: NearbyPolicy,
        clock: Clock,
    ) -> None:
        self._nearby = nearby
        self._rate_limiter = rate_limiter
        self._policy = policy
        self._clock = clock

    def execute(self, user_id: uuid.UUID, location: GeoPoint) -> Sequence[DuplicateCandidate]:
        ensure_in_service_area(location, self._policy.service_area)
        # Cupo propio, no el de crear reportes: consultar antes de enviar no debe
        # gastar el cupo del envío.
        self._rate_limiter.hit(
            f"nearby:user:{user_id}", self._policy.limit_per_user, self._clock.now()
        )
        return self._nearby.find_active_within(
            location, DEDUPLICATION_RADIUS_M, MAX_DUPLICATE_CANDIDATES
        )
