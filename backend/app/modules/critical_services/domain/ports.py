from collections.abc import Sequence
from typing import Protocol

from app.modules.critical_services.domain.entities import (
    NearestCriticalService,
    OsmCriticalService,
)
from app.shared.domain.geo import GeoPoint


class CriticalServiceRepository(Protocol):
    def upsert_many(self, services: Sequence[OsmCriticalService]) -> int:
        """Inserta o actualiza por ``osm_id``; devuelve cuántos servicios se guardaron."""
        ...


class CriticalServiceLocator(Protocol):
    def find_nearest(self, point: GeoPoint, max_distance_m: float) -> NearestCriticalService | None:
        """Servicio crítico más cercano a ``max_distance_m`` o menos; ``None`` si no hay."""
        ...
