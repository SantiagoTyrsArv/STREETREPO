"""POST /api/v1/reports por HTTP contra PostGIS real: reporte, foto, historial y evaluación.

Como en las demás pruebas de PostGIS, el punto está en el océano Pacífico, sobre el
ecuador, lejos de los datos reales de Pasto; el área de servicio de la prueba lo incluye.
"""

import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Connection, text
from sqlalchemy.orm import Session

from app.core.database import get_engine
from app.main import API_V1_PREFIX
from app.modules.reports.domain.new_report import NewReport
from app.modules.reports.domain.photos import PhotoKeys
from app.modules.reports.domain.ports import DuplicateIdempotencyKeyError
from app.modules.reports.domain.severity import Severity
from app.modules.reports.infrastructure.nearby import (
    REPORT_CREATION_LOCK_KEY,
    PostgresReportCreationLock,
)
from app.modules.reports.infrastructure.repository import SqlReportRepository
from app.shared.domain.geo import BoundingBox, GeoPoint
from tests.images import EXIF_GPS_IFD, EXIF_MAKE, jpeg_with_metadata, open_image
from tests.integration.conftest import (
    PASSWORD,
    TEST_OSM_ID,
    TEST_REPORT_AREA,
    bearer,
    insert_report,
    insert_user,
    login_user,
    register_user,
    requires_db,
)

pytestmark = [pytest.mark.integration, requires_db]

REPORTS = f"{API_V1_PREFIX}/reports"
LON, LAT = -80.0, 0.0
FORM = {"longitude": str(LON), "latitude": str(LAT), "severity": "alta"}


def _token(api: TestClient) -> str:
    register_user(api)
    return str(login_user(api)["access_token"])


def _photo() -> dict[str, tuple[str, bytes, str]]:
    return {"photo": ("IMG_0001.jpg", jpeg_with_metadata(), "image/jpeg")}


def _insert_secondary_road(conn: Connection, name: str | None = "Vía de prueba") -> int:
    return conn.execute(
        text(
            "INSERT INTO via (osm_id, nombre, highway_osm, jerarquia_vial, factor_flujo, geom) "
            "VALUES (:osm_id, :name, 'secondary', 'secundaria', 7, "
            "ST_GeomFromText(:wkt, 4326)) RETURNING id_via"
        ),
        {
            "osm_id": TEST_OSM_ID + 201,
            "name": name,
            "wkt": f"LINESTRING({LON - 0.001} {LAT}, {LON + 0.001} {LAT})",
        },
    ).scalar_one()


def _count(conn: Connection, table: str, report_id: str) -> int:
    queries = {
        "historial_estado": "SELECT count(*) FROM historial_estado WHERE id_reporte = :id",
        "evaluacion_prioridad": "SELECT count(*) FROM evaluacion_prioridad WHERE id_reporte = :id",
        "evidencia": "SELECT count(*) FROM evidencia WHERE id_reporte = :id",
    }
    return conn.execute(text(queries[table]), {"id": report_id}).scalar_one()


def test_create_report_on_a_road(api: TestClient, conn: Connection, photo_dir: Path) -> None:
    road_id = _insert_secondary_road(conn)

    response = api.post(
        REPORTS,
        data=FORM | {"description": " Hueco en el carril derecho "},
        files=_photo(),
        headers=bearer(_token(api)),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "evaluado"
    assert body["severity"] == "alta"
    assert body["description"] == "Hueco en el carril derecho"
    assert body["location"] == {"longitude": LON, "latitude": LAT}
    assert body["address"] == "Vía de prueba"
    # U = 0,5·10 + 0,3·7 + 0,2·0 (sin servicios críticos a 500 m).
    assert body["priority_score"] == "7.10"
    assert body["needs_road_review"] is False

    report = conn.execute(
        text("SELECT id_via, severidad FROM reporte WHERE id_reporte = :id"), {"id": body["id"]}
    ).one()
    assert (report.id_via, report.severidad) == (road_id, Severity.HIGH)
    assert _count(conn, "evaluacion_prioridad", body["id"]) == 1


def test_history_starts_registered_by_the_citizen_then_evaluated_by_the_engine(
    api: TestClient, conn: Connection
) -> None:
    body = api.post(REPORTS, data=FORM, files=_photo(), headers=bearer(_token(api))).json()

    history = conn.execute(
        text(
            "SELECT estado_anterior, estado_nuevo, id_usuario IS NULL AS by_system "
            "FROM historial_estado WHERE id_reporte = :id ORDER BY id_historial"
        ),
        {"id": body["id"]},
    ).all()
    assert [(row.estado_anterior, row.estado_nuevo, row.by_system) for row in history] == [
        (None, "registrado", False),
        ("registrado", "evaluado", True),
    ]


def test_photo_is_stored_recoded_without_metadata(
    api: TestClient, conn: Connection, photo_dir: Path
) -> None:
    body = api.post(REPORTS, data=FORM, files=_photo(), headers=bearer(_token(api))).json()

    evidence = conn.execute(
        text("SELECT url_foto, formato, tamano_bytes FROM evidencia WHERE id_reporte = :id"),
        {"id": body["id"]},
    ).one()
    keys = PhotoKeys.from_photo_key(evidence.url_foto)
    stored = (photo_dir / keys.photo).read_bytes()
    assert evidence.formato == "jpg"
    assert evidence.tamano_bytes == len(stored)
    assert (photo_dir / keys.thumbnail).is_file()
    # La clave no revela el reporte ni el nombre del archivo original.
    assert body["id"] not in evidence.url_foto
    assert "IMG_0001" not in evidence.url_foto
    exif = open_image(stored).getexif()
    assert EXIF_MAKE not in exif
    assert not exif.get_ifd(EXIF_GPS_IFD)


def test_without_a_road_nearby_it_is_marked_for_road_review(api: TestClient) -> None:
    response = api.post(
        REPORTS, data=FORM | {"severity": "media"}, files=_photo(), headers=bearer(_token(api))
    )

    body = response.json()
    assert body["needs_road_review"] is True
    assert body["address"] == "Sin vía asociada"
    # Sector Obonuco de la guía 8.3: S = 6, F = 2, P = 0.
    assert body["priority_score"] == "3.60"


def test_road_without_a_name_shows_the_fallback_text(api: TestClient, conn: Connection) -> None:
    _insert_secondary_road(conn, name=None)

    body = api.post(REPORTS, data=FORM, files=_photo(), headers=bearer(_token(api))).json()

    assert body["address"] == "Vía sin nombre"
    assert body["needs_road_review"] is False


def test_retry_with_the_same_idempotency_key_does_not_duplicate(
    api: TestClient, conn: Connection, photo_dir: Path
) -> None:
    headers = bearer(_token(api)) | {"Idempotency-Key": str(uuid.uuid4())}
    first = api.post(REPORTS, data=FORM, files=_photo(), headers=headers)

    second = api.post(REPORTS, data=FORM, files=_photo(), headers=headers)

    assert (first.status_code, second.status_code) == (201, 200)
    assert second.json() == first.json()
    assert _count(conn, "evidencia", first.json()["id"]) == 1
    assert len([path for path in photo_dir.rglob("*.jpg")]) == 2  # foto y miniatura


def test_same_idempotency_key_with_other_data_is_422(api: TestClient, conn: Connection) -> None:
    headers = bearer(_token(api)) | {"Idempotency-Key": str(uuid.uuid4())}
    first = api.post(REPORTS, data=FORM, files=_photo(), headers=headers)

    second = api.post(REPORTS, data=FORM | {"severity": "baja"}, files=_photo(), headers=headers)

    assert first.status_code == 201
    assert second.status_code == 422
    assert second.json()["code"] == "IDEMPOTENCY_KEY_REUSED"
    assert conn.execute(text("SELECT count(*) FROM reporte")).scalar_one() == 1


def test_outside_the_service_area_nothing_is_saved(
    api: TestClient, conn: Connection, photo_dir: Path
) -> None:
    before = conn.execute(text("SELECT count(*) FROM reporte")).scalar_one()

    response = api.post(
        REPORTS,
        data=FORM | {"longitude": "-77.2811", "latitude": "1.2136"},  # Pasto real
        files=_photo(),
        headers=bearer(_token(api)),
    )

    assert response.status_code == 422
    assert response.json()["code"] == "LOCATION_OUTSIDE_SERVICE_AREA"
    assert conn.execute(text("SELECT count(*) FROM reporte")).scalar_one() == before
    assert not photo_dir.exists() or not any(photo_dir.rglob("*.jpg"))


def test_repository_detects_a_reused_idempotency_key(conn: Connection, session: Session) -> None:
    repository = SqlReportRepository(session)
    key = uuid.uuid4()
    report = NewReport.create(
        user_id=insert_user(conn),
        location=GeoPoint(longitude=LON, latitude=LAT),
        severity=Severity.LOW,
        description=None,
        idempotency_key=key,
        service_area=BoundingBox.parse(TEST_REPORT_AREA),
    )
    report_id = repository.add(report)

    assert repository.find_by_idempotency_key(report.user_id, key) == report_id
    with pytest.raises(DuplicateIdempotencyKeyError):
        repository.add(report)


# --- Posible duplicado a 25 m (propuesta 36) -------------------------------------

# En el ecuador 1° de latitud ≈ 110 574 m.
METERS_PER_DEGREE_LAT = 110_574.0


def _insert_report_north(
    conn: Connection, meters: float, status: str = "evaluado", email: str = "otro@example.test"
) -> uuid.UUID:
    return conn.execute(
        text(
            "INSERT INTO reporte (id_usuario, ubicacion, severidad, estado) "
            "VALUES (:user_id, ST_SetSRID(ST_MakePoint(:lon, :lat), 4326), 3, "
            "CAST(:status AS estado_reporte)) RETURNING id_reporte"
        ),
        {
            "user_id": insert_user(conn, email),
            "lon": LON,
            "lat": LAT + meters / METERS_PER_DEGREE_LAT,
            "status": status,
        },
    ).scalar_one()


def _confirm(conn: Connection, report_id: uuid.UUID, emails: list[str]) -> None:
    for email in emails:
        conn.execute(
            text("INSERT INTO confirmacion (id_reporte, id_usuario) VALUES (:r, :u)"),
            {"r": report_id, "u": insert_user(conn, email)},
        )


def test_nearby_lists_only_active_reports_within_25_m(api: TestClient, conn: Connection) -> None:
    near = _insert_report_north(conn, 20.0, email="a@example.test")
    _confirm(conn, near, ["c1@example.test", "c2@example.test"])
    _insert_report_north(conn, 30.0, email="b@example.test")
    _insert_report_north(conn, 5.0, status="reparado", email="c@example.test")

    response = api.get(
        f"{REPORTS}/nearby",
        params={"longitude": LON, "latitude": LAT},
        headers=bearer(_token(api)),
    )

    assert response.status_code == 200
    items = response.json()["items"]
    assert [item["id"] for item in items] == [str(near)]
    assert items[0]["confirmations"] == 2
    # La ubicación pública es la exacta ajustada a la cuadrícula de 0,0001°, y la
    # distancia se mide desde ella: 20 m al norte quedan en 0,0002° (≈ 22,1 m).
    assert items[0]["location"] == {"longitude": LON, "latitude": 0.0002}
    assert items[0]["distance_m"] == pytest.approx(0.0002 * METERS_PER_DEGREE_LAT, abs=0.2)
    assert items[0]["severity"] == "alta"


def test_nearby_orders_from_the_closest(api: TestClient, conn: Connection) -> None:
    far = _insert_report_north(conn, 24.0, email="a@example.test")
    close = _insert_report_north(conn, 2.0, email="b@example.test")

    items = api.get(
        f"{REPORTS}/nearby",
        params={"longitude": LON, "latitude": LAT},
        headers=bearer(_token(api)),
    ).json()["items"]

    assert [item["id"] for item in items] == [str(close), str(far)]


def test_nearby_marks_the_viewers_own_reports(api: TestClient, conn: Connection) -> None:
    token = _citizen_token(api, "autor@example.com")
    author_id = conn.execute(
        text("SELECT id_usuario FROM usuario WHERE correo = 'autor@example.com'")
    ).scalar_one()
    own = insert_report(conn, author_id, LON, LAT)
    other = _insert_report_north(conn, 10.0)

    items = api.get(
        f"{REPORTS}/nearby", params={"longitude": LON, "latitude": LAT}, headers=bearer(token)
    ).json()["items"]

    assert {item["id"]: item["is_mine"] for item in items} == {str(own): True, str(other): False}


def test_report_next_to_an_active_one_answers_409_and_saves_nothing(
    api: TestClient, conn: Connection, photo_dir: Path
) -> None:
    existing = _insert_report_north(conn, 10.0)
    before = conn.execute(text("SELECT count(*) FROM reporte")).scalar_one()

    response = api.post(REPORTS, data=FORM, files=_photo(), headers=bearer(_token(api)))

    assert response.status_code == 409
    assert response.json()["code"] == "REPORT_DUPLICATE_NEARBY"
    assert [item["id"] for item in response.json()["details"]["items"]] == [str(existing)]
    assert response.json()["details"]["items"][0]["is_mine"] is False
    assert conn.execute(text("SELECT count(*) FROM reporte")).scalar_one() == before
    assert not photo_dir.exists() or not any(photo_dir.rglob("*.jpg"))


def test_create_anyway_creates_it_next_to_the_active_one(api: TestClient, conn: Connection) -> None:
    _insert_report_north(conn, 10.0)

    response = api.post(
        REPORTS,
        data=FORM | {"create_anyway": "true"},
        files=_photo(),
        headers=bearer(_token(api)),
    )

    assert response.status_code == 201


def test_a_repaired_report_nearby_is_not_a_duplicate(api: TestClient, conn: Connection) -> None:
    _insert_report_north(conn, 3.0, status="reparado")

    response = api.post(REPORTS, data=FORM, files=_photo(), headers=bearer(_token(api)))

    assert response.status_code == 201


def test_creation_lock_blocks_other_connections_until_the_transaction_ends(
    session: Session,
) -> None:
    PostgresReportCreationLock(session).acquire()

    with get_engine().connect() as other:
        acquired = other.execute(
            text("SELECT pg_try_advisory_xact_lock(:key)"), {"key": REPORT_CREATION_LOCK_KEY}
        ).scalar_one()
        other.rollback()

    assert acquired is False


# --- Servir la foto (propuesta 34) --------------------------------------------------


def _citizen_token(api: TestClient, email: str) -> str:
    register_user(api, email=email)
    return str(login_user(api, email=email)["access_token"])


def _admin_token(api: TestClient, conn: Connection) -> str:
    email = "funcionario@example.com"
    register_user(api, email=email)
    conn.execute(
        text("UPDATE usuario SET rol = 'administrador' WHERE correo = :email"), {"email": email}
    )
    return str(login_user(api, email=email)["access_token"])


def test_owner_and_admin_see_the_photo_and_others_do_not(
    api: TestClient, conn: Connection, photo_dir: Path
) -> None:
    owner = _citizen_token(api, "autora@example.com")
    report_id = api.post(REPORTS, data=FORM, files=_photo(), headers=bearer(owner)).json()["id"]
    photo_url = f"{REPORTS}/{report_id}/photo"
    stored_key = conn.execute(
        text("SELECT url_foto FROM evidencia WHERE id_reporte = :id"), {"id": report_id}
    ).scalar_one()

    own = api.get(photo_url, headers=bearer(owner))
    thumbnail = api.get(f"{photo_url}/thumbnail", headers=bearer(owner))
    by_admin = api.get(photo_url, headers=bearer(_admin_token(api, conn)))
    by_other = api.get(photo_url, headers=bearer(_citizen_token(api, "vecino@example.com")))

    assert own.status_code == 200
    assert own.content == (photo_dir / stored_key).read_bytes()
    assert open_image(own.content).format == "JPEG"
    assert thumbnail.status_code == 200
    assert len(thumbnail.content) <= len(own.content)
    assert by_admin.content == own.content
    assert by_other.status_code == 404
    assert by_other.json()["code"] == "PHOTO_NOT_FOUND"


def test_photo_of_a_report_that_does_not_exist(api: TestClient) -> None:
    response = api.get(f"{REPORTS}/{uuid.uuid4()}/photo", headers=bearer(_token(api)))

    assert response.status_code == 404


def test_after_the_titular_deletes_their_data_the_photo_is_gone_for_the_admin(
    api: TestClient, conn: Connection
) -> None:
    owner = _citizen_token(api, "autora@example.com")
    report_id = api.post(REPORTS, data=FORM, files=_photo(), headers=bearer(owner)).json()["id"]
    admin = _admin_token(api, conn)
    assert api.get(f"{REPORTS}/{report_id}/photo", headers=bearer(admin)).status_code == 200

    api.post(
        f"{API_V1_PREFIX}/me/data-deletion-requests",
        json={"current_password": PASSWORD},
        headers=bearer(owner),
    )

    assert api.get(f"{REPORTS}/{report_id}/photo", headers=bearer(admin)).status_code == 404


def test_distances_cannot_recover_the_exact_location(api: TestClient, conn: Connection) -> None:
    # Trilateración: desde tres puntos distintos, las distancias deben ser coherentes con
    # la ubicación pública, no con la exacta (propuesta 43).
    _insert_report_north(conn, 13.0)  # exacta ≈ 0,0001176°; pública 0,0001°
    token = _token(api)
    public_lat = 0.0001

    for probe_lat in (0.0, 0.00005, 0.00015):
        item = api.get(
            f"{REPORTS}/nearby",
            params={"longitude": LON, "latitude": probe_lat},
            headers=bearer(token),
        ).json()["items"][0]
        expected = abs(public_lat - probe_lat) * METERS_PER_DEGREE_LAT
        assert item["distance_m"] == pytest.approx(expected, abs=0.2)


def test_nearby_outside_the_service_area_over_http(api: TestClient) -> None:
    response = api.get(
        f"{REPORTS}/nearby",
        params={"longitude": -77.2811, "latitude": 1.2136},  # Pasto real, fuera del área de prueba
        headers=bearer(_token(api)),
    )

    assert response.status_code == 422
