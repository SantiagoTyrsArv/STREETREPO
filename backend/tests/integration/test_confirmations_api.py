"""POST /api/v1/reports/{id}/confirmations contra PostGIS real (HU-16, propuestas 48 y 112)."""

import uuid

import pytest
from fastapi.testclient import TestClient
from httpx import Response
from sqlalchemy import Connection, text

from app.main import API_V1_PREFIX
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
# Unos 4 m al nordeste del reporte: quien confirma está frente al daño.
NEAR = {"longitude": LON + 0.00003, "latitude": LAT + 0.00002}
# 0,0006° de latitud son unos 66 m: fuera del radio de 50 m.
FAR = {"longitude": LON, "latitude": LAT + 0.0006}
# 0,0004° de latitud son unos 44 m: dentro del radio.
EDGE = {"longitude": LON, "latitude": LAT + 0.0004}


def _token(api: TestClient, email: str = "vecina@example.com") -> str:
    register_user(api, email=email)
    return str(login_user(api, email=email)["access_token"])


def _user_id(conn: Connection, email: str) -> uuid.UUID:
    return conn.execute(
        text("SELECT id_usuario FROM usuario WHERE correo = :email"), {"email": email}
    ).scalar_one()


def _report(conn: Connection, status: str = "evaluado") -> uuid.UUID:
    report_id = insert_report(conn, insert_user(conn, "autor@example.test"), LON, LAT)
    conn.execute(
        text(
            "UPDATE reporte SET estado = CAST(:s AS estado_reporte), puntaje_prioridad = 7.25 "
            "WHERE id_reporte = :r"
        ),
        {"s": status, "r": report_id},
    )
    return report_id


def _confirm(
    api: TestClient,
    report_id: uuid.UUID,
    token: str,
    where: dict[str, float] | None = None,
) -> Response:
    return api.post(
        f"{REPORTS}/{report_id}/confirmations",
        json=NEAR if where is None else where,
        headers=bearer(token),
    )


def _stored_distance(conn: Connection, report_id: uuid.UUID) -> float | None:
    value = conn.execute(
        text("SELECT distancia_m FROM confirmacion WHERE id_reporte = :r"), {"r": report_id}
    ).scalar_one_or_none()
    return None if value is None else float(value)


def test_a_citizen_confirms_another_citizens_report(api: TestClient, conn: Connection) -> None:
    report_id = _report(conn)

    response = _confirm(api, report_id, _token(api))

    assert response.status_code == 201
    assert response.json() == {"report_id": str(report_id), "confirmations": 1}
    rows = conn.execute(
        text("SELECT count(*) FROM confirmacion WHERE id_reporte = :r"), {"r": report_id}
    ).scalar_one()
    assert rows == 1
    # La confirmación no cambia la urgencia U (guía 2.2).
    score = conn.execute(
        text("SELECT puntaje_prioridad FROM reporte WHERE id_reporte = :r"), {"r": report_id}
    ).scalar_one()
    assert float(score) == 7.25


def test_double_tap_answers_409_not_500(api: TestClient, conn: Connection) -> None:
    report_id = _report(conn)
    token = _token(api)

    first = _confirm(api, report_id, token)
    second = _confirm(api, report_id, token)

    assert first.status_code == 201
    assert second.status_code == 409
    assert second.json()["code"] == "CONFIRMATION_ALREADY_EXISTS"


def test_author_gets_409_own_report(api: TestClient, conn: Connection) -> None:
    token = _token(api, "autora@example.com")
    report_id = insert_report(conn, _user_id(conn, "autora@example.com"), LON, LAT)

    response = _confirm(api, report_id, token)

    assert response.status_code == 409
    assert response.json()["code"] == "CONFIRMATION_OWN_REPORT"


def test_repaired_report_gets_409_not_active(api: TestClient, conn: Connection) -> None:
    response = _confirm(api, _report(conn, status="reparado"), _token(api))

    assert response.status_code == 409
    assert response.json()["code"] == "REPORT_NOT_ACTIVE"


def test_unknown_report_gets_404(api: TestClient) -> None:
    response = _confirm(api, uuid.uuid4(), _token(api))

    assert response.status_code == 404
    assert response.json()["code"] == "REPORT_NOT_FOUND"


def test_confirmation_without_token_is_401(api: TestClient, conn: Connection) -> None:
    response = api.post(f"{REPORTS}/{_report(conn)}/confirmations", json=NEAR)

    assert response.status_code == 401


def test_confirmation_saves_the_distance_to_the_damage(api: TestClient, conn: Connection) -> None:
    report_id = _report(conn)

    assert _confirm(api, report_id, _token(api)).status_code == 201

    distance = _stored_distance(conn, report_id)
    assert distance is not None
    assert 3.0 < distance < 5.0


def test_confirmation_within_the_radius_is_accepted(api: TestClient, conn: Connection) -> None:
    report_id = _report(conn)

    response = _confirm(api, report_id, _token(api), EDGE)

    assert response.status_code == 201


def test_confirmation_from_far_away_is_403_and_saves_nothing(
    api: TestClient, conn: Connection
) -> None:
    report_id = _report(conn)

    response = _confirm(api, report_id, _token(api), FAR)

    assert response.status_code == 403
    body = response.json()
    assert body["code"] == "CONFIRMATION_TOO_FAR"
    # Solo el radio, nunca la distancia exacta (propuesta 43).
    assert body["details"] == {"max_distance_m": 50.0}
    assert _stored_distance(conn, report_id) is None


def test_confirmation_without_location_is_422(api: TestClient, conn: Connection) -> None:
    response = api.post(f"{REPORTS}/{_report(conn)}/confirmations", headers=bearer(_token(api)))

    assert response.status_code == 422


def test_confirmation_with_invalid_latitude_is_422(api: TestClient, conn: Connection) -> None:
    response = _confirm(api, _report(conn), _token(api), {"longitude": LON, "latitude": 91.0})

    assert response.status_code == 422


def test_an_evaluator_cannot_confirm_reports(api: TestClient, conn: Connection) -> None:
    report_id = _report(conn)
    token = _token(api)
    conn.execute(text("UPDATE usuario SET rol = 'evaluador' WHERE correo = 'vecina@example.com'"))

    response = _confirm(api, report_id, token)

    assert response.status_code == 403
    assert response.json()["code"] == "EVALUATOR_CANNOT_REPORT"
    rows = conn.execute(
        text("SELECT count(*) FROM confirmacion WHERE id_reporte = :r"), {"r": report_id}
    ).scalar_one()
    assert rows == 0
