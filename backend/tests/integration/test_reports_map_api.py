"""GET /api/v1/reports por HTTP contra PostGIS real: mapa de reportes de la app."""

import uuid

import pytest
from fastapi.testclient import TestClient
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
AREA = "-80.01,-0.01,-79.99,0.01"
ME_EMAIL = "yo@example.com"


def _token(api: TestClient, email: str = ME_EMAIL) -> str:
    register_user(api, email=email)
    return str(login_user(api, email=email)["access_token"])


def _user_id(conn: Connection, email: str) -> uuid.UUID:
    return conn.execute(
        text("SELECT id_usuario FROM usuario WHERE correo = :email"), {"email": email}
    ).scalar_one()


def _report(
    conn: Connection,
    user_id: uuid.UUID,
    lon: float = LON,
    lat: float = LAT,
    *,
    created_at: str = "2026-10-10T10:00:00Z",
    status: str | None = None,
) -> uuid.UUID:
    report_id = insert_report(conn, user_id, lon, lat)
    conn.execute(
        text("UPDATE reporte SET fecha_creacion = CAST(:f AS timestamptz) WHERE id_reporte = :r"),
        {"f": created_at, "r": report_id},
    )
    if status is not None:
        conn.execute(
            text("UPDATE reporte SET estado = CAST(:e AS estado_reporte) WHERE id_reporte = :r"),
            {"e": status, "r": report_id},
        )
    return report_id


def _ids(api: TestClient, token: str, **params: object) -> list[str]:
    response = api.get(REPORTS, params={"bbox": AREA} | params, headers=bearer(token))
    assert response.status_code == 200, response.text
    return [item["id"] for item in response.json()["items"]]


def test_lists_reports_of_any_citizen_inside_the_area_newest_first(
    api: TestClient, conn: Connection
) -> None:
    token = _token(api)
    other = insert_user(conn, "otra@example.test")
    old = _report(conn, other, created_at="2026-10-01T10:00:00Z")
    new = _report(conn, _user_id(conn, ME_EMAIL), LON + 0.001, created_at="2026-10-05T10:00:00Z")
    _report(conn, other, LON + 0.5, LAT)  # fuera del área

    assert _ids(api, token) == [str(new), str(old)]


def test_items_are_the_public_view_without_author_description_or_exact_location(
    api: TestClient, conn: Connection
) -> None:
    token = _token(api)
    other = insert_user(conn, "otra@example.test")
    report = _report(conn, other, LON + 0.000037, LAT + 0.000012)
    conn.execute(
        text("UPDATE reporte SET descripcion = 'Frente a la casa de Ana' WHERE id_reporte = :r"),
        {"r": report},
    )

    body = api.get(REPORTS, params={"bbox": AREA}, headers=bearer(token)).json()

    assert body["limit"] == 200
    assert body["truncated"] is False
    assert body["items"] == [
        {
            "id": str(report),
            "location": {"longitude": -80.0, "latitude": 0.0},
            "status": "registrado",
            "severity": "media",
            "address": "Sin vía asociada",
            "confirmations": 0,
            "created_at": "2026-10-10T10:00:00Z",
            "is_mine": False,
            "confirmed_by_me": False,
        }
    ]


def test_marks_own_and_confirmed_reports(api: TestClient, conn: Connection) -> None:
    token = _token(api)
    me = _user_id(conn, ME_EMAIL)
    other = insert_user(conn, "otra@example.test")
    mine = _report(conn, me, created_at="2026-10-03T10:00:00Z")
    confirmed = _report(conn, other, LON + 0.001, created_at="2026-10-02T10:00:00Z")
    _report(conn, other, LON + 0.002, created_at="2026-10-01T10:00:00Z")
    conn.execute(
        text("INSERT INTO confirmacion (id_reporte, id_usuario) VALUES (:r, :u)"),
        {"r": confirmed, "u": me},
    )

    items = api.get(REPORTS, params={"bbox": AREA}, headers=bearer(token)).json()["items"]

    assert [(i["is_mine"], i["confirmed_by_me"], i["confirmations"]) for i in items] == [
        (True, False, 0),
        (False, True, 1),
        (False, False, 0),
    ]
    assert items[0]["id"] == str(mine)


def test_filters_by_status_and_includes_repaired_reports(api: TestClient, conn: Connection) -> None:
    token = _token(api)
    other = insert_user(conn, "otra@example.test")
    repaired = _report(conn, other, status="reparado", created_at="2026-10-02T10:00:00Z")
    registered = _report(conn, other, LON + 0.001, created_at="2026-10-01T10:00:00Z")

    assert _ids(api, token) == [str(repaired), str(registered)]
    assert _ids(api, token, status="reparado") == [str(repaired)]
    assert _ids(api, token, status="priorizado") == []


def test_limit_truncates_and_says_so(api: TestClient, conn: Connection) -> None:
    token = _token(api)
    other = insert_user(conn, "otra@example.test")
    _report(conn, other, created_at="2026-10-01T10:00:00Z")
    newest = _report(conn, other, LON + 0.001, created_at="2026-10-02T10:00:00Z")

    body = api.get(REPORTS, params={"bbox": AREA, "limit": 1}, headers=bearer(token)).json()

    assert [item["id"] for item in body["items"]] == [str(newest)]
    assert (body["limit"], body["truncated"]) == (1, True)


def test_the_area_is_compared_with_the_public_location_not_the_exact_one(
    api: TestClient, conn: Connection
) -> None:
    """Con rectángulos cada vez más pequeños no se puede acotar la ubicación exacta.

    El reporte está en -79.99996 (exacta), que en público se muestra como -80.0.
    """
    token = _token(api)
    report = _report(conn, insert_user(conn, "otra@example.test"), LON + 0.00004, LAT)

    def ids(bbox: str) -> list[str]:
        response = api.get(REPORTS, params={"bbox": bbox}, headers=bearer(token))
        return [item["id"] for item in response.json()["items"]]

    # Contiene la ubicación exacta pero no la pública: no aparece.
    assert ids("-79.99998,-0.01,-79.99,0.01") == []
    # Contiene la pública pero no la exacta: aparece.
    assert ids("-80.01,-0.01,-79.99999,0.01") == [str(report)]


def test_requires_a_session(api: TestClient) -> None:
    assert api.get(REPORTS, params={"bbox": AREA}).status_code == 401
