"""PATCH /api/v1/admin/reports/{id}/status contra PostGIS real (HU-12)."""

import uuid

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
    _evaluated,
)

pytestmark = [pytest.mark.integration, requires_db]

NOTE = "Cuadrilla asignada para el lunes"


def _patch(api: TestClient, token: str, report_id: object, **body: object) -> Response:
    return api.patch(f"{ADMIN}/reports/{report_id}/status", json=body, headers=bearer(token))


def _stored_status(conn: Connection, report_id: uuid.UUID) -> tuple[str, str]:
    row = conn.execute(
        text("SELECT estado, puntaje_prioridad FROM reporte WHERE id_reporte = :r"),
        {"r": report_id},
    ).one()
    return str(row.estado), str(row.puntaje_prioridad)


def test_patch_status_evaluated_to_prioritized(api: TestClient, conn: Connection) -> None:
    token = _admin_token(api, conn)
    report_id = _evaluated(conn, insert_user(conn), urgency="7.25")

    response = _patch(api, token, report_id, status="priorizado", note=f"  {NOTE}  ")

    assert response.status_code == 200, response.json()
    body = response.json()
    assert body["id"] == str(report_id)
    assert body["status"] == "priorizado"
    assert body["allowed_next_statuses"] == ["reparado"]
    assert body["history"][-1] == {
        "previous_status": "evaluado",
        "status": "priorizado",
        "changed_at": body["history"][-1]["changed_at"],
        "note": NOTE,
        "changed_by_name": "Ana Pérez",
    }
    assert _stored_status(conn, report_id)[0] == "priorizado"


def test_patch_status_skip_to_repaired(api: TestClient, conn: Connection) -> None:
    token = _admin_token(api, conn)
    report_id = _evaluated(conn, insert_user(conn), urgency="7.25")

    response = _patch(api, token, report_id, status="reparado")

    assert response.status_code == 200
    assert response.json()["status"] == "reparado"
    assert response.json()["allowed_next_statuses"] == []
    assert response.json()["history"][-1]["note"] is None


def test_patch_status_backwards_is_409(api: TestClient, conn: Connection) -> None:
    token = _admin_token(api, conn)
    report_id = _evaluated(conn, insert_user(conn), urgency="7.25", status=ReportStatus.PRIORITIZED)

    response = _patch(api, token, report_id, status="evaluado")

    assert response.status_code == 409
    assert response.json() == {
        "code": "INVALID_STATUS_TRANSITION",
        "message": "No se puede pasar de «priorizado» a «evaluado»",
        "details": {"current_status": "priorizado"},
    }
    assert _stored_status(conn, report_id)[0] == "priorizado"


def test_patch_status_system_transition_is_409(api: TestClient, conn: Connection) -> None:
    token = _admin_token(api, conn)
    report_id = conn.execute(
        text(
            "INSERT INTO reporte (id_usuario, ubicacion, severidad) "
            "VALUES (:autor, ST_SetSRID(ST_MakePoint(-80, 0), 4326), 2) RETURNING id_reporte"
        ),
        {"autor": insert_user(conn)},
    ).scalar_one()

    response = _patch(api, token, report_id, status="evaluado")

    assert response.status_code == 409
    assert response.json()["details"] == {"current_status": "registrado"}


def test_patch_status_stale_is_409(api: TestClient, conn: Connection) -> None:
    """Otro administrador lo reparó después de que este cargó la pantalla."""
    token = _admin_token(api, conn)
    report_id = _evaluated(conn, insert_user(conn), urgency="7.25")
    assert _patch(api, token, report_id, status="reparado").status_code == 200

    response = _patch(api, token, report_id, status="priorizado", note=NOTE)

    assert response.status_code == 409
    assert response.json()["details"] == {"current_status": "reparado"}
    history = conn.execute(
        text("SELECT count(*) FROM historial_estado WHERE id_reporte = :r"), {"r": report_id}
    ).scalar_one()
    assert history == 1


def test_patch_status_does_not_change_urgency(api: TestClient, conn: Connection) -> None:
    token = _admin_token(api, conn)
    report_id = _evaluated(conn, insert_user(conn), urgency="7.25")

    _patch(api, token, report_id, status="priorizado")

    assert _stored_status(conn, report_id) == ("priorizado", "7.25")


def test_patch_status_unknown_report_is_404(api: TestClient, conn: Connection) -> None:
    token = _admin_token(api, conn)

    response = _patch(api, token, uuid.uuid4(), status="priorizado")

    assert response.status_code == 404
    assert response.json()["code"] == "REPORT_NOT_FOUND"


@pytest.mark.parametrize(
    "body",
    [
        {"status": "priorizado", "note": "x" * 1001},
        {"status": "archivado"},
        {"note": "sin estado"},
    ],
)
def test_patch_status_invalid_body_is_422(
    api: TestClient, conn: Connection, body: dict[str, object]
) -> None:
    token = _admin_token(api, conn)
    report_id = _evaluated(conn, insert_user(conn), urgency="7.25")

    assert _patch(api, token, report_id, **body).status_code == 422


def test_patch_status_note_of_1000_chars_is_accepted(api: TestClient, conn: Connection) -> None:
    token = _admin_token(api, conn)
    report_id = _evaluated(conn, insert_user(conn), urgency="7.25")

    response = _patch(api, token, report_id, status="priorizado", note="x" * 1000)

    assert response.status_code == 200


def test_patch_status_requires_admin(api: TestClient, conn: Connection) -> None:
    report_id = _evaluated(conn, insert_user(conn), urgency="7.25")
    citizen = _citizen_token(api)

    assert _patch(api, citizen, report_id, status="priorizado").status_code == 403
    assert (
        api.patch(f"{ADMIN}/reports/{report_id}/status", json={"status": "priorizado"}).status_code
        == 401
    )
    assert _stored_status(conn, report_id)[0] == "evaluado"
