"""GET /api/v1/reports/{id} por HTTP contra PostGIS real (decisión 49)."""

import uuid

import pytest
from fastapi.testclient import TestClient
from httpx import Response
from sqlalchemy import Connection, text

from app.main import API_V1_PREFIX
from tests.integration.conftest import (
    bearer,
    login_user,
    register_user,
    requires_db,
)
from tests.integration.test_reports_api import FORM, _photo

pytestmark = [pytest.mark.integration, requires_db]

REPORTS = f"{API_V1_PREFIX}/reports"
NOTE = "Cuadrilla asignada; avisar a la señora Pérez"


def _token(api: TestClient, email: str) -> str:
    register_user(api, email=email)
    return str(login_user(api, email=email)["access_token"])


def _create_report(api: TestClient, token: str) -> uuid.UUID:
    response = api.post(REPORTS, data=FORM, files=_photo(), headers=bearer(token))
    assert response.status_code == 201
    return uuid.UUID(response.json()["id"])


def _prioritize_with_note(conn: Connection, report_id: uuid.UUID) -> None:
    conn.execute(
        text("UPDATE reporte SET estado = 'priorizado' WHERE id_reporte = :r"), {"r": report_id}
    )
    conn.execute(
        text(
            "INSERT INTO historial_estado (id_reporte, estado_anterior, estado_nuevo, observacion) "
            "VALUES (:r, 'evaluado', 'priorizado', :nota)"
        ),
        {"r": report_id, "nota": NOTE},
    )


def _detail(api: TestClient, report_id: object, token: str) -> Response:
    return api.get(f"{REPORTS}/{report_id}", headers=bearer(token))


def test_author_sees_history_registered_then_evaluated(api: TestClient) -> None:
    token = _token(api, "autora@example.com")
    report_id = _create_report(api, token)

    body = _detail(api, report_id, token).json()

    assert body["relation"] == "own"
    assert body["id"] == str(report_id)
    assert body["confirmations"] == 0
    assert [entry["status"] for entry in body["history"]] == ["registrado", "evaluado"]


def test_confirmer_sees_limited_view_and_notes_are_hidden(
    api: TestClient, conn: Connection
) -> None:
    author = _token(api, "autora@example.com")
    report_id = _create_report(api, author)
    _prioritize_with_note(conn, report_id)
    confirmer = _token(api, "vecino@example.com")
    assert (
        api.post(f"{REPORTS}/{report_id}/confirmations", headers=bearer(confirmer)).status_code
        == 201
    )

    limited = _detail(api, report_id, confirmer).json()
    full = _detail(api, report_id, author).json()

    assert limited["relation"] == "confirmed"
    assert limited["confirmations"] == 1
    assert "description" not in limited
    assert "confirmed_at" in limited
    assert [entry["note"] for entry in limited["history"]] == [None, None, None]
    assert full["history"][-1]["note"] == NOTE


def test_admin_who_confirmed_gets_the_full_view_as_staff(api: TestClient, conn: Connection) -> None:
    report_id = _create_report(api, _token(api, "autora@example.com"))
    _token(api, "funcionario@example.com")
    conn.execute(
        text("UPDATE usuario SET rol = 'administrador' WHERE correo = 'funcionario@example.com'")
    )
    admin = str(login_user(api, email="funcionario@example.com")["access_token"])
    assert (
        api.post(f"{REPORTS}/{report_id}/confirmations", headers=bearer(admin)).status_code == 201
    )

    body = _detail(api, report_id, admin).json()

    assert body["relation"] == "staff"
    assert "description" in body
    assert [entry["status"] for entry in body["history"]] == ["registrado", "evaluado"]


def test_stranger_gets_404_like_a_missing_report(api: TestClient) -> None:
    report_id = _create_report(api, _token(api, "autora@example.com"))
    stranger = _token(api, "extrano@example.com")

    hidden = _detail(api, report_id, stranger)
    missing = _detail(api, uuid.uuid4(), stranger)

    assert hidden.status_code == missing.status_code == 404
    assert hidden.json() == missing.json()
    assert hidden.json()["code"] == "REPORT_NOT_FOUND"


def test_non_uuid_id_is_422(api: TestClient) -> None:
    response = _detail(api, "abc", _token(api, "autora@example.com"))

    assert response.status_code == 422
