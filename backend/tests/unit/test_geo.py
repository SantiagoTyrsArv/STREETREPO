import pytest

from app.shared.domain.geo import BoundingBox, GeoPoint, InvalidGeometryError
from app.shared.infrastructure.wkt import linestring_wkt, point_wkt


def test_point_accepts_valid_coordinates() -> None:
    point = GeoPoint(longitude=-77.2811, latitude=1.2136)

    assert (point.longitude, point.latitude) == (-77.2811, 1.2136)


@pytest.mark.parametrize(("lon", "lat"), [(-181.0, 0.0), (181.0, 0.0), (0.0, -91.0), (0.0, 91.0)])
def test_point_rejects_out_of_range_coordinates(lon: float, lat: float) -> None:
    with pytest.raises(InvalidGeometryError):
        GeoPoint(longitude=lon, latitude=lat)


def test_bbox_parses_overpass_order() -> None:
    area = BoundingBox.parse(" 1.16, -77.33 ,1.25,-77.23 ")

    assert area == BoundingBox(south=1.16, west=-77.33, north=1.25, east=-77.23)


@pytest.mark.parametrize(
    "raw",
    [
        "1.16,-77.33,1.25",  # faltan valores
        "1.16,-77.33,1.25,-77.23,0",  # sobran valores
        "a,b,c,d",  # no numéricos
        "1.25,-77.33,1.16,-77.23",  # sur > norte
        "1.16,-77.23,1.25,-77.33",  # oeste > este
        "1.16,-77.33,95,-77.23",  # latitud fuera de rango
    ],
)
def test_bbox_rejects_invalid_input(raw: str) -> None:
    with pytest.raises(InvalidGeometryError):
        BoundingBox.parse(raw)


def test_wkt_uses_longitude_first() -> None:
    a = GeoPoint(longitude=-77.28, latitude=1.21)
    b = GeoPoint(longitude=-77.27, latitude=1.22)

    assert point_wkt(a) == "POINT(-77.28 1.21)"
    assert linestring_wkt([a, b]) == "LINESTRING(-77.28 1.21, -77.27 1.22)"
