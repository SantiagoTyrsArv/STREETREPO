"""Caso de uso: reportes del área visible para el mapa de la app (guía 6.2)."""

import uuid

from app.modules.reports.domain.ports import PublicReportsReader
from app.modules.reports.domain.public_map import MAX_MAP_REPORTS, MapReportsPage
from app.modules.reports.domain.status import ReportStatus
from app.shared.application.clock import Clock
from app.shared.application.rate_limit import RateLimit, RateLimiter
from app.shared.domain.geo import BoundingBox


class ListReportsInArea:
    """Consulta acotada: tope de reportes por respuesta y cupo por usuario, para que el
    mapa no sirva para descargar todos los reportes de la ciudad."""

    def __init__(
        self,
        reader: PublicReportsReader,
        rate_limiter: RateLimiter,
        limit_per_user: RateLimit,
        clock: Clock,
    ) -> None:
        self._reader = reader
        self._rate_limiter = rate_limiter
        self._limit_per_user = limit_per_user
        self._clock = clock

    def execute(
        self,
        viewer_id: uuid.UUID,
        area: BoundingBox,
        status: ReportStatus | None,
        limit: int,
    ) -> MapReportsPage:
        if not 1 <= limit <= MAX_MAP_REPORTS:
            raise ValueError(f"limit debe estar entre 1 y {MAX_MAP_REPORTS}")
        self._rate_limiter.hit(f"map:user:{viewer_id}", self._limit_per_user, self._clock.now())
        # Se pide uno de más para saber si quedaron reportes fuera sin contar toda el área.
        found = self._reader.list_in_area(area, status, limit + 1, viewer_id)
        return MapReportsPage(items=found[:limit], limit=limit, truncated=len(found) > limit)
