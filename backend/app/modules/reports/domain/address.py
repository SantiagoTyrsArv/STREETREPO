"""Dirección que se muestra del reporte (propuesta 41).

En el MVP no se geocodifica con Nominatim: la dirección es el nombre de la vía
OSM asociada, ya cargada en PostGIS.
"""

from typing import Final

UNNAMED_ROAD: Final = "Vía sin nombre"
NO_ROAD: Final = "Sin vía asociada"


def display_address(*, has_road: bool, road_name: str | None) -> str:
    """Nombre de la vía, o un texto de reserva si la vía no tiene nombre o no hay vía."""
    if not has_road:
        return NO_ROAD
    name = (road_name or "").strip()
    return name or UNNAMED_ROAD
