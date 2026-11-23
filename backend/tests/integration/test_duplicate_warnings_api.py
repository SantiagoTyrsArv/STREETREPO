"""Registro de avisos de «Posible duplicado» contra PostGIS real (objetivo 4, sección 8.1).

Como en las demás pruebas de PostGIS, los puntos están en el Pacífico, sobre el ecuador.
"""

import uuid

import pytest
from fastapi.testclient import TestClient
from httpx import Response
from sqlalchemy import Connection, text

from app.main import API_V1_PREFIX
from tests.images import jpeg_with_metadata
from tests.integration.conftest import (
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
# Unos 4 m al nordeste del reporte existente: dentro de los 25 m y de los 50 m.
NEAR = {"longitude": LON + 0.00003, "latitude": LAT + 0.00002}
FORM = {"longitude": str(NEAR["longitude"]), "latitude": str(NEAR["latitude"]), "severity": "alta"}
ZONE_WKT = (
    f"POLYGON(({LON - 0.01} {LAT - 0.01}, {LON + 0.01} {LAT - 0.01}, "
    f"{LON + 0.01} {LAT + 0.01}, {LON - 0.01} {LAT + 0.01}, {LON - 0.01} {LAT - 0.01}))"
)


def _token(api: TestClient, email: str = "vecina@example.com") -> str:
    register_user(api, email=email)
    return str(login_user(api, email=email)["access_token"])


def _existing_report(conn: Connection, lon: float = LON, lat: float = LAT) -> uuid.UUID:
    report_id = insert_report(
        conn, insert_user(conn, f"autor-{uuid.uuid4()}@example.test"), lon, lat
    )
    conn.execute(
        text(
            "UPDATE reporte SET estado = 'evaluado', puntaje_prioridad = 7.25 WHERE id_reporte = :r"
        ),
        {"r": report_id},
    )
    return report_id


def _zone(conn: Connection) -> int:
    return conn.execute(
        text(
            "INSERT INTO zona (nombre, geom, concentracion) "
            "VALUES ('Zona de avisos', ST_GeomFromText(:wkt, 4326), 'alta') RETURNING id_zona"
        ),
        {"wkt": ZONE_WKT},
    ).scalar_one()


def _nearby(api: TestClient, token: str) -> Response:
    return api.get(f"{REPORTS}/nearby", params=NEAR, headers=bearer(token))


def _create(
    api: TestClient, token: str, extra: dict[str, str] | None = None, key: str | None = None
) -> Response:
    headers = bearer(token) | ({"Idempotency-Key": key} if key else {})
    return api.post(
        REPORTS,
        data=FORM | (extra or {}),
        files={"photo": ("IMG_0001.jpg", jpeg_with_metadata(), "image/jpeg")},
        headers=headers,
    )


def _confirm(
    api: TestClient, report_id: uuid.UUID, token: str, warning_id: object = None
) -> Response:
    body: dict[str, object] = dict(NEAR)
    if warning_id is not None:
        body["duplicate_warning_id"] = str(warning_id)
    return api.post(f"{REPORTS}/{report_id}/confirmations", json=body, headers=bearer(token))


def _warning(conn: Connection, warning_id: object) -> tuple[str, int | None, uuid.UUID | None]:
    row = conn.execute(
        text(
            "SELECT decision, id_zona, id_reporte_resultante FROM aviso_duplicado "
            "WHERE id_aviso = :w"
        ),
        {"w": str(warning_id)},
    ).one()
    return row.decision, row.id_zona, row.id_reporte_resultante


def _warnings_count(conn: Connection) -> int:
    return conn.execute(text("SELECT count(*) FROM aviso_duplicado")).scalar_one()


def test_nearby_with_candidates_records_a_pending_warning(
    api: TestClient, conn: Connection
) -> None:
    zone_id = _zone(conn)
    report_id = _existing_report(conn)

    response = _nearby(api, _token(api))

    assert response.status_code == 200
    warning_id = response.json()["duplicate_warning_id"]
    assert warning_id is not None
    assert _warning(conn, warning_id) == ("pendiente", zone_id, None)
    candidates = conn.execute(
        text("SELECT id_reporte, distancia_m FROM aviso_duplicado_candidato WHERE id_aviso = :w"),
        {"w": warning_id},
    ).all()
    assert [row.id_reporte for row in candidates] == [report_id]
    # Distancia exacta desde el reporte (unos 4 m), no desde su ubicación pública.
    assert 3.0 < float(candidates[0].distancia_m) < 5.0


def test_a_warning_outside_every_zone_has_no_zone(api: TestClient, conn: Connection) -> None:
    _existing_report(conn)

    warning_id = _nearby(api, _token(api)).json()["duplicate_warning_id"]

    assert _warning(conn, warning_id) == ("pendiente", None, None)


def test_nearby_without_candidates_records_nothing(api: TestClient, conn: Connection) -> None:
    response = _nearby(api, _token(api))

    assert response.json()["duplicate_warning_id"] is None
    assert _warnings_count(conn) == 0


def test_the_409_records_a_warning_and_returns_its_id(api: TestClient, conn: Connection) -> None:
    _existing_report(conn)

    response = _create(api, _token(api))

    assert response.status_code == 409
    warning_id = response.json()["details"]["duplicate_warning_id"]
    assert _warning(conn, warning_id)[0] == "pendiente"


def test_creating_anyway_with_the_warning_marks_it_created_anyway(
    api: TestClient, conn: Connection
) -> None:
    _existing_report(conn)
    token = _token(api)
    warning_id = _create(api, token).json()["details"]["duplicate_warning_id"]

    response = _create(api, token, {"create_anyway": "true", "duplicate_warning_id": warning_id})

    assert response.status_code == 201
    decision, _, resulting = _warning(conn, warning_id)
    assert (decision, str(resulting)) == ("creo_igual", response.json()["id"])


def test_confirming_from_the_warning_marks_it_confirmed(api: TestClient, conn: Connection) -> None:
    report_id = _existing_report(conn)
    token = _token(api)
    warning_id = _nearby(api, token).json()["duplicate_warning_id"]

    response = _confirm(api, report_id, token, warning_id)

    assert response.status_code == 201
    assert _warning(conn, warning_id) == ("confirmo", None, report_id)


def test_a_warning_of_another_user_is_left_untouched(api: TestClient, conn: Connection) -> None:
    report_id = _existing_report(conn)
    warning_id = _nearby(api, _token(api, "otra@example.com")).json()["duplicate_warning_id"]

    response = _confirm(api, report_id, _token(api), warning_id)

    assert response.status_code == 201
    assert _warning(conn, warning_id)[0] == "pendiente"


def test_confirming_a_report_that_was_not_a_candidate_leaves_the_warning(
    api: TestClient, conn: Connection
) -> None:
    _existing_report(conn)
    token = _token(api)
    warning_id = _nearby(api, token).json()["duplicate_warning_id"]
    # Otro reporte a unos 44 m: confirmable (≤ 50 m) pero fuera de los 25 m del aviso.
    other = _existing_report(conn, lat=LAT + 0.0004)

    response = _confirm(api, other, token, warning_id)

    assert response.status_code == 201
    assert _warning(conn, warning_id)[0] == "pendiente"


def test_a_resolved_warning_does_not_change_again(api: TestClient, conn: Connection) -> None:
    _existing_report(conn)
    token = _token(api)
    warning_id = _create(api, token).json()["details"]["duplicate_warning_id"]
    extra = {"create_anyway": "true", "duplicate_warning_id": warning_id}
    first = _create(api, token, extra)

    second = _create(api, token, extra)

    assert second.status_code == 201
    assert str(_warning(conn, warning_id)[2]) == first.json()["id"]


def test_an_unknown_warning_id_does_not_stop_the_confirmation(
    api: TestClient, conn: Connection
) -> None:
    report_id = _existing_report(conn)

    response = _confirm(api, report_id, _token(api), uuid.uuid4())

    assert response.status_code == 201


def test_an_idempotent_retry_does_not_record_new_warnings(
    api: TestClient, conn: Connection
) -> None:
    token = _token(api)
    key = str(uuid.uuid4())
    created = _create(api, token, key=key)
    assert created.status_code == 201
    # Ahora hay un reporte activo a 0 m del punto del reintento.

    retry = _create(api, token, key=key)

    assert retry.status_code == 200
    assert _warnings_count(conn) == 0


def test_the_warning_keeps_the_point_out_of_the_database(api: TestClient, conn: Connection) -> None:
    _existing_report(conn)
    _nearby(api, _token(api))

    columns = (
        conn.execute(
            text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name IN ('aviso_duplicado', 'aviso_duplicado_candidato')"
            )
        )
        .scalars()
        .all()
    )

    # Minimización (guía 7.2): ni el punto consultado ni su geometría se guardan.
    assert not {"ubicacion", "geom", "lon", "lat"} & set(columns)
