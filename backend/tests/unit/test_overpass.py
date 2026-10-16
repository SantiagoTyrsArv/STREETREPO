"""Adaptador de Overpass: consultas, traducción al dominio y manejo de errores."""

import json
from decimal import Decimal
from typing import Any

import httpx
import pytest

from app.modules.admin.application.import_osm_data import OsmSourceError
from app.modules.admin.infrastructure.overpass import (
    MAX_ATTEMPTS,
    MAX_NAME_LENGTH,
    OverpassClient,
    build_critical_services_query,
    build_roads_query,
    create_overpass_client,
    parse_critical_service,
    parse_road,
    retry_delay,
)
from app.modules.critical_services.domain.service_type import CriticalServiceType
from app.modules.roads.domain.road_class import RoadClass
from app.shared.domain.geo import BoundingBox, GeoPoint

AREA = BoundingBox(south=1.16, west=-77.33, north=1.25, east=-77.23)
URL = "https://overpass.test/api/interpreter"

# Datos de prueba con la forma de la respuesta de Overpass (out tags geom / out tags center).
ROAD = {
    "type": "way",
    "id": 101,
    "tags": {"highway": "trunk", "name": "Avenida Panamericana"},
    "geometry": [{"lat": 1.2100, "lon": -77.2800}, {"lat": 1.2110, "lon": -77.2790}],
}
SCHOOL_NODE = {
    "type": "node",
    "id": 501,
    "lat": 1.2140,
    "lon": -77.2810,
    "tags": {"amenity": "school", "name": "Escuela de prueba"},
}
HOSPITAL_WAY = {
    "type": "way",
    "id": 777,
    "center": {"lat": 1.2200, "lon": -77.2750},
    "tags": {"amenity": "hospital", "name": "Hospital de prueba"},
}


def test_roads_query_filters_supported_tags_and_area() -> None:
    query = build_roads_query(AREA)

    assert "[out:json]" in query
    assert "(1.16,-77.33,1.25,-77.23)" in query
    assert "trunk" in query
    assert "footway" not in query
    assert query.endswith("out tags geom;")


def test_services_query_asks_nodes_and_ways_with_center() -> None:
    query = build_critical_services_query(AREA)

    assert 'node["amenity"~"^(hospital|school)$"]' in query
    assert 'way["amenity"~"^(hospital|school)$"]' in query
    assert query.endswith("out tags center;")


def test_parse_road_classifies_and_keeps_geometry() -> None:
    road = parse_road(ROAD)

    assert road is not None
    assert road.osm_id == 101
    assert road.road_class is RoadClass.PRIMARY
    assert road.flow_factor == Decimal("10")
    assert road.highway_tag == "trunk"
    assert road.points == (
        GeoPoint(longitude=-77.28, latitude=1.21),
        GeoPoint(longitude=-77.279, latitude=1.211),
    )


def test_parse_road_without_name_stores_none() -> None:
    road = parse_road({**ROAD, "tags": {"highway": "residential"}})

    assert road is not None
    assert road.name is None


def test_parse_road_truncates_long_names() -> None:
    road = parse_road({**ROAD, "tags": {"highway": "primary", "name": "x" * 300}})

    assert road is not None
    assert road.name is not None
    assert len(road.name) == MAX_NAME_LENGTH


@pytest.mark.parametrize(
    "element",
    [
        {**ROAD, "tags": {"highway": "footway"}},  # etiqueta no soportada
        {**ROAD, "geometry": [{"lat": 1.21, "lon": -77.28}]},  # un solo punto
        {**ROAD, "geometry": [{"lat": 1.21}, {"lat": 1.22}]},  # sin longitud
        {**ROAD, "geometry": [{"lat": 99, "lon": -77.28}, {"lat": 1.2, "lon": -77.2}]},
    ],
)
def test_parse_road_discards_unusable_elements(element: dict[str, Any]) -> None:
    assert parse_road(element) is None


def test_parse_service_node_uses_its_coordinates() -> None:
    service = parse_critical_service(SCHOOL_NODE)

    assert service is not None
    assert service.osm_id == 501
    assert service.service_type is CriticalServiceType.SCHOOL
    assert service.location == GeoPoint(longitude=-77.281, latitude=1.214)


def test_parse_service_way_uses_center_and_negative_id() -> None:
    # Nodos y vías de OSM pueden compartir número: la vía se guarda con id negativo.
    service = parse_critical_service(HOSPITAL_WAY)

    assert service is not None
    assert service.osm_id == -777
    assert service.service_type is CriticalServiceType.HOSPITAL
    assert service.location == GeoPoint(longitude=-77.275, latitude=1.22)


@pytest.mark.parametrize(
    "element",
    [
        {**SCHOOL_NODE, "tags": {"amenity": "pharmacy"}},
        {"type": "way", "id": 1, "tags": {"amenity": "school"}},  # sin center
    ],
)
def test_parse_service_discards_unusable_elements(element: dict[str, Any]) -> None:
    assert parse_critical_service(element) is None


def _client(handler: Any) -> OverpassClient:
    transport = httpx.MockTransport(handler)
    return OverpassClient(httpx.Client(transport=transport), URL, sleep=lambda _: None)


def test_client_posts_query_and_returns_domain_objects() -> None:
    received: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        received.append(request)
        return httpx.Response(200, json={"elements": [ROAD, {**ROAD, "id": 9, "tags": {}}]})

    roads = _client(handler).fetch_roads(AREA)

    assert [road.osm_id for road in roads] == [101]
    assert received[0].method == "POST"
    assert str(received[0].url) == URL
    assert b"data=" in received[0].content


def test_client_fetches_critical_services() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"elements": [SCHOOL_NODE, HOSPITAL_WAY]})

    services = _client(handler).fetch_critical_services(AREA)

    assert {service.osm_id for service in services} == {501, -777}


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(429, text="rate limited"),
        httpx.Response(504, text="gateway timeout"),
        httpx.Response(200, text="<html>no es json</html>"),
        httpx.Response(200, json={"remark": "runtime error"}),
        httpx.Response(200, json=[1, 2]),
    ],
)
def test_client_turns_failures_into_source_error(response: httpx.Response) -> None:
    with pytest.raises(OsmSourceError):
        _client(lambda _: response).fetch_roads(AREA)


def test_client_turns_network_errors_into_source_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("sin red", request=request)

    with pytest.raises(OsmSourceError):
        _client(handler).fetch_roads(AREA)


def test_factory_sends_identifiable_user_agent() -> None:
    client = create_overpass_client(URL, "StreetRepo/test (contacto)", timeout_s=30)

    assert client._http.headers["User-Agent"] == "StreetRepo/test (contacto)"


def test_example_payload_is_valid_json() -> None:
    # Garantiza que los datos de prueba se serializan como los enviaría Overpass.
    assert json.loads(json.dumps({"elements": [ROAD, SCHOOL_NODE, HOSPITAL_WAY]}))


@pytest.mark.parametrize("status_code", [429, 502, 503, 504, None])
def test_transient_failures_are_retried_with_growing_delay(status_code: int | None) -> None:
    assert retry_delay(1, status_code) == 10.0
    assert retry_delay(2, status_code) == 20.0


@pytest.mark.parametrize("status_code", [400, 401, 403, 404, 500])
def test_permanent_failures_are_not_retried(status_code: int) -> None:
    assert retry_delay(1, status_code) is None


def test_gives_up_after_max_attempts() -> None:
    assert retry_delay(MAX_ATTEMPTS, 504) is None


def test_client_retries_then_succeeds() -> None:
    responses = iter(
        [httpx.Response(504), httpx.Response(429), httpx.Response(200, json={"elements": [ROAD]})]
    )
    waits: list[float] = []
    transport = httpx.MockTransport(lambda _: next(responses))
    client = OverpassClient(httpx.Client(transport=transport), URL, sleep=waits.append)

    roads = client.fetch_roads(AREA)

    assert [road.osm_id for road in roads] == [101]
    assert waits == [10.0, 20.0]


def test_client_stops_after_max_attempts() -> None:
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(503)

    with pytest.raises(OsmSourceError, match="503"):
        _client(handler).fetch_roads(AREA)

    assert len(calls) == MAX_ATTEMPTS


def test_client_does_not_retry_bad_query() -> None:
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(400)

    with pytest.raises(OsmSourceError):
        _client(handler).fetch_roads(AREA)

    assert len(calls) == 1
