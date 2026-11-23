"""Rondas de evaluación contra PostGIS real: abrir, avance y cerrar (objetivo 4)."""

import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from httpx import Response
from sqlalchemy import Connection, text
from sqlalchemy.orm import Session

from app.main import API_V1_PREFIX
from app.modules.reports.domain.status import ReportStatus
from app.modules.validation.infrastructure.round_repository import SqlRoundRepository
from tests.integration.conftest import bearer, insert_user, requires_db
from tests.integration.test_admin_dashboard_api import (
    _admin_token,
    _citizen_token,
    _evaluated,
)
from tests.integration.test_zones_api import CENTRO, OBONUCO, _collection, _import

pytestmark = [pytest.mark.integration, requires_db]

ROUNDS = f"{API_V1_PREFIX}/admin/evaluation-rounds"
WEIGHTS = f"{API_V1_PREFIX}/admin/weights"
CENTRO_LON = -80.0  # dentro de «Centro» (-80,01..-79,99)
OBONUCO_LON = -79.97  # dentro de «Obonuco» (-79,98..-79,96)


def _zone_reports(
    conn: Connection, zone_lon: float, count: int, prefix: str, **kwargs: object
) -> list[uuid.UUID]:
    author = insert_user(conn, email=f"{prefix}@example.test")
    return [
        _evaluated(conn, author, urgency=f"{9 - index * 0.5:.2f}", lon=zone_lon, **kwargs)
        for index in range(count)
    ]


def _open(api: TestClient, token: str, size: int = 5, name: str = "Ronda 1") -> Response:
    return api.post(ROUNDS, json={"name": name, "sample_size": size}, headers=bearer(token))


def _frozen(conn: Connection, round_id: str) -> list[tuple[uuid.UUID, int, Decimal, int]]:
    rows = conn.execute(
        text(
            "SELECT id_reporte, id_zona, puntaje_u, orden_motor FROM ronda_reporte "
            "WHERE id_ronda = :r ORDER BY id_zona, orden_motor"
        ),
        {"r": round_id},
    )
    return [(row.id_reporte, row.id_zona, row.puntaje_u, row.orden_motor) for row in rows]


def _two_zones(session: Session) -> None:
    _import(session, _collection(CENTRO, OBONUCO))


def test_open_freezes_only_active_reports_inside_zones_with_u_and_weights_version(
    api: TestClient, session: Session, conn: Connection
) -> None:
    token = _admin_token(api, conn)
    centro = _zone_reports(conn, CENTRO_LON, 5, "c")
    obonuco = _zone_reports(conn, OBONUCO_LON, 5, "o")
    author = insert_user(conn, email="otro@example.test")
    _evaluated(conn, author, urgency="9.90", status=ReportStatus.REPAIRED, lon=CENTRO_LON)
    outside = _evaluated(conn, author, urgency="9.90", lon=-79.5)
    unevaluated = conn.execute(
        text(
            "INSERT INTO reporte (id_usuario, ubicacion, severidad) VALUES "
            "(:u, ST_SetSRID(ST_MakePoint(-80.0, 0.0), 4326), 2) RETURNING id_reporte"
        ),
        {"u": author},
    ).scalar_one()
    _two_zones(session)

    response = _open(api, token)

    assert response.status_code == 201, response.json()
    round_id = response.json()["id"]
    frozen = _frozen(conn, round_id)
    assert {row[0] for row in frozen} == set(centro) | set(obonuco)
    assert outside not in {row[0] for row in frozen}
    assert unevaluated not in {row[0] for row in frozen}
    centro_rows = [row for row in frozen if row[0] in centro]
    assert [row[3] for row in centro_rows] == [1, 2, 3, 4, 5]
    assert [row[2] for row in centro_rows] == [
        Decimal("9.00"),
        Decimal("8.50"),
        Decimal("8.00"),
        Decimal("7.50"),
        Decimal("7.00"),
    ]
    stored = conn.execute(
        text(
            "SELECT estado::text, tamano_muestra, id_config, "
            "(SELECT id_config FROM configuracion_pesos WHERE vigente) AS current "
            "FROM ronda_evaluacion WHERE id_ronda = :r"
        ),
        {"r": round_id},
    ).one()
    assert stored.estado == "abierta"
    assert stored.tamano_muestra == 5
    assert stored.id_config == stored.current


def test_sample_limits_each_zone_to_the_requested_size(
    api: TestClient, session: Session, conn: Connection
) -> None:
    token = _admin_token(api, conn)
    _zone_reports(conn, CENTRO_LON, 8, "c")
    _zone_reports(conn, OBONUCO_LON, 6, "o")
    _two_zones(session)

    round_id = _open(api, token, size=5).json()["id"]

    frozen = _frozen(conn, round_id)
    zones = [row[1] for row in frozen]
    assert sorted(zones.count(zone) for zone in set(zones)) == [5, 5]


def test_changing_weights_afterwards_does_not_change_the_frozen_rows(
    api: TestClient, session: Session, conn: Connection
) -> None:
    token = _admin_token(api, conn)
    _zone_reports(conn, CENTRO_LON, 5, "c")
    _two_zones(session)
    _zone_reports(conn, OBONUCO_LON, 5, "o")
    _two_zones(session)
    round_id = _open(api, token).json()["id"]
    before = _frozen(conn, round_id)
    base = api.get(WEIGHTS, headers=bearer(token)).json()["id"]

    saved = api.put(
        WEIGHTS,
        json={
            "base_version_id": base,
            "w_severity": "0.60",
            "w_flow": "0.30",
            "w_proximity": "0.10",
        },
        headers=bearer(token),
    )

    assert saved.status_code == 200, saved.json()
    assert saved.json()["recalculated_reports"] == 10
    assert _frozen(conn, round_id) == before


def test_second_open_is_409(api: TestClient, session: Session, conn: Connection) -> None:
    token = _admin_token(api, conn)
    _zone_reports(conn, CENTRO_LON, 5, "c")
    _import(session, _collection(CENTRO))
    assert _open(api, token).status_code == 201

    response = _open(api, token, name="Ronda 2")

    assert response.status_code == 409
    assert response.json()["code"] == "EVALUATION_ROUND_ALREADY_OPEN"


def test_concurrent_open_loses_at_the_unique_index_and_is_409_not_500(
    api: TestClient, session: Session, conn: Connection, monkeypatch: pytest.MonkeyPatch
) -> None:
    token = _admin_token(api, conn)
    _zone_reports(conn, CENTRO_LON, 5, "c")
    _import(session, _collection(CENTRO))
    assert _open(api, token).status_code == 201
    # Simula que la otra transacción abrió la ronda justo después de la verificación amistosa.
    monkeypatch.setattr(SqlRoundRepository, "has_open", lambda _self: False)

    response = _open(api, token, name="Ronda 2")

    assert response.status_code == 409
    assert response.json()["code"] == "EVALUATION_ROUND_ALREADY_OPEN"
    open_rounds = conn.execute(
        text("SELECT count(*) FROM ronda_evaluacion WHERE estado = 'abierta'")
    ).scalar_one()
    assert open_rounds == 1


def test_open_without_zones_is_422(api: TestClient, conn: Connection) -> None:
    token = _admin_token(api, conn)

    response = _open(api, token)

    assert response.status_code == 422
    assert response.json()["code"] == "EVALUATION_NO_ZONES"


def test_open_with_a_small_zone_is_422_with_details_and_creates_nothing(
    api: TestClient, session: Session, conn: Connection
) -> None:
    token = _admin_token(api, conn)
    _zone_reports(conn, CENTRO_LON, 5, "c")
    _zone_reports(conn, OBONUCO_LON, 4, "o")
    _two_zones(session)

    response = _open(api, token)

    assert response.status_code == 422
    body = response.json()
    assert body["code"] == "EVALUATION_ZONE_TOO_SMALL"
    assert body["details"] == {"zone": "Obonuco", "reports": 4, "minimum": 5}
    assert conn.execute(text("SELECT count(*) FROM ronda_evaluacion")).scalar_one() == 0


@pytest.mark.parametrize("size", [0, 101, -3])
def test_sample_size_outside_1_to_100_is_422(api: TestClient, conn: Connection, size: int) -> None:
    token = _admin_token(api, conn)

    response = _open(api, token, size=size)

    assert response.status_code == 422
    assert response.json()["code"] == "VALIDATION_ERROR"


def test_close_then_close_again_is_409_and_unknown_is_404(
    api: TestClient, session: Session, conn: Connection
) -> None:
    token = _admin_token(api, conn)
    _zone_reports(conn, CENTRO_LON, 5, "c")
    _import(session, _collection(CENTRO))
    round_id = _open(api, token).json()["id"]

    closed = api.post(f"{ROUNDS}/{round_id}/close", headers=bearer(token))
    again = api.post(f"{ROUNDS}/{round_id}/close", headers=bearer(token))
    unknown = api.post(f"{ROUNDS}/{uuid.uuid4()}/close", headers=bearer(token))

    assert closed.status_code == 200, closed.json()
    assert closed.json()["status"] == "cerrada"
    assert closed.json()["closed_at"] is not None
    assert (again.status_code, again.json()["code"]) == (409, "EVALUATION_ROUND_CLOSED")
    assert (unknown.status_code, unknown.json()["code"]) == (404, "EVALUATION_ROUND_NOT_FOUND")


def test_a_new_round_can_open_after_closing_the_previous_one(
    api: TestClient, session: Session, conn: Connection
) -> None:
    token = _admin_token(api, conn)
    _zone_reports(conn, CENTRO_LON, 5, "c")
    _import(session, _collection(CENTRO))
    first = _open(api, token).json()["id"]
    api.post(f"{ROUNDS}/{first}/close", headers=bearer(token))

    second = _open(api, token, name="Ronda 2")

    assert second.status_code == 201


def _submit(
    conn: Connection, round_id: str, user: uuid.UUID, report: uuid.UUID, at: datetime
) -> None:
    conn.execute(
        text(
            "INSERT INTO orden_evaluador (id_ronda, id_usuario, id_reporte, posicion, fecha_envio) "
            "VALUES (:r, :u, :p, 1, :t)"
        ),
        {"r": round_id, "u": user, "p": report, "t": at},
    )


def test_progress_shows_anonymous_labels_numbered_by_first_submission(
    api: TestClient, session: Session, conn: Connection
) -> None:
    token = _admin_token(api, conn)
    centro = _zone_reports(conn, CENTRO_LON, 5, "c")
    obonuco = _zone_reports(conn, OBONUCO_LON, 5, "o")
    _two_zones(session)
    round_id = _open(api, token).json()["id"]
    early = insert_user(conn, email="ana-secreta@example.test")
    late = insert_user(conn, email="beto-secreto@example.test")
    now = datetime(2026, 11, 1, 12, 0, tzinfo=UTC)
    # «late» entra antes en la zona Obonuco pero su primer envío global es posterior.
    _submit(conn, round_id, early, centro[0], now)
    _submit(conn, round_id, late, obonuco[0], now + timedelta(minutes=5))
    _submit(conn, round_id, early, obonuco[1], now + timedelta(minutes=9))

    response = api.get(f"{ROUNDS}/{round_id}", headers=bearer(token))

    assert response.status_code == 200, response.json()
    body = response.json()
    assert (body["name"], body["status"], body["sample_size"]) == ("Ronda 1", "abierta", 5)
    zones = {zone["name"]: zone for zone in body["zones"]}
    assert zones["Centro"]["n_reports"] == 5
    assert zones["Centro"]["submitted_by"] == ["Evaluador 1"]
    assert zones["Obonuco"]["submitted_by"] == ["Evaluador 1", "Evaluador 2"]
    raw = response.text
    assert "secret" not in raw
    assert str(early) not in raw
    assert str(late) not in raw


def test_list_is_most_recent_first_and_paginated(
    api: TestClient, session: Session, conn: Connection
) -> None:
    token = _admin_token(api, conn)
    _zone_reports(conn, CENTRO_LON, 5, "c")
    _import(session, _collection(CENTRO))
    old = _open(api, token, name="Antigua").json()["id"]
    api.post(f"{ROUNDS}/{old}/close", headers=bearer(token))
    conn.execute(
        text("UPDATE ronda_evaluacion SET fecha_apertura = fecha_apertura - interval '1 day'")
    )
    _open(api, token, name="Reciente")

    listed = api.get(ROUNDS, headers=bearer(token))
    page = api.get(f"{ROUNDS}?limit=1&offset=1", headers=bearer(token))

    assert [item["name"] for item in listed.json()["items"]] == ["Reciente", "Antigua"]
    assert [item["name"] for item in page.json()["items"]] == ["Antigua"]
    assert api.get(f"{ROUNDS}?limit=51", headers=bearer(token)).status_code == 422


def test_unknown_round_progress_is_404(api: TestClient, conn: Connection) -> None:
    token = _admin_token(api, conn)

    response = api.get(f"{ROUNDS}/{uuid.uuid4()}", headers=bearer(token))

    assert (response.status_code, response.json()["code"]) == (404, "EVALUATION_ROUND_NOT_FOUND")


def test_routes_require_administrator(api: TestClient) -> None:
    citizen = _citizen_token(api)
    some_id = uuid.uuid4()

    calls = [
        api.post(ROUNDS, json={"name": "x", "sample_size": 5}, headers=bearer(citizen)),
        api.get(ROUNDS, headers=bearer(citizen)),
        api.get(f"{ROUNDS}/{some_id}", headers=bearer(citizen)),
        api.post(f"{ROUNDS}/{some_id}/close", headers=bearer(citizen)),
        api.get(ROUNDS),
    ]

    assert [call.status_code for call in calls] == [403, 403, 403, 403, 401]
