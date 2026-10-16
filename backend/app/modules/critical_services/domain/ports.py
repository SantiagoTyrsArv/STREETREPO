from collections.abc import Sequence
from typing import Protocol

from app.modules.critical_services.domain.entities import OsmCriticalService


class CriticalServiceRepository(Protocol):
    def upsert_many(self, services: Sequence[OsmCriticalService]) -> int:
        """Inserta o actualiza por ``osm_id``; devuelve cuántos servicios se guardaron."""
        ...
