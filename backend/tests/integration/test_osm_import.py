"""Carga OSM contra PostGIS real: upsert idempotente y geometrías correctas."""

from collections.abc import Sequence
from decimal import Decimal

import pytest
from sqlalchemy import Connection, text
from sqlalchemy.orm import Session

from app.modules.admin.application.import_osm_data import ImportOsmData
from app.modules.critical_services.domain.entities import OsmCriticalService
from app.modules.critical_services.domain.service_type import CriticalServiceType
from app.modules.critical_services.infrastructure.repository import SqlCriticalServiceRepository
from app.modules.roads.domain.entities import OsmRoad
from app.modules.roads.domain.road_class import RoadClass
from app.modules.roads.infrastructure.repository import SqlRoadRepository
from app.shared.domain.geo import BoundingBox, GeoPoint
from tests.integration.conftest import TEST_OSM_ID, requires_db

pytestmark = [pytest.mark.integration, requires_db]

AREA = BoundingBox(south=1.16, west=-77.33, north=1.25, east=-77.23)
ROAD_A, ROAD_B, ROAD_C = TEST_OSM_ID + 1, TEST_OSM_ID + 2, TEST_OSM_ID + 3
SCHOOL, HOSPITAL_AREA = TEST_OSM_ID + 11, -(TEST_OSM_ID + 12)


def _road(osm_id: int, name: str | None = "Calle de prueba", highway: str = "primary") -> OsmRoad:
    return OsmRoad(
        osm_id=osm_id,
        name=name,
        highway_tag=highway,
        road_class=RoadClass.PRIMARY,
        flow_factor=Decimal("10"),
        points=(GeoPoint(-77.2800, 1.2100), GeoPoint(-77.2790, 1.2110)),
    )


def _service(osm_id: int, name: str | None = "Escuela de prueba") -> OsmCriticalService:
    return OsmCriticalService(
        osm_id=osm_id,
        name=name,
        service_type=CriticalServiceType.SCHOOL,
        location=GeoPoint(-77.2810, 1.2140),
    )


def _count(conn: Connection, table: str) -> int:
    return conn.execute(text(f"SELECT count(*) FROM {table}")).scalar_one()  # noqa: S608


def _road_name(conn: Connection, osm_id: int) -> str | None:
    return conn.execute(
        text("SELECT nombre FROM via WHERE osm_id = :osm_id"), {"osm_id": osm_id}
    ).scalar_one()


def test_roads_are_stored_with_linestring_geometry(session: Session, conn: Connection) -> None:
    SqlRoadRepository(session).upsert_many([_road(ROAD_A)])
    session.flush()

    row = conn.execute(
        text(
            "SELECT nombre, highway_osm, jerarquia_vial, factor_flujo, "
            "ST_AsText(geom) AS wkt, ST_SRID(geom) AS srid FROM via WHERE osm_id = :osm_id"
        ),
        {"osm_id": ROAD_A},
    ).one()

    assert row.nombre == "Calle de prueba"
    assert row.highway_osm == "primary"
    assert row.jerarquia_vial == "primaria"
    assert row.factor_flujo == Decimal("10.00")
    assert row.wkt == "LINESTRING(-77.28 1.21,-77.279 1.211)"
    assert row.srid == 4326


def test_road_upsert_is_idempotent_and_updates(session: Session, conn: Connection) -> None:
    repository = SqlRoadRepository(session)
    before = _count(conn, "via")

    repository.upsert_many([_road(ROAD_A), _road(ROAD_B)])
    repository.upsert_many([_road(ROAD_A, name="Nombre nuevo"), _road(ROAD_B)])
    session.flush()

    assert _count(conn, "via") == before + 2
    assert _road_name(conn, ROAD_A) == "Nombre nuevo"


def test_duplicate_osm_ids_in_one_batch_keep_the_last(session: Session, conn: Connection) -> None:
    saved = SqlRoadRepository(session).upsert_many(
        [_road(ROAD_C, "Primero"), _road(ROAD_C, "Último")]
    )
    session.flush()

    assert saved == 1
    assert _road_name(conn, ROAD_C) == "Último"


def test_critical_services_upsert_is_idempotent(session: Session, conn: Connection) -> None:
    repository = SqlCriticalServiceRepository(session)
    before = _count(conn, "servicio_critico")

    repository.upsert_many([_service(SCHOOL), _service(HOSPITAL_AREA)])
    repository.upsert_many([_service(SCHOOL, name=None), _service(HOSPITAL_AREA)])
    session.flush()

    assert _count(conn, "servicio_critico") == before + 2
    row = conn.execute(
        text(
            "SELECT nombre, tipo, ST_AsText(ubicacion) AS wkt FROM servicio_critico "
            "WHERE osm_id = :osm_id"
        ),
        {"osm_id": SCHOOL},
    ).one()
    assert row.nombre is None
    assert row.tipo == "escuela"
    assert row.wkt == "POINT(-77.281 1.214)"


class _StaticSource:
    def fetch_roads(self, area: BoundingBox) -> Sequence[OsmRoad]:
        return [_road(ROAD_A), _road(ROAD_B, highway="trunk")]

    def fetch_critical_services(self, area: BoundingBox) -> Sequence[OsmCriticalService]:
        return [_service(SCHOOL)]


def test_import_use_case_end_to_end_is_repeatable(session: Session, conn: Connection) -> None:
    use_case = ImportOsmData(
        _StaticSource(), SqlRoadRepository(session), SqlCriticalServiceRepository(session), session
    )
    roads_before, services_before = _count(conn, "via"), _count(conn, "servicio_critico")

    first = use_case.execute(AREA)
    second = use_case.execute(AREA)

    assert first == second
    assert _count(conn, "via") == roads_before + 2
    assert _count(conn, "servicio_critico") == services_before + 1
