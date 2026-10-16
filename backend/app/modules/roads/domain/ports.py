from collections.abc import Sequence
from typing import Protocol

from app.modules.roads.domain.entities import OsmRoad, RoadMatch
from app.shared.domain.geo import GeoPoint


class RoadRepository(Protocol):
    def upsert_many(self, roads: Sequence[OsmRoad]) -> int:
        """Inserta o actualiza por ``osm_id``; devuelve cuántas vías se guardaron."""
        ...


class RoadMatcher(Protocol):
    def find_nearest(self, point: GeoPoint, max_distance_m: float) -> RoadMatch | None:
        """Vía más cercana a ``point`` a ``max_distance_m`` o menos; ``None`` si no hay."""
        ...
