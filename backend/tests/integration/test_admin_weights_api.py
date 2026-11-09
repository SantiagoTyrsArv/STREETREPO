"""GET/PUT /api/v1/admin/weights y GET /admin/weights/versions contra PostGIS (HU-14)."""

from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from httpx import Response
from sqlalchemy import Connection, text

from app.modules.reports.domain.status import ReportStatus
from tests.integration.conftest import bearer, insert_user, requires_db
from tests.integration.test_admin_dashboard_api import (
    ADMIN,
    _admin_token,
    _citizen_token,
)

pytestmark = [pytest.mark.integration, requires_db]

WEIGHTS = f"{ADMIN}/weights"
NEW = {"w_severity": "0.40", "w_flow": "0.40", "w_proximity": "0.20"}


def _current(api: TestClient, token: str) -> dict[str, object]:
    response = api.get(WEIGHTS, headers=bearer(token))
    assert response.status_code == 200, response.json()
    body: dict[str, object] = response.json()
    return body


def _put(api: TestClient, token: str, base: object, **weights: object) -> Response:
    return api.put(
        WEIGHTS, json={"base_version_id": base} | (weights or NEW), headers=bearer(token)
    )


def _report(conn: Connection, status: ReportStatus) -> object:
    """Reporte sin vía ni servicios cerca (S = 10, F = 2, P = 0) con su evaluación inicial."""
    report_id = conn.execute(
        text(
            "INSERT INTO reporte (id_usuario, ubicacion, severidad, estado, puntaje_prioridad) "
            "VALUES (:autor, ST_SetSRID(ST_MakePoint(-80, 0), 4326), 3, "
            "CAST(:estado AS estado_reporte), 5.60) RETURNING id_reporte"
        ),
        {"autor": insert_user(conn, email=f"{status.value}@example.test"), "estado": status.value},
    ).scalar_one()
    conn.execute(
        text(
            "INSERT INTO evaluacion_prioridad (id_reporte, id_config, s_severidad, f_flujo, "
            "p_proximidad, u_utilidad) "
            "SELECT :r, id_config, 10, 2, 0, 5.60 FROM configuracion_pesos WHERE vigente"
        ),
        {"r": report_id},
    )
    return report_id


def _evaluations(conn: Connection, report_id: object) -> list[tuple[Decimal, int]]:
    rows = conn.execute(
        text(
            "SELECT u_utilidad, id_config FROM evaluacion_prioridad WHERE id_reporte = :r "
            "ORDER BY id_evaluacion"
        ),
        {"r": report_id},
    ).all()
    return [(row.u_utilidad, row.id_config) for row in rows]


def test_get_current_weights(api: TestClient, conn: Connection) -> None:
    token = _admin_token(api, conn)

    body = _current(api, token)

    assert (body["w_severity"], body["w_flow"], body["w_proximity"]) == (0.5, 0.3, 0.2)
    assert body["created_by_name"] is None
    assert body["is_current"] is True
    assert isinstance(body["id"], int)


def test_get_weights_without_current_version_is_404(api: TestClient, conn: Connection) -> None:
    token = _admin_token(api, conn)
    conn.execute(text("UPDATE configuracion_pesos SET vigente = false"))

    response = api.get(WEIGHTS, headers=bearer(token))

    assert response.status_code == 404
    assert response.json()["code"] == "WEIGHTS_NOT_CONFIGURED"


def test_put_weights_recalculates_active_reports(api: TestClient, conn: Connection) -> None:
    token = _admin_token(api, conn)
    base = _current(api, token)["id"]
    active = _report(conn, ReportStatus.PRIORITIZED)
    repaired = _report(conn, ReportStatus.REPAIRED)

    response = _put(api, token, base)

    assert response.status_code == 200, response.json()
    body = response.json()
    version = body["version"]
    assert body["recalculated_reports"] == 1
    assert version["id"] != base
    assert (version["w_severity"], version["w_flow"], version["w_proximity"]) == (0.4, 0.4, 0.2)
    assert version["created_by_name"] == "Ana Pérez"
    assert version["is_current"] is True
    # 0,4·10 + 0,4·2 + 0,2·0 = 4,80 con la versión nueva; el reparado no se recalcula.
    assert _evaluations(conn, active)[-1] == (Decimal("4.80"), version["id"])
    assert len(_evaluations(conn, repaired)) == 1
    assert _current(api, token)["id"] == version["id"]


def test_put_weights_accepts_json_numbers(api: TestClient, conn: Connection) -> None:
    token = _admin_token(api, conn)
    base = _current(api, token)["id"]

    response = _put(api, token, base, w_severity=0.6, w_flow=0.3, w_proximity=0.1)

    assert response.status_code == 200, response.json()
    assert response.json()["version"]["w_severity"] == 0.6


@pytest.mark.parametrize(
    ("weights", "fragment"),
    [
        ({"w_severity": "0.50", "w_flow": "0.30", "w_proximity": "0.19"}, "sumar 1,00"),
        ({"w_severity": "0.505", "w_flow": "0.30", "w_proximity": "0.195"}, "dos decimales"),
        ({"w_severity": 0.505, "w_flow": 0.3, "w_proximity": 0.195}, "dos decimales"),
        ({"w_severity": "1.20", "w_flow": "-0.10", "w_proximity": "-0.10"}, "entre 0 y 1"),
    ],
)
def test_put_invalid_weights_is_422(
    api: TestClient, conn: Connection, weights: dict[str, object], fragment: str
) -> None:
    token = _admin_token(api, conn)
    base = _current(api, token)["id"]

    response = _put(api, token, base, **weights)

    assert response.status_code == 422
    assert response.json()["code"] == "INVALID_WEIGHTS"
    assert fragment in response.json()["message"]
    assert _current(api, token)["id"] == base


@pytest.mark.parametrize(
    "body",
    [
        {"w_severity": "0.50", "w_flow": "0.30", "w_proximity": "0.20"},
        {"base_version_id": 1, "w_severity": "0,50", "w_flow": "0.30", "w_proximity": "0.20"},
        {"base_version_id": 1, "w_severity": "NaN", "w_flow": "0.30", "w_proximity": "0.20"},
    ],
)
def test_put_malformed_body_is_422(
    api: TestClient, conn: Connection, body: dict[str, object]
) -> None:
    token = _admin_token(api, conn)

    assert api.put(WEIGHTS, json=body, headers=bearer(token)).status_code == 422


def test_put_weights_stale_base_is_409(api: TestClient, conn: Connection) -> None:
    token = _admin_token(api, conn)
    base = _current(api, token)["id"]
    newer = _put(api, token, base).json()["version"]["id"]

    response = _put(api, token, base, w_severity="0.60", w_flow="0.20", w_proximity="0.20")

    assert response.status_code == 409
    assert response.json()["code"] == "WEIGHTS_VERSION_CONFLICT"
    assert response.json()["details"] == {"current_version_id": newer}
    assert _current(api, token)["id"] == newer


def test_versions_newest_first(api: TestClient, conn: Connection) -> None:
    token = _admin_token(api, conn)
    first = _current(api, token)["id"]
    second = _put(api, token, first).json()["version"]["id"]
    third = _put(api, token, second, w_severity="0.60", w_flow="0.20", w_proximity="0.20").json()[
        "version"
    ]["id"]

    response = api.get(f"{WEIGHTS}/versions?limit=3", headers=bearer(token))

    assert response.status_code == 200
    body = response.json()
    assert [item["id"] for item in body["items"]] == [third, second, first]
    assert [item["is_current"] for item in body["items"]] == [True, False, False]
    assert (body["limit"], body["offset"]) == (3, 0)
    paged = api.get(f"{WEIGHTS}/versions?limit=1&offset=1", headers=bearer(token)).json()
    assert [item["id"] for item in paged["items"]] == [second]


def test_versions_limit_over_100_is_422(api: TestClient, conn: Connection) -> None:
    token = _admin_token(api, conn)

    assert api.get(f"{WEIGHTS}/versions?limit=101", headers=bearer(token)).status_code == 422


def test_weights_routes_require_admin(api: TestClient) -> None:
    citizen = _citizen_token(api)

    assert api.get(WEIGHTS, headers=bearer(citizen)).status_code == 403
    assert api.get(f"{WEIGHTS}/versions", headers=bearer(citizen)).status_code == 403
    assert _put(api, citizen, 1).status_code == 403
    assert api.get(WEIGHTS).status_code == 401
