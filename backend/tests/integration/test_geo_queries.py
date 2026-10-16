"""Map-matching (30 m) y proximidad (500 m) contra PostGIS con distancias conocidas.

Las geometrías de prueba están en el océano Pacífico, sobre el ecuador, lejos de
los datos reales de Pasto que pueda tener la base de desarrollo. Los puntos se
generan con ST_Project (N metros hacia un azimut) para probar los bordes sin
calcular coordenadas a mano.
"""

from decimal import Decimal

import pytest
from sqlalchemy import Connection, text
from sqlalchemy.orm import Session

from app.modules.critical_services.domain.service_type import CriticalServiceType
from app.modules.critical_services.infrastructure.locator import PostgisCriticalServiceLocator
from app.modules.roads.domain.road_class import RoadClass
from app.modules.roads.infrastructure.matcher import PostgisRoadMatcher
from app.shared.domain.geo import GeoPoint
from app.shared.domain.geo_parameters import PROXIMITY_MAX_RADIUS_M, ROAD_MATCHING_RADIUS_M
from tests.integration.conftest import TEST_OSM_ID, requires_db

pytestmark = [pytest.mark.integration, requires_db]

ORIGIN = GeoPoint(longitude=-80.0, latitude=0.0)
# Tolerancia frente a la diferencia entre el cálculo de ST_Project y ST_Distance.
TOLERANCE_M = 0.5
NORTH, SOUTH, EAST = 0.0, 180.0, 90.0


def _point_at(conn: Connection, distance_m: float, azimuth_deg: float = NORTH) -> GeoPoint:
    row = conn.execute(
        text(
            "SELECT ST_X(p::geometry) AS lon, ST_Y(p::geometry) AS lat FROM ("
            "SELECT ST_Project(ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography, "
            ":distance, radians(:azimuth)) AS p) AS projected"
        ),
        {
            "lon": ORIGIN.longitude,
            "lat": ORIGIN.latitude,
            "distance": distance_m,
            "azimuth": azimuth_deg,
        },
    ).one()
    return GeoPoint(longitude=row.lon, latitude=row.lat)


def _insert_road(
    conn: Connection, osm_id: int, through: GeoPoint, road_class: str, flow: str
) -> int:
    """Vía este-oeste de ~220 m que pasa por ``through``."""
    wkt = (
        f"LINESTRING({through.longitude - 0.001} {through.latitude}, "
        f"{through.longitude + 0.001} {through.latitude})"
    )
    return conn.execute(
        text(
            "INSERT INTO via (osm_id, nombre, highway_osm, jerarquia_vial, factor_flujo, geom) "
            "VALUES (:osm_id, 'Vía de prueba', 'primary', :clase, :flujo, "
            "ST_GeomFromText(:wkt, 4326)) RETURNING id_via"
        ),
        {"osm_id": osm_id, "clase": road_class, "flujo": flow, "wkt": wkt},
    ).scalar_one()


def _insert_service(conn: Connection, osm_id: int, location: GeoPoint, kind: str) -> int:
    return conn.execute(
        text(
            "INSERT INTO servicio_critico (osm_id, nombre, tipo, ubicacion) "
            "VALUES (:osm_id, 'Servicio de prueba', :tipo, "
            "ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)) RETURNING id_servicio"
        ),
        {"osm_id": osm_id, "tipo": kind, "lon": location.longitude, "lat": location.latitude},
    ).scalar_one()


@pytest.fixture
def matcher(session: Session) -> PostgisRoadMatcher:
    return PostgisRoadMatcher(session)


@pytest.fixture
def locator(session: Session) -> PostgisCriticalServiceLocator:
    return PostgisCriticalServiceLocator(session)


# --- Map-matching a la vía (30 m) ---


def test_road_inside_radius_is_matched_with_its_flow(
    conn: Connection, matcher: PostgisRoadMatcher
) -> None:
    road_id = _insert_road(conn, TEST_OSM_ID + 1, ORIGIN, "secundaria", "7")

    match = matcher.find_nearest(_point_at(conn, 29.5), ROAD_MATCHING_RADIUS_M)

    assert match is not None
    assert match.road_id == road_id
    assert match.road_class is RoadClass.SECONDARY
    assert match.flow_factor == Decimal("7.00")
    assert match.distance_m == pytest.approx(29.5, abs=TOLERANCE_M)


def test_road_beyond_radius_is_not_matched(conn: Connection, matcher: PostgisRoadMatcher) -> None:
    # Sin vía a 30 m el reporte se marcará "Revisar vía" con F = 2 (guía 2.2).
    _insert_road(conn, TEST_OSM_ID + 1, ORIGIN, "primaria", "10")

    assert matcher.find_nearest(_point_at(conn, 30.5), ROAD_MATCHING_RADIUS_M) is None


def test_point_on_the_road_has_zero_distance(conn: Connection, matcher: PostgisRoadMatcher) -> None:
    _insert_road(conn, TEST_OSM_ID + 1, ORIGIN, "terciaria", "5")

    match = matcher.find_nearest(ORIGIN, ROAD_MATCHING_RADIUS_M)

    assert match is not None
    assert match.distance_m == pytest.approx(0.0, abs=0.01)


def test_closest_road_wins_over_higher_hierarchy(
    conn: Connection, matcher: PostgisRoadMatcher
) -> None:
    # La vía la decide la distancia, no la jerarquía: no se "infla" F con una avenida vecina.
    _insert_road(conn, TEST_OSM_ID + 1, _point_at(conn, 20), "primaria", "10")
    residential = _insert_road(
        conn, TEST_OSM_ID + 2, _point_at(conn, 10, SOUTH), "residencial", "2"
    )

    match = matcher.find_nearest(ORIGIN, ROAD_MATCHING_RADIUS_M)

    assert match is not None
    assert match.road_id == residential
    assert match.distance_m == pytest.approx(10, abs=TOLERANCE_M)


def test_equidistant_roads_resolve_deterministically(
    conn: Connection, matcher: PostgisRoadMatcher
) -> None:
    first = _insert_road(conn, TEST_OSM_ID + 1, _point_at(conn, 15), "primaria", "10")
    _insert_road(conn, TEST_OSM_ID + 2, _point_at(conn, 15, SOUTH), "residencial", "2")

    results = {matcher.find_nearest(ORIGIN, ROAD_MATCHING_RADIUS_M) for _ in range(3)}

    assert len(results) == 1
    match = results.pop()
    assert match is not None
    assert match.road_id == first


# --- Proximidad a servicios críticos (500 m) ---


def test_service_inside_radius_is_found_with_distance(
    conn: Connection, locator: PostgisCriticalServiceLocator
) -> None:
    service_id = _insert_service(conn, TEST_OSM_ID + 11, _point_at(conn, 499.5, EAST), "hospital")

    nearest = locator.find_nearest(ORIGIN, PROXIMITY_MAX_RADIUS_M)

    assert nearest is not None
    assert nearest.service_id == service_id
    assert nearest.service_type is CriticalServiceType.HOSPITAL
    assert nearest.distance_m == pytest.approx(499.5, abs=TOLERANCE_M)


def test_service_beyond_radius_is_ignored(
    conn: Connection, locator: PostgisCriticalServiceLocator
) -> None:
    # Más allá de 500 m, P = 0 (guía 2.2).
    _insert_service(conn, TEST_OSM_ID + 11, _point_at(conn, 500.5, EAST), "escuela")

    assert locator.find_nearest(ORIGIN, PROXIMITY_MAX_RADIUS_M) is None


@pytest.mark.parametrize("distance_m", [100.0, 300.0])
def test_proximity_distance_is_accurate(
    conn: Connection, locator: PostgisCriticalServiceLocator, distance_m: float
) -> None:
    # Las distancias alimentan la fórmula de P (100 m -> 10, 500 m -> 0): deben ser exactas.
    _insert_service(conn, TEST_OSM_ID + 11, _point_at(conn, distance_m, EAST), "escuela")

    nearest = locator.find_nearest(ORIGIN, PROXIMITY_MAX_RADIUS_M)

    assert nearest is not None
    assert nearest.distance_m == pytest.approx(distance_m, abs=TOLERANCE_M)


def test_nearest_service_is_chosen_among_several(
    conn: Connection, locator: PostgisCriticalServiceLocator
) -> None:
    _insert_service(conn, TEST_OSM_ID + 11, _point_at(conn, 400, EAST), "hospital")
    school = _insert_service(conn, TEST_OSM_ID + 12, _point_at(conn, 150, NORTH), "escuela")

    nearest = locator.find_nearest(ORIGIN, PROXIMITY_MAX_RADIUS_M)

    assert nearest is not None
    assert nearest.service_id == school
    assert nearest.service_type is CriticalServiceType.SCHOOL
