from dataclasses import dataclass
from decimal import Decimal

from app.modules.roads.domain.road_class import RoadClass
from app.shared.domain.geo import GeoPoint, InvalidGeometryError

_MIN_LINE_POINTS = 2


@dataclass(frozen=True, slots=True)
class OsmRoad:
    """Vía obtenida de OpenStreetMap, ya clasificada, lista para guardarse."""

    osm_id: int
    name: str | None
    highway_tag: str
    road_class: RoadClass
    flow_factor: Decimal
    points: tuple[GeoPoint, ...]

    def __post_init__(self) -> None:
        if len(self.points) < _MIN_LINE_POINTS:
            raise InvalidGeometryError(f"La vía {self.osm_id} necesita al menos dos puntos")
