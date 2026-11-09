"""GET /admin/ranking, /admin/summary y /admin/heatmap contra PostGIS real (HU-08)."""

import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Connection, text

from app.main import API_V1_PREFIX
from app.modules.admin.domain.ranking_view import RankingItem
from app.modules.priority.domain.ranking import rank
from app.modules.reports.domain.severity import Severity
from app.modules.reports.domain.status import ReportStatus
from tests.integration.conftest import (
    TEST_OSM_ID,
    bearer,
    insert_user,
    login_user,
    register_user,
    requires_db,
)

pytestmark = [pytest.mark.integration, requires_db]

ADMIN = f"{API_V1_PREFIX}/admin"
ADMIN_EMAIL = "funcionaria@example.com"
CITIZEN_EMAIL = "ciudadano@example.com"
# Punto del Pacífico donde las pruebas de PostGIS ponen sus datos, lejos de Pasto.
LON, LAT = -80.0, 0.0
BASE_DATE = datetime(2026, 10, 1, 12, 0, tzinfo=UTC)


def _admin_token(api: TestClient, conn: Connection) -> str:
    register_user(api, email=ADMIN_EMAIL)
    conn.execute(
        text("UPDATE usuario SET rol = 'administrador' WHERE correo = :correo"),
        {"correo": ADMIN_EMAIL},
    )
    return str(login_user(api, email=ADMIN_EMAIL)["access_token"])


def _citizen_token(api: TestClient) -> str:
    register_user(api, email=CITIZEN_EMAIL)
    return str(login_user(api, email=CITIZEN_EMAIL)["access_token"])


def _road(conn: Connection, name: str | None = "Avenida de prueba") -> int:
    road_id: int = conn.execute(
        text(
            "INSERT INTO via (osm_id, nombre, highway_osm, jerarquia_vial, factor_flujo, geom) "
            "VALUES (:osm_id, :nombre, 'secondary', 'secundaria', 7, "
            "ST_GeomFromText('LINESTRING(-80.001 0, -79.999 0)', 4326)) RETURNING id_via"
        ),
        {"osm_id": TEST_OSM_ID + 500, "nombre": name},
    ).scalar_one()
    return road_id


def _evaluated(
    conn: Connection,
    author: uuid.UUID,
    *,
    urgency: str,
    severity: Severity = Severity.MEDIUM,
    status: ReportStatus = ReportStatus.EVALUATED,
    created_at: datetime = BASE_DATE,
    road_id: int | None = None,
    lon: float = LON,
    lat: float = LAT,
) -> uuid.UUID:
    """Reporte con una evaluación guardada, como lo deja el motor de priorización."""
    report_id: uuid.UUID = conn.execute(
        text(
            "INSERT INTO reporte (id_usuario, ubicacion, severidad, estado, puntaje_prioridad, "
            "id_via, fecha_creacion) "
            "VALUES (:autor, ST_SetSRID(ST_MakePoint(:lon, :lat), 4326), :severidad, "
            "CAST(:estado AS estado_reporte), :u, :via, :fecha) RETURNING id_reporte"
        ),
        {
            "autor": author,
            "lon": lon,
            "lat": lat,
            "severidad": int(severity),
            "estado": status.value,
            "u": Decimal(urgency),
            "via": road_id,
            "fecha": created_at,
        },
    ).scalar_one()
    conn.execute(
        text(
            "INSERT INTO evaluacion_prioridad (id_reporte, id_config, s_severidad, f_flujo, "
            "p_proximidad, u_utilidad) "
            "SELECT :r, id_config, 6, 7, 5, :u FROM configuracion_pesos WHERE vigente"
        ),
        {"r": report_id, "u": Decimal(urgency)},
    )
    return report_id


def _confirm(conn: Connection, report_id: uuid.UUID, times: int) -> None:
    for index in range(times):
        user = insert_user(conn, email=f"confirma{index}-{report_id}@example.test")
        conn.execute(
            text("INSERT INTO confirmacion (id_reporte, id_usuario) VALUES (:r, :u)"),
            {"r": report_id, "u": user},
        )


def _ranking(api: TestClient, token: str, query: str = "") -> dict[str, object]:
    response = api.get(f"{ADMIN}/ranking{query}", headers=bearer(token))
    assert response.status_code == 200, response.json()
    body: dict[str, object] = response.json()
    return body


def _ids(body: dict[str, object]) -> list[str]:
    items = body["items"]
    assert isinstance(items, list)
    return [item["id"] for item in items]


def test_ranking_order_matches_domain_ranking(api: TestClient, conn: Connection) -> None:
    token = _admin_token(api, conn)
    author = insert_user(conn, email="autor@example.test")
    # Empates en U que se resuelven por severidad, luego confirmaciones, luego antigüedad.
    specs = [
        ("6.10", Severity.MEDIUM, 0, BASE_DATE),
        ("8.70", Severity.MEDIUM, 0, BASE_DATE),
        ("6.10", Severity.HIGH, 0, BASE_DATE + timedelta(days=3)),
        ("6.10", Severity.MEDIUM, 2, BASE_DATE + timedelta(days=2)),
        ("6.10", Severity.MEDIUM, 2, BASE_DATE + timedelta(days=1)),
        ("3.60", Severity.HIGH, 5, BASE_DATE),
    ]
    domain_items = []
    for urgency, severity, confirmations, created_at in specs:
        report_id = _evaluated(
            conn, author, urgency=urgency, severity=severity, created_at=created_at
        )
        _confirm(conn, report_id, confirmations)
        domain_items.append(
            RankingItem(
                report_id=report_id,
                status=ReportStatus.EVALUATED,
                severity=severity,
                severity_score=Decimal(6),
                flow_score=Decimal(7),
                proximity_score=Decimal(5),
                urgency_score=Decimal(urgency),
                road_id=None,
                road_name=None,
                confirmations=confirmations,
                created_at=created_at,
            )
        )

    body = _ranking(api, token)

    assert _ids(body) == [str(item.report_id) for item in rank(domain_items)]
    assert body["total"] == len(specs)
    assert (body["limit"], body["offset"]) == (20, 0)


def test_ranking_item_fields(api: TestClient, conn: Connection) -> None:
    token = _admin_token(api, conn)
    road = _road(conn)
    report_id = _evaluated(
        conn, insert_user(conn), urgency="8.70", severity=Severity.HIGH, road_id=road
    )
    _confirm(conn, report_id, 1)

    (item,) = _ranking(api, token)["items"]  # type: ignore[misc]

    assert item == {
        "id": str(report_id),
        "status": "evaluado",
        "severity": "alta",
        "s": 6.0,
        "f": 7.0,
        "p": 5.0,
        "u": 8.7,
        "needs_road_review": False,
        "address": "Avenida de prueba",
        "confirmations": 1,
        "created_at": "2026-10-01T12:00:00Z",
    }


def test_ranking_pages_with_limit_and_offset(api: TestClient, conn: Connection) -> None:
    token = _admin_token(api, conn)
    author = insert_user(conn)
    ids = [str(_evaluated(conn, author, urgency=f"{9 - index}.00")) for index in range(5)]

    body = _ranking(api, token, "?limit=2&offset=2")

    assert _ids(body) == ids[2:4]
    assert body["total"] == 5


def test_ranking_limit_over_100_is_422(api: TestClient, conn: Connection) -> None:
    token = _admin_token(api, conn)

    assert api.get(f"{ADMIN}/ranking?limit=101", headers=bearer(token)).status_code == 422


def test_ranking_requires_admin(api: TestClient) -> None:
    citizen = _citizen_token(api)

    assert api.get(f"{ADMIN}/ranking", headers=bearer(citizen)).status_code == 403
    assert api.get(f"{ADMIN}/ranking").status_code == 401
    assert api.get(f"{ADMIN}/summary", headers=bearer(citizen)).status_code == 403
    assert api.get(f"{ADMIN}/heatmap", headers=bearer(citizen)).status_code == 403


def test_ranking_excludes_repaired_by_default(api: TestClient, conn: Connection) -> None:
    token = _admin_token(api, conn)
    author = insert_user(conn)
    active = _evaluated(conn, author, urgency="5.00")
    _evaluated(conn, author, urgency="9.00", status=ReportStatus.REPAIRED)

    assert _ids(_ranking(api, token)) == [str(active)]


def test_ranking_skips_reports_without_evaluation(api: TestClient, conn: Connection) -> None:
    token = _admin_token(api, conn)
    author = insert_user(conn)
    evaluated = _evaluated(conn, author, urgency="5.00")
    conn.execute(
        text(
            "INSERT INTO reporte (id_usuario, ubicacion, severidad) "
            "VALUES (:autor, ST_SetSRID(ST_MakePoint(-80, 0), 4326), 2)"
        ),
        {"autor": author},
    )

    assert _ids(_ranking(api, token)) == [str(evaluated)]


def test_ranking_filters_by_status(api: TestClient, conn: Connection) -> None:
    token = _admin_token(api, conn)
    author = insert_user(conn)
    _evaluated(conn, author, urgency="9.00")
    prioritized = _evaluated(conn, author, urgency="5.00", status=ReportStatus.PRIORITIZED)
    repaired = _evaluated(conn, author, urgency="4.00", status=ReportStatus.REPAIRED)

    body = _ranking(api, token, "?status=priorizado&status=reparado")

    assert _ids(body) == [str(prioritized), str(repaired)]
    assert body["total"] == 2


def test_ranking_unknown_status_is_422(api: TestClient, conn: Connection) -> None:
    token = _admin_token(api, conn)

    response = api.get(f"{ADMIN}/ranking?status=archivado", headers=bearer(token))

    assert response.status_code == 422


def test_ranking_marks_review_road_when_no_road(api: TestClient, conn: Connection) -> None:
    token = _admin_token(api, conn)
    _evaluated(conn, insert_user(conn), urgency="3.60")

    (item,) = _ranking(api, token)["items"]  # type: ignore[misc]

    assert item["needs_road_review"] is True
    assert item["address"] == "Sin vía asociada"


def test_summary_counts_by_status(api: TestClient, conn: Connection) -> None:
    token = _admin_token(api, conn)
    author = insert_user(conn)
    _evaluated(conn, author, urgency="5.00")
    _evaluated(conn, author, urgency="6.00")
    _evaluated(conn, author, urgency="7.00", status=ReportStatus.PRIORITIZED)
    _evaluated(conn, author, urgency="8.00", status=ReportStatus.REPAIRED)

    response = api.get(f"{ADMIN}/summary", headers=bearer(token))

    assert response.status_code == 200
    assert response.json() == {"active": 3, "evaluated": 2, "prioritized": 1, "repaired": 1}


def test_summary_counts_registered_reports_as_active(api: TestClient, conn: Connection) -> None:
    token = _admin_token(api, conn)
    conn.execute(
        text(
            "INSERT INTO reporte (id_usuario, ubicacion, severidad) "
            "VALUES (:autor, ST_SetSRID(ST_MakePoint(-80, 0), 4326), 2)"
        ),
        {"autor": insert_user(conn)},
    )

    body = api.get(f"{ADMIN}/summary", headers=bearer(token)).json()

    assert body == {"active": 1, "evaluated": 0, "prioritized": 0, "repaired": 0}


def test_summary_and_ranking_empty_database(api: TestClient, conn: Connection) -> None:
    token = _admin_token(api, conn)

    ranking = _ranking(api, token)
    summary = api.get(f"{ADMIN}/summary", headers=bearer(token)).json()
    heatmap = api.get(f"{ADMIN}/heatmap", headers=bearer(token)).json()

    assert (ranking["total"], ranking["items"]) == (0, [])
    assert summary == {"active": 0, "evaluated": 0, "prioritized": 0, "repaired": 0}
    assert heatmap == {"points": []}


def test_heatmap_points_inside_bbox_only(api: TestClient, conn: Connection) -> None:
    token = _admin_token(api, conn)
    author = insert_user(conn)
    _evaluated(conn, author, urgency="8.70", lon=-80.0, lat=0.0)
    _evaluated(conn, author, urgency="5.00", lon=-79.0, lat=0.5)
    _evaluated(conn, author, urgency="9.00", lon=-80.0, lat=0.0, status=ReportStatus.REPAIRED)

    inside = api.get(f"{ADMIN}/heatmap?bbox=-80.1,-0.1,-79.9,0.1", headers=bearer(token))
    everything = api.get(f"{ADMIN}/heatmap", headers=bearer(token))

    assert inside.status_code == 200
    assert inside.json() == {"points": [{"lat": 0.0, "lon": -80.0, "u": 8.7}]}
    assert len(everything.json()["points"]) == 2


@pytest.mark.parametrize(
    "bbox",
    ["1,2,3", "a,b,c,d", "-79.9,-0.1,-80.1,0.1", "-80.1,-91,-79.9,0.1", "-80.1,0.1,-79.9,-0.1"],
)
def test_heatmap_invalid_bbox_is_422(api: TestClient, conn: Connection, bbox: str) -> None:
    token = _admin_token(api, conn)

    response = api.get(f"{ADMIN}/heatmap?bbox={bbox}", headers=bearer(token))

    assert response.status_code == 422
    assert response.json()["code"] == "INVALID_BBOX"
