"""Clasificación de vías OSM y factor de flujo vehicular F (guía 2.2, propuesta 7)."""

from decimal import Decimal
from types import MappingProxyType

from app.modules.roads.domain.road_class import RoadClass

# Correspondencia aprobada (propuesta 7) entre la etiqueta ``highway`` de OSM y la
# jerarquía vial del diagrama ER. Las etiquetas que no aparecen (footway, track,
# path, steps, motorway…) no se cargan.
HIGHWAY_TO_ROAD_CLASS: MappingProxyType[str, RoadClass] = MappingProxyType(
    {
        "trunk": RoadClass.PRIMARY,
        "trunk_link": RoadClass.PRIMARY,
        "primary": RoadClass.PRIMARY,
        "primary_link": RoadClass.PRIMARY,
        "secondary": RoadClass.SECONDARY,
        "tertiary": RoadClass.TERTIARY,
        "residential": RoadClass.RESIDENTIAL,
        "unclassified": RoadClass.RESIDENTIAL,
        "service": RoadClass.RESIDENTIAL,
        "living_street": RoadClass.RESIDENTIAL,
    }
)

# Normalización de F en escala 0-10 (guía 2.2): primary = 10, secondary = 7,
# tertiary = 5, residential / unclassified / service = 2.
FLOW_FACTOR_BY_ROAD_CLASS: MappingProxyType[RoadClass, Decimal] = MappingProxyType(
    {
        RoadClass.PRIMARY: Decimal("10"),
        RoadClass.SECONDARY: Decimal("7"),
        RoadClass.TERTIARY: Decimal("5"),
        RoadClass.RESIDENTIAL: Decimal("2"),
    }
)

SUPPORTED_HIGHWAY_TAGS: frozenset[str] = frozenset(HIGHWAY_TO_ROAD_CLASS)


def classify_highway(highway_tag: str) -> RoadClass | None:
    """Jerarquía vial para una etiqueta ``highway`` de OSM, o ``None`` si no se carga."""
    return HIGHWAY_TO_ROAD_CLASS.get(highway_tag.strip().lower())


def flow_factor(road_class: RoadClass) -> Decimal:
    """Factor de flujo F (0-10) de una vía según su jerarquía."""
    return FLOW_FACTOR_BY_ROAD_CLASS[road_class]
