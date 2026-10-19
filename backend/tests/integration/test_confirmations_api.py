"""POST /api/v1/reports/{id}/confirmations por HTTP contra PostGIS real (HU-16, propuesta 48)."""

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


def _confirm(api: TestClient, report_id: uuid.UUID, token: str) -> Response:
    return api.post(f"{REPORTS}/{report_id}/confirmations", headers=bearer(token))


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
    response = api.post(f"{REPORTS}/{_report(conn)}/confirmations")

    assert response.status_code == 401
