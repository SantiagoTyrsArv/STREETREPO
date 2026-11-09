"""GET /api/v1/admin/reports/{id} contra PostGIS real (HU-08, HU-12)."""

import uuid
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Connection, text

from app.main import API_V1_PREFIX
from app.modules.reports.domain.severity import Severity
from tests.integration.conftest import TEST_OSM_ID, bearer, insert_user, requires_db
from tests.integration.test_admin_dashboard_api import (
    ADMIN,
    ADMIN_EMAIL,
    _admin_token,
    _citizen_token,
    _confirm,
    _evaluated,
    _road,
)

pytestmark = [pytest.mark.integration, requires_db]

NOTE = "Cuadrilla asignada para el lunes"


def _service(conn: Connection) -> int:
    service_id: int = conn.execute(
        text(
            "INSERT INTO servicio_critico (osm_id, nombre, tipo, ubicacion) "
            "VALUES (:osm_id, 'Hospital de prueba', 'hospital', "
            "ST_SetSRID(ST_MakePoint(-80, 0.002), 4326)) RETURNING id_servicio"
        ),
        {"osm_id": TEST_OSM_ID + 600},
    ).scalar_one()
    return service_id


def _add_evaluation(conn: Connection, report_id: uuid.UUID, service_id: int | None) -> int:
    """Segunda evaluación (más reciente) con pesos propios y servicio a 222,39 m."""
    config_id: int = conn.execute(
        text(
            "INSERT INTO configuracion_pesos (w_severidad, w_flujo, w_proximidad) "
            "VALUES (0.40, 0.40, 0.20) RETURNING id_config"
        )
    ).scalar_one()
    conn.execute(
        text(
            "INSERT INTO evaluacion_prioridad (id_reporte, id_config, id_servicio, "
            "distancia_servicio_m, s_severidad, f_flujo, p_proximidad, u_utilidad) "
            "VALUES (:r, :c, :s, :d, 10, 7, 6.94, 8.19)"
        ),
        {
            "r": report_id,
            "c": config_id,
            "s": service_id,
            "d": Decimal("222.39") if service_id else None,
        },
    )
    return config_id


def _history(
    conn: Connection, report_id: uuid.UUID, user_id: uuid.UUID | None, **kw: str | None
) -> None:
    conn.execute(
        text(
            "INSERT INTO historial_estado (id_reporte, id_usuario, estado_anterior, "
            "estado_nuevo, observacion, fecha_cambio) VALUES (:r, :u, "
            "CAST(:antes AS estado_reporte), CAST(:despues AS estado_reporte), :nota, "
            "CAST(:fecha AS timestamptz))"
        ),
        {"r": report_id, "u": user_id, "nota": None} | kw,
    )


def _user_id(conn: Connection, email: str) -> uuid.UUID:
    user_id: uuid.UUID = conn.execute(
        text("SELECT id_usuario FROM usuario WHERE correo = :c"), {"c": email}
    ).scalar_one()
    return user_id


def test_admin_detail_full_breakdown(api: TestClient, conn: Connection) -> None:
    token = _admin_token(api, conn)
    admin_id = _user_id(conn, ADMIN_EMAIL)
    author = insert_user(conn, email="autor@example.test")
    report_id = _evaluated(
        conn, author, urgency="8.19", severity=Severity.HIGH, road_id=_road(conn)
    )
    config_id = _add_evaluation(conn, report_id, _service(conn))
    _confirm(conn, report_id, 2)
    _history(conn, report_id, author, antes=None, despues="registrado", fecha="2026-10-01T12:00Z")
    _history(
        conn, report_id, None, antes="registrado", despues="evaluado", fecha="2026-10-01T12:01Z"
    )
    _history(
        conn,
        report_id,
        admin_id,
        antes="evaluado",
        despues="priorizado",
        nota=NOTE,
        fecha="2026-10-02T09:00Z",
    )
    conn.execute(
        text(
            "UPDATE reporte SET estado = 'priorizado', descripcion = 'Hueco' WHERE id_reporte = :r"
        ),
        {"r": report_id},
    )

    response = api.get(f"{ADMIN}/reports/{report_id}", headers=bearer(token))

    assert response.status_code == 200, response.json()
    body = response.json()
    assert body["id"] == str(report_id)
    assert body["status"] == "priorizado"
    assert body["allowed_next_statuses"] == ["reparado"]
    assert body["severity"] == "alta"
    assert body["description"] == "Hueco"
    assert body["location"] == {"lat": 0.0, "lon": -80.0}
    assert body["address"] == "Avenida de prueba"
    assert body["needs_road_review"] is False
    assert body["road"] == {"name": "Avenida de prueba", "highway": "secondary"}
    assert body["reporter_name"] == "Prueba"
    assert body["confirmations"] == 2
    evaluation = body["evaluation"]
    assert {k: evaluation[k] for k in ("s", "f", "p", "u")} == {
        "s": 10.0,
        "f": 7.0,
        "p": 6.94,
        "u": 8.19,
    }
    assert (evaluation["w_severity"], evaluation["w_flow"], evaluation["w_proximity"]) == (
        0.4,
        0.4,
        0.2,
    )
    assert evaluation["config_id"] == config_id
    assert evaluation["service"] == {
        "name": "Hospital de prueba",
        "service_type": "hospital",
        "distance_m": 222.39,
    }
    assert [
        (e["previous_status"], e["status"], e["note"], e["changed_by_name"])
        for e in body["history"]
    ] == [
        (None, "registrado", None, "Prueba"),
        ("registrado", "evaluado", None, None),
        ("evaluado", "priorizado", NOTE, "Ana Pérez"),
    ]


def test_admin_detail_without_road_or_service(api: TestClient, conn: Connection) -> None:
    token = _admin_token(api, conn)
    report_id = _evaluated(conn, insert_user(conn), urgency="3.60")

    body = api.get(f"{ADMIN}/reports/{report_id}", headers=bearer(token)).json()

    assert body["road"] is None
    assert body["needs_road_review"] is True
    assert body["address"] == "Sin vía asociada"
    assert body["evaluation"]["service"] is None
    assert body["evaluation"]["u"] == 3.6
    assert body["allowed_next_statuses"] == ["priorizado", "reparado"]


def test_admin_detail_without_evaluation(api: TestClient, conn: Connection) -> None:
    token = _admin_token(api, conn)
    report_id = conn.execute(
        text(
            "INSERT INTO reporte (id_usuario, ubicacion, severidad) "
            "VALUES (:autor, ST_SetSRID(ST_MakePoint(-80, 0), 4326), 1) RETURNING id_reporte"
        ),
        {"autor": insert_user(conn)},
    ).scalar_one()

    body = api.get(f"{ADMIN}/reports/{report_id}", headers=bearer(token)).json()

    assert body["evaluation"] is None
    assert body["status"] == "registrado"
    assert body["allowed_next_statuses"] == []
    assert body["severity"] == "baja"


def test_admin_detail_requires_admin(api: TestClient, conn: Connection) -> None:
    report_id = _evaluated(conn, insert_user(conn), urgency="5.00")
    citizen = _citizen_token(api)

    assert api.get(f"{ADMIN}/reports/{report_id}", headers=bearer(citizen)).status_code == 403
    assert api.get(f"{ADMIN}/reports/{report_id}").status_code == 401


def test_admin_detail_unknown_id_is_404(api: TestClient, conn: Connection) -> None:
    token = _admin_token(api, conn)

    response = api.get(f"{ADMIN}/reports/{uuid.uuid4()}", headers=bearer(token))

    assert response.status_code == 404
    assert response.json()["code"] == "REPORT_NOT_FOUND"


def test_admin_detail_non_uuid_is_422(api: TestClient, conn: Connection) -> None:
    token = _admin_token(api, conn)

    assert api.get(f"{API_V1_PREFIX}/admin/reports/abc", headers=bearer(token)).status_code == 422
