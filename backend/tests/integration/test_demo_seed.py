"""Datos de demostración contra PostGIS real (decisión 76).

Las vías y los servicios de prueba están en el océano Pacífico, dentro del área de
servicio de las pruebas, lejos de los datos reales de Pasto.
"""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Connection, text
from sqlalchemy.orm import Session

from app.cli import _build_seed_demo
from app.core.config import Environment, Settings
from app.main import API_V1_PREFIX
from app.modules.admin.application.demo_seed import SeedDemo
from app.modules.admin.domain.demo import (
    DEMO_ADMIN_EMAIL,
    DEMO_CITIZEN_EMAIL,
    DEMO_NEAR_SERVICE_COUNT,
    DEMO_OFF_ROAD_COUNT,
    DEMO_PRIORITIZED_NOTE,
    DEMO_REPAIRED_NOTE,
    DEMO_REPORT_COUNT,
    NotEnoughOsmDataError,
)
from app.modules.admin.infrastructure.demo_points import MIN_SEPARATION_M, PostgisDemoPointPicker
from app.modules.auth.infrastructure.passwords import Argon2PasswordHasher
from app.modules.users.infrastructure.repository import SqlUserRepository
from app.shared.domain.geo import BoundingBox
from tests.conftest import TEST_JWT_SECRET
from tests.integration.conftest import (
    PASSWORD,
    TEST_OSM_ID,
    TEST_REPORT_AREA,
    insert_report,
    insert_user,
    requires_db,
)

pytestmark = [pytest.mark.integration, requires_db]

LON, LAT = -80.0, 0.0
# En el ecuador 1° de latitud ≈ 110 574 m.
METERS_PER_DEGREE_LAT = 110_574.0
# Separación entre las vías de prueba (≈ 220 m): cada punto medio queda lejos de las demás.
ROAD_SPACING_DEG = 0.002
# Dos vías de más por jerarquía; las dos residenciales sobrantes tienen un hospital al frente.
ROADS_BY_CLASS = (
    ("primary", "primaria", 10),
    ("secondary", "secundaria", 10),
    ("tertiary", "terciaria", 8),
    ("residential", "residencial", 8),
)
HOSPITAL_DISTANCE_M = 40.0
AREA = BoundingBox.parse(TEST_REPORT_AREA)


def _insert_osm_data(conn: Connection) -> None:
    row = 0
    residential_lats: list[float] = []
    for highway, road_class, count in ROADS_BY_CLASS:
        for _ in range(count):
            row += 1
            lat = LAT + row * ROAD_SPACING_DEG
            conn.execute(
                text(
                    "INSERT INTO via (osm_id, nombre, highway_osm, jerarquia_vial, factor_flujo, "
                    "geom) VALUES (:osm_id, :name, :highway, CAST(:road_class AS jerarquia_vial), "
                    "2, ST_GeomFromText(:wkt, 4326))"
                ),
                {
                    "osm_id": TEST_OSM_ID + 500 + row,
                    "name": f"Vía de prueba {row}",
                    "highway": highway,
                    "road_class": road_class,
                    "wkt": f"LINESTRING({LON - 0.001} {lat}, {LON + 0.001} {lat})",
                },
            )
            if highway == "residential":
                residential_lats.append(lat)
    for number, lat in enumerate(residential_lats[-DEMO_NEAR_SERVICE_COUNT:]):
        conn.execute(
            text(
                "INSERT INTO servicio_critico (osm_id, nombre, tipo, ubicacion) "
                "VALUES (:osm_id, 'Hospital de prueba', 'hospital', "
                "ST_SetSRID(ST_MakePoint(:lon, :lat), 4326))"
            ),
            {
                "osm_id": TEST_OSM_ID + 600 + number,
                "lon": LON,
                "lat": lat + HOSPITAL_DISTANCE_M / METERS_PER_DEGREE_LAT,
            },
        )


def _seed(session: Session, photo_dir: Path) -> SeedDemo:
    """El mismo armado que usa ``python -m app.cli seed-demo``, con las fotos reales."""
    settings = Settings(
        app_env=Environment.TEST,
        jwt_secret_key=TEST_JWT_SECRET,
        photo_storage_dir=photo_dir,
        report_area_bbox=TEST_REPORT_AREA,
    )
    return _build_seed_demo(session, settings)


def _photo_files(photo_dir: Path) -> list[Path]:
    return sorted(photo_dir.rglob("*.jpg"))


def _count(conn: Connection, sql: str) -> int:
    count: int = conn.execute(text(sql)).scalar_one()
    return count


DEMO_REPORTS = (
    "FROM reporte AS r JOIN usuario AS u ON u.id_usuario = r.id_usuario "
    "WHERE u.correo LIKE '%@demo.invalid'"
)


def test_seed_creates_reports_with_all_cases(
    session: Session, conn: Connection, photo_dir: Path
) -> None:
    _insert_osm_data(conn)

    assert _seed(session, photo_dir).execute() == DEMO_REPORT_COUNT

    reports = conn.execute(
        text(
            "SELECT r.severidad, r.estado, r.puntaje_prioridad, r.descripcion, "
            "v.jerarquia_vial, e.p_proximidad, e.u_utilidad, "
            "(SELECT count(*) FROM evaluacion_prioridad AS x "
            " WHERE x.id_reporte = r.id_reporte) AS evaluaciones, "
            "(SELECT count(*) FROM evidencia AS x WHERE x.id_reporte = r.id_reporte) AS fotos "
            "FROM reporte AS r JOIN usuario AS u ON u.id_usuario = r.id_usuario "
            "LEFT JOIN via AS v ON v.id_via = r.id_via "
            "JOIN evaluacion_prioridad AS e ON e.id_reporte = r.id_reporte "
            "WHERE u.correo = :citizen"
        ),
        {"citizen": DEMO_CITIZEN_EMAIL},
    ).all()
    assert len(reports) == DEMO_REPORT_COUNT
    assert {row.severidad for row in reports} == {1, 2, 3}
    assert {row.jerarquia_vial for row in reports} == {
        "primaria",
        "secundaria",
        "terciaria",
        "residencial",
        None,  # sin vía a 30 m: «Revisar vía»
    }
    assert sum(row.jerarquia_vial is None for row in reports) == DEMO_OFF_ROAD_COUNT
    assert sum(row.p_proximidad == 10 for row in reports) >= DEMO_NEAR_SERVICE_COUNT
    assert any(row.p_proximidad == 0 for row in reports)
    # Una sola evaluación, la del motor, y su U es la que queda en el reporte.
    assert all(row.evaluaciones == 1 and row.fotos == 1 for row in reports)
    assert all(row.puntaje_prioridad == row.u_utilidad for row in reports)
    assert all("demostración" in row.descripcion for row in reports)
    statuses = [row.estado for row in reports]
    assert (
        statuses.count("evaluado"),
        statuses.count("priorizado"),
        statuses.count("reparado"),
    ) == (
        20,
        8,
        4,
    )
    # Foto y miniatura por reporte.
    assert len(_photo_files(photo_dir)) == 2 * DEMO_REPORT_COUNT


def test_seed_history_is_signed_by_the_demo_admin(
    session: Session, conn: Connection, photo_dir: Path
) -> None:
    _insert_osm_data(conn)
    _seed(session, photo_dir).execute()

    history = conn.execute(
        text(
            "SELECT h.estado_nuevo, h.observacion, a.correo "
            "FROM historial_estado AS h JOIN reporte AS r ON r.id_reporte = h.id_reporte "
            "LEFT JOIN usuario AS a ON a.id_usuario = h.id_usuario "
            "WHERE r.estado = 'reparado' ORDER BY h.id_reporte, h.id_historial"
        )
    ).all()

    assert [tuple(row) for row in history[:4]] == [
        ("registrado", None, DEMO_CITIZEN_EMAIL),
        ("evaluado", None, None),
        ("priorizado", DEMO_PRIORITIZED_NOTE, DEMO_ADMIN_EMAIL),
        ("reparado", DEMO_REPAIRED_NOTE, DEMO_ADMIN_EMAIL),
    ]
    assert len(history) == 4 * 4


def test_seed_twice_creates_nothing_new(
    session: Session, conn: Connection, photo_dir: Path
) -> None:
    _insert_osm_data(conn)
    _seed(session, photo_dir).execute()

    assert _seed(session, photo_dir).execute() == 0

    assert _count(conn, f"SELECT count(*) {DEMO_REPORTS}") == DEMO_REPORT_COUNT
    assert len(_photo_files(photo_dir)) == 2 * DEMO_REPORT_COUNT


def test_seed_without_osm_data_fails_and_leaves_nothing(
    session: Session, conn: Connection, photo_dir: Path
) -> None:
    with pytest.raises(NotEnoughOsmDataError):
        _seed(session, photo_dir).execute()

    assert _count(conn, "SELECT count(*) FROM usuario WHERE correo LIKE '%@demo.invalid'") == 0
    assert _photo_files(photo_dir) == []


def test_seed_remove_deletes_everything(
    session: Session, conn: Connection, photo_dir: Path
) -> None:
    _insert_osm_data(conn)
    real_user = insert_user(conn)
    real_report = insert_report(conn, real_user, LON + 0.01, LAT)
    seed = _seed(session, photo_dir)
    seed.execute()

    assert seed.remove() == DEMO_REPORT_COUNT

    assert _count(conn, "SELECT count(*) FROM usuario WHERE correo LIKE '%@demo.invalid'") == 0
    for table in ("evidencia", "evaluacion_prioridad", "historial_estado", "confirmacion"):
        assert _count(conn, f"SELECT count(*) FROM {table}") == 0, table  # noqa: S608
    assert _photo_files(photo_dir) == []
    # Lo que no es de demostración no se toca.
    remaining = conn.execute(text("SELECT id_reporte, id_usuario FROM reporte")).all()
    assert [tuple(row) for row in remaining] == [(real_report, real_user)]
    # Y se puede volver a cargar.
    assert seed.execute() == DEMO_REPORT_COUNT


def test_remove_without_demo_data_deletes_nothing(
    session: Session, conn: Connection, photo_dir: Path
) -> None:
    insert_report(conn, insert_user(conn), LON, LAT)

    assert _seed(session, photo_dir).remove() == 0

    assert _count(conn, "SELECT count(*) FROM reporte") == 1


def test_demo_points_are_deterministic_and_apart(session: Session, conn: Connection) -> None:
    _insert_osm_data(conn)
    picker = PostgisDemoPointPicker(session)

    points = picker.pick(AREA)

    assert points == picker.pick(AREA)
    assert len(points) == DEMO_REPORT_COUNT
    assert all(AREA.contains(point.location) for point in points)
    closest = conn.execute(
        text(
            "SELECT min(ST_Distance(a.g::geography, b.g::geography)) FROM "
            "(SELECT row_number() OVER () AS n, ST_SetSRID(ST_MakePoint(lon, lat), 4326) AS g "
            " FROM unnest(CAST(:lons AS float8[]), CAST(:lats AS float8[])) AS p(lon, lat)) AS a "
            "JOIN (SELECT row_number() OVER () AS n, "
            "      ST_SetSRID(ST_MakePoint(lon, lat), 4326) AS g "
            " FROM unnest(CAST(:lons AS float8[]), CAST(:lats AS float8[])) AS p(lon, lat)) AS b "
            "ON a.n < b.n"
        ),
        {
            "lons": [point.location.longitude for point in points],
            "lats": [point.location.latitude for point in points],
        },
    ).scalar_one()
    # Medido por PostGIS, no por la aproximación del selector.
    assert closest > MIN_SEPARATION_M * 0.99


def test_demo_points_ignore_roads_outside_the_area(session: Session, conn: Connection) -> None:
    _insert_osm_data(conn)
    elsewhere = BoundingBox(south=10.0, west=-70.0, north=10.5, east=-69.5)

    points = PostgisDemoPointPicker(session).pick(elsewhere)

    # Sin vías ni servicios dentro del área solo quedan los puntos «sin vía».
    assert len(points) == DEMO_OFF_ROAD_COUNT
    assert all(elsewhere.contains(point.location) for point in points)


def test_demo_admin_cannot_log_in(
    api: TestClient, session: Session, conn: Connection, photo_dir: Path
) -> None:
    _insert_osm_data(conn)
    _seed(session, photo_dir).execute()
    admin = SqlUserRepository(session).get_by_email(DEMO_ADMIN_EMAIL)
    assert admin is not None

    # Ninguna contraseña coincide con la marca guardada…
    assert not Argon2PasswordHasher().verify(admin.password_hash, PASSWORD)
    # … y la API ni siquiera acepta el correo: ``.invalid`` no es un dominio real.
    login = api.post(
        f"{API_V1_PREFIX}/auth/login", json={"email": DEMO_ADMIN_EMAIL, "password": PASSWORD}
    )
    assert login.status_code == 422
