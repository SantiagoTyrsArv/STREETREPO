from collections.abc import Sequence
from typing import Protocol

from app.modules.roads.domain.entities import OsmRoad


class RoadRepository(Protocol):
    def upsert_many(self, roads: Sequence[OsmRoad]) -> int:
        """Inserta o actualiza por ``osm_id``; devuelve cuántas vías se guardaron."""
        ...
