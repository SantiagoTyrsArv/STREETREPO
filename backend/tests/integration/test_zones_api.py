"""Zonas de validación contra PostGIS real: importación, zona del reporte y GET /admin/zones."""

import uuid
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Connection, text
from sqlalchemy.orm import Session

from app.main import API_V1_PREFIX
from app.modules.validation.application.import_zones import ImportZones
from app.modules.validation.domain.zones import InvalidZonesError
from app.modules.validation.infrastructure.zone_repository import SqlZoneRepository
from tests.images import jpeg_with_metadata
from tests.integration.conftest import (
    bearer,
    insert_report,
    insert_user,
    login_user,
    register_user,
    requires_db,
)
from tests.integration.test_admin_dashboard_api import _admin_token, _citizen_token

pytestmark = [pytest.mark.integration, requires_db]

ZONES = f"{API_V1_PREFIX}/admin/zones"


def _square(west: float, south: float, east: float, north: float) -> dict[str, Any]:
    ring = [[west, south], [west, north], [east, north], [east, south], [west, south]]
    return {"type": "Polygon", "coordinates": [ring]}


def _feature(name: str, concentration: str, geometry: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "Feature",
        "properties": {"name": name, "concentration": concentration},
        "geometry": geometry,
    }


def _collection(*features: dict[str, Any]) -> dict[str, Any]:
    return {"type": "FeatureCollection", "features": list(features)}


# Dos zonas contiguas en el Pacífico: «Centro» (lon -80.01..-79.99) y «Obonuco» (-79.98..-79.96).
CENTRO = _feature("Centro", "alta", _square(-80.01, -0.01, -79.99, 0.01))
OBONUCO = _feature("Obonuco", "baja", _square(-79.98, -0.01, -79.96, 0.01))


def _import(session: Session, geojson: dict[str, Any]) -> tuple[int, int]:
    result = ImportZones(SqlZoneRepository(session), session).execute(geojson)
    return result.zones, result.reports_assigned


def _zone_of(conn: Connection, report_id: uuid.UUID) -> str | None:
    return conn.execute(
        text(
            "SELECT z.nombre FROM reporte r LEFT JOIN zona z ON z.id_zona = r.id_zona "
            "WHERE r.id_reporte = :id"
        ),
        {"id": report_id},
    ).scalar_one()


def _zone_row(conn: Connection, name: str) -> Any:
    return conn.execute(
        text(
            "SELECT CAST(concentracion AS text) AS concentracion, "
            "ST_XMax(geom) AS east FROM zona WHERE nombre = :n"
        ),
        {"n": name},
    ).one()


def _zone_count(conn: Connection) -> int:
    return conn.execute(text("SELECT count(*) FROM zona")).scalar_one()


def test_import_assigns_reports_inside_and_leaves_the_rest_without_zone(
    session: Session, conn: Connection
) -> None:
    author = insert_user(conn)
    inside_a = insert_report(conn, author, -80.0, 0.0)
    inside_b = insert_report(conn, author, -79.97, 0.0)
    outside = insert_report(conn, author, -79.5, 0.0)

    assert _import(session, _collection(CENTRO, OBONUCO)) == (2, 2)

    assert _zone_of(conn, inside_a) == "Centro"
    assert _zone_of(conn, inside_b) == "Obonuco"
    assert _zone_of(conn, outside) is None


def test_reimport_replaces_geometry_and_concentration_and_reassigns(
    session: Session, conn: Connection
) -> None:
    author = insert_user(conn)
    report = insert_report(conn, author, -79.9, 0.0)
    _import(session, _collection(CENTRO))
    assert _zone_of(conn, report) is None

    moved = _feature("Centro", "baja", _square(-80.01, -0.01, -79.85, 0.01))
    assert _import(session, _collection(moved)) == (1, 1)

    assert _zone_count(conn) == 1
    row = _zone_row(conn, "Centro")
    assert row.concentracion == "baja"
    assert row.east == pytest.approx(-79.85)
    assert _zone_of(conn, report) == "Centro"


def test_reimport_leaves_zones_missing_from_the_file_untouched(
    session: Session, conn: Connection
) -> None:
    _import(session, _collection(CENTRO))

    _import(session, _collection(OBONUCO))

    assert _zone_count(conn) == 2


def test_overlapping_polygons_change_nothing(session: Session, conn: Connection) -> None:
    author = insert_user(conn)
    report = insert_report(conn, author, -80.0, 0.0)
    overlapping = _feature("Norte", "baja", _square(-80.005, -0.005, -79.985, 0.02))

    with pytest.raises(InvalidZonesError, match=r"Centro.*Norte|Norte.*Centro"):
        _import(session, _collection(CENTRO, overlapping))

    assert _zone_count(conn) == 0
    assert _zone_of(conn, report) is None


def test_overlap_with_an_existing_zone_is_rejected_and_keeps_the_previous_state(
    session: Session, conn: Connection
) -> None:
    _import(session, _collection(CENTRO))
    overlapping = _feature("Norte", "baja", _square(-80.005, -0.005, -79.985, 0.02))

    with pytest.raises(InvalidZonesError, match="Norte"):
        _import(session, _collection(overlapping))

    assert _zone_count(conn) == 1
    assert _zone_row(conn, "Centro").concentracion == "alta"


def test_zones_sharing_only_an_edge_are_allowed(session: Session, conn: Connection) -> None:
    neighbour = _feature("Vecina", "baja", _square(-79.99, -0.01, -79.97, 0.01))

    assert _import(session, _collection(CENTRO, neighbour))[0] == 2


def test_self_intersecting_polygon_is_rejected(session: Session, conn: Connection) -> None:
    bowtie = {
        "type": "Polygon",
        "coordinates": [[[-80.0, 0.0], [-79.99, 0.01], [-79.99, 0.0], [-80.0, 0.01], [-80.0, 0.0]]],
    }

    with pytest.raises(InvalidZonesError, match="Corbata"):
        _import(session, _collection(_feature("Corbata", "alta", bowtie)))

    assert _zone_count(conn) == 0


def test_unreadable_polygon_is_rejected(session: Session, conn: Connection) -> None:
    broken = {"type": "Polygon", "coordinates": [[["x", "y"]]]}

    with pytest.raises(InvalidZonesError, match="Rota"):
        _import(session, _collection(_feature("Rota", "alta", broken)))


def test_a_report_created_inside_a_zone_gets_its_zone(
    api: TestClient, session: Session, conn: Connection, photo_dir: Path
) -> None:
    _import(session, _collection(CENTRO))
    register_user(api)
    token = str(login_user(api)["access_token"])

    created = api.post(
        f"{API_V1_PREFIX}/reports",
        data={"longitude": "-80.0", "latitude": "0.0", "severity": "alta"},
        files={"photo": ("IMG_0001.jpg", jpeg_with_metadata(), "image/jpeg")},
        headers=bearer(token),
    )

    assert created.status_code == 201, created.json()
    assert _zone_of(conn, uuid.UUID(created.json()["id"])) == "Centro"


def test_a_report_created_outside_every_zone_has_no_zone(
    api: TestClient, session: Session, conn: Connection
) -> None:
    _import(session, _collection(CENTRO))
    register_user(api)
    token = str(login_user(api)["access_token"])

    created = api.post(
        f"{API_V1_PREFIX}/reports",
        data={"longitude": "-79.9", "latitude": "0.0", "severity": "alta"},
        files={"photo": ("IMG_0001.jpg", jpeg_with_metadata(), "image/jpeg")},
        headers=bearer(token),
    )

    assert created.status_code == 201, created.json()
    assert _zone_of(conn, uuid.UUID(created.json()["id"])) is None


def test_list_zones_counts_active_and_total_reports(
    api: TestClient, session: Session, conn: Connection
) -> None:
    token = _admin_token(api, conn)
    author = insert_user(conn, email="autor@example.test")
    insert_report(conn, author, -80.0, 0.0)
    repaired = insert_report(conn, author, -80.001, 0.0)
    conn.execute(
        text("UPDATE reporte SET estado = 'reparado' WHERE id_reporte = :id"), {"id": repaired}
    )
    insert_report(conn, author, -79.5, 0.0)
    _import(session, _collection(CENTRO, OBONUCO))

    response = api.get(ZONES, headers=bearer(token))

    assert response.status_code == 200
    centro, obonuco = response.json()["items"]
    assert (centro["name"], centro["concentration"]) == ("Centro", "alta")
    assert (centro["active_reports"], centro["total_reports"]) == (1, 2)
    assert (obonuco["name"], obonuco["concentration"]) == ("Obonuco", "baja")
    assert (obonuco["active_reports"], obonuco["total_reports"]) == (0, 0)
    assert centro["geometry"]["type"] == "Polygon"
    assert isinstance(centro["id"], int)


def test_list_zones_is_empty_without_zones(api: TestClient, conn: Connection) -> None:
    token = _admin_token(api, conn)

    assert api.get(ZONES, headers=bearer(token)).json() == {"items": []}


def test_list_zones_requires_an_administrator(api: TestClient, conn: Connection) -> None:
    assert api.get(ZONES).status_code == 401
    citizen = _citizen_token(api)
    assert api.get(ZONES, headers=bearer(citizen)).status_code == 403

    register_user(api, email="evaluadora@example.com")
    conn.execute(
        text("UPDATE usuario SET rol = 'evaluador' WHERE correo = 'evaluadora@example.com'")
    )
    evaluator = str(login_user(api, email="evaluadora@example.com")["access_token"])
    response = api.get(ZONES, headers=bearer(evaluator))

    assert response.status_code == 403
    assert response.json()["code"] == "FORBIDDEN"
