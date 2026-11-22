"""Zonas de validación (objetivo 4): lectura y validación del GeoJSON que las define."""

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from app.modules.validation.domain.parameters import MAX_ZONES


class Concentration(StrEnum):
    """Concentración de reportes de una zona de validación."""

    HIGH = "alta"
    LOW = "baja"


class InvalidZonesError(ValueError):
    """El archivo de zonas no cumple las reglas del estudio; el mensaje va en español."""


@dataclass(frozen=True, slots=True)
class ZoneDefinition:
    name: str
    concentration: Concentration
    polygon_geojson: dict[str, Any]


def _read_zone(position: int, feature: object) -> ZoneDefinition:
    if not isinstance(feature, Mapping):
        raise InvalidZonesError(f"La zona {position} no es una Feature de GeoJSON.")
    properties = feature.get("properties")
    properties = properties if isinstance(properties, Mapping) else {}
    raw_name = properties.get("name")
    name = raw_name.strip() if isinstance(raw_name, str) else ""
    if not name:
        raise InvalidZonesError(f"La zona {position} no tiene la propiedad «name» (nombre).")

    raw_concentration = properties.get("concentration")
    try:
        concentration = Concentration(str(raw_concentration))
    except ValueError:
        raise InvalidZonesError(
            f"La zona «{name}» debe declarar «concentration» como «alta» o «baja»."
        ) from None

    geometry = feature.get("geometry")
    if (
        not isinstance(geometry, Mapping)
        or geometry.get("type") != "Polygon"
        or not isinstance(geometry.get("coordinates"), list)
    ):
        raise InvalidZonesError(
            f"La zona «{name}» debe ser un Polygon (no se admite MultiPolygon ni otra geometría)."
        )
    return ZoneDefinition(name, concentration, dict(geometry))


def parse_zones(geojson: Mapping[str, Any]) -> list[ZoneDefinition]:
    """Convierte una FeatureCollection de polígonos en definiciones de zona.

    La validez geométrica y el solapamiento se comprueban en la base de datos (PostGIS).
    """
    if not isinstance(geojson, Mapping) or geojson.get("type") != "FeatureCollection":
        raise InvalidZonesError("El archivo debe ser un GeoJSON de tipo FeatureCollection.")
    features = geojson.get("features")
    if not isinstance(features, list) or not features:
        raise InvalidZonesError("El archivo debe traer al menos una zona.")
    if len(features) > MAX_ZONES:
        raise InvalidZonesError(f"El estudio admite como máximo {MAX_ZONES} zonas.")

    zones = [_read_zone(position, feature) for position, feature in enumerate(features, start=1)]
    names = [zone.name for zone in zones]
    for name in names:
        if names.count(name) > 1:
            raise InvalidZonesError(f"El nombre de zona «{name}» está repetido.")
    return zones
