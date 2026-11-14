"""Objetos de valor geográficos compartidos (WGS 84, grados decimales)."""

from dataclasses import dataclass

_MAX_LATITUDE = 90.0
_MAX_LONGITUDE = 180.0


class InvalidGeometryError(ValueError):
    """Coordenadas o geometrías fuera de rango."""


def _check_latitude(value: float) -> None:
    if not -_MAX_LATITUDE <= value <= _MAX_LATITUDE:
        raise InvalidGeometryError(f"Latitud fuera de rango: {value}")


def _check_longitude(value: float) -> None:
    if not -_MAX_LONGITUDE <= value <= _MAX_LONGITUDE:
        raise InvalidGeometryError(f"Longitud fuera de rango: {value}")


@dataclass(frozen=True, slots=True)
class GeoPoint:
    longitude: float
    latitude: float

    def __post_init__(self) -> None:
        _check_longitude(self.longitude)
        _check_latitude(self.latitude)


@dataclass(frozen=True, slots=True)
class BoundingBox:
    """Rectángulo en el orden de Overpass: sur, oeste, norte, este."""

    south: float
    west: float
    north: float
    east: float

    def __post_init__(self) -> None:
        for latitude in (self.south, self.north):
            _check_latitude(latitude)
        for longitude in (self.west, self.east):
            _check_longitude(longitude)
        if self.south >= self.north or self.west >= self.east:
            raise InvalidGeometryError("El área debe tener sur < norte y oeste < este")

    def contains(self, point: GeoPoint) -> bool:
        """El borde cuenta como dentro."""
        return (
            self.south <= point.latitude <= self.north and self.west <= point.longitude <= self.east
        )

    @classmethod
    def parse(cls, raw: str) -> "BoundingBox":
        """Lee ``"sur,oeste,norte,este"``."""
        south, west, north, east = cls._four_numbers(raw, "sur,oeste,norte,este")
        return cls(south, west, north, east)

    @classmethod
    def parse_min_max(cls, raw: str) -> "BoundingBox":
        """Lee ``"min_lon,min_lat,max_lon,max_lat"``, el orden de los mapas (``toBBoxString``
        de Leaflet) y del parámetro ``bbox`` de la API."""
        west, south, east, north = cls._four_numbers(raw, "min_lon,min_lat,max_lon,max_lat")
        return cls(south, west, north, east)

    @staticmethod
    def _four_numbers(raw: str, order: str) -> tuple[float, float, float, float]:
        parts = [part.strip() for part in raw.split(",")]
        if len(parts) != 4:  # noqa: PLR2004 - cuatro lados del rectángulo
            raise InvalidGeometryError(f"Se esperan cuatro valores: {order}")
        try:
            first, second, third, fourth = (float(part) for part in parts)
        except ValueError as exc:
            raise InvalidGeometryError("Los valores del área deben ser números") from exc
        return first, second, third, fourth
