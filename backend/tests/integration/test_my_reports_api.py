"""GET /api/v1/me/reports por HTTP contra PostGIS real (decisión 49)."""

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Connection, text

from app.main import API_V1_PREFIX
from tests.integration.conftest import (
    PASSWORD,
    bearer,
    insert_report,
    insert_user,
    login_user,
    register_user,
    requires_db,
)

pytestmark = [pytest.mark.integration, requires_db]

MY_REPORTS = f"{API_V1_PREFIX}/me/reports"
REPORTS = f"{API_V1_PREFIX}/reports"
LON, LAT = -80.0, 0.0
ME_EMAIL = "yo@example.com"


def _token(api: TestClient, email: str = ME_EMAIL) -> str:
    register_user(api, email=email)
    return str(login_user(api, email=email)["access_token"])


def _user_id(conn: Connection, email: str) -> uuid.UUID:
    return conn.execute(
        text("SELECT id_usuario FROM usuario WHERE correo = :email"), {"email": email}
    ).scalar_one()


def _report_at(conn: Connection, user_id: uuid.UUID, created_at: str) -> uuid.UUID:
    report_id = insert_report(conn, user_id, LON + 0.000037, LAT + 0.000012)
    conn.execute(
        text("UPDATE reporte SET fecha_creacion = CAST(:f AS timestamptz) WHERE id_reporte = :r"),
        {"f": created_at, "r": report_id},
    )
    return report_id


def _confirm_at(conn: Connection, report_id: uuid.UUID, user_id: uuid.UUID, at: str) -> None:
    conn.execute(
        text(
            "INSERT INTO confirmacion (id_reporte, id_usuario, fecha) "
            "VALUES (:r, :u, CAST(:f AS timestamptz))"
        ),
        {"r": report_id, "u": user_id, "f": at},
    )


def test_lists_own_and_confirmed_reports_newest_first(api: TestClient, conn: Connection) -> None:
    token = _token(api)
    me = _user_id(conn, ME_EMAIL)
    own = _report_at(conn, me, "2026-10-10T10:00:00Z")
    other = _report_at(conn, insert_user(conn, "otra@example.test"), "2026-10-01T10:00:00Z")
    _confirm_at(conn, other, me, "2026-10-12T10:00:00Z")

    body = api.get(MY_REPORTS, headers=bearer(token)).json()

    assert body["total"] == 2
    assert [(i["relation"], i["id"]) for i in body["items"]] == [
        ("confirmed", str(other)),
        ("own", str(own)),
    ]
    assert body["items"][0]["confirmed_at"] == "2026-10-12T10:00:00Z"
    assert body["items"][0]["confirmations"] == 1
    assert body["items"][1]["confirmations"] == 0


def test_confirmed_items_hide_exact_location_author_and_description(
    api: TestClient, conn: Connection
) -> None:
    token = _token(api)
    other = _report_at(conn, insert_user(conn, "otra@example.test"), "2026-10-01T10:00:00Z")
    conn.execute(
        text("UPDATE reporte SET descripcion = 'Frente a la casa de Ana' WHERE id_reporte = :r"),
        {"r": other},
    )
    _confirm_at(conn, other, _user_id(conn, ME_EMAIL), "2026-10-12T10:00:00Z")

    item = api.get(MY_REPORTS, headers=bearer(token)).json()["items"][0]

    assert item["location"] == {"longitude": -80.0, "latitude": 0.0}
    for hidden in ("description", "priority_score", "user_id", "needs_road_review"):
        assert hidden not in item


def test_own_items_keep_the_exact_location(api: TestClient, conn: Connection) -> None:
    token = _token(api)
    _report_at(conn, _user_id(conn, ME_EMAIL), "2026-10-10T10:00:00Z")

    item = api.get(MY_REPORTS, headers=bearer(token)).json()["items"][0]

    assert item["location"] == {"longitude": LON + 0.000037, "latitude": LAT + 0.000012}
    assert "description" in item


def test_other_citizens_reports_are_not_listed(api: TestClient, conn: Connection) -> None:
    token = _token(api)
    _report_at(conn, insert_user(conn, "otra@example.test"), "2026-10-01T10:00:00Z")

    body = api.get(MY_REPORTS, headers=bearer(token)).json()

    assert body == {"items": [], "total": 0, "limit": 20, "offset": 0}


def test_offset_past_the_end_returns_empty_items_with_total(
    api: TestClient, conn: Connection
) -> None:
    token = _token(api)
    me = _user_id(conn, ME_EMAIL)
    _report_at(conn, me, "2026-10-10T10:00:00Z")
    _report_at(conn, me, "2026-10-11T10:00:00Z")

    body = api.get(MY_REPORTS, params={"offset": 10}, headers=bearer(token)).json()

    assert body["items"] == []
    assert body["total"] == 2


def test_limit_pages_the_list(api: TestClient, conn: Connection) -> None:
    token = _token(api)
    me = _user_id(conn, ME_EMAIL)
    _report_at(conn, me, "2026-10-10T10:00:00Z")
    newest = _report_at(conn, me, "2026-10-11T10:00:00Z")

    body = api.get(MY_REPORTS, params={"limit": 1}, headers=bearer(token)).json()

    assert [i["id"] for i in body["items"]] == [str(newest)]
    assert (body["total"], body["limit"]) == (2, 1)


def test_limit_above_50_is_422(api: TestClient) -> None:
    response = api.get(MY_REPORTS, params={"limit": 51}, headers=bearer(_token(api)))

    assert response.status_code == 422


def test_my_reports_requires_a_session(api: TestClient) -> None:
    assert api.get(MY_REPORTS).status_code == 401


def test_confirmation_by_a_deleted_user_still_counts(api: TestClient, conn: Connection) -> None:
    author_token = _token(api, "autora@example.com")
    report_id = _report_at(conn, _user_id(conn, "autora@example.com"), "2026-10-10T10:00:00Z")
    confirmer_token = _token(api, "vecino@example.com")
    assert (
        api.post(
            f"{REPORTS}/{report_id}/confirmations", headers=bearer(confirmer_token)
        ).status_code
        == 201
    )
    deletion = api.post(
        f"{API_V1_PREFIX}/me/data-deletion-requests",
        json={"current_password": PASSWORD},
        headers=bearer(confirmer_token),
    )
    assert deletion.status_code == 201

    item = api.get(MY_REPORTS, headers=bearer(author_token)).json()["items"][0]

    assert item["confirmations"] == 1
