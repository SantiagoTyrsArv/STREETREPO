"""Conversión de objetos de valor geográficos a WKT.

El WKT se envía como parámetro enlazado a ``ST_GeomFromText``; nunca se
concatena en el SQL (guía 5).
"""

from collections.abc import Iterable

from app.shared.domain.geo import GeoPoint


def _coordinates(point: GeoPoint) -> str:
    return f"{point.longitude!r} {point.latitude!r}"


def point_wkt(point: GeoPoint) -> str:
    return f"POINT({_coordinates(point)})"


def linestring_wkt(points: Iterable[GeoPoint]) -> str:
    return f"LINESTRING({', '.join(_coordinates(point) for point in points)})"
