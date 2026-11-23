"""Evaluación a ciegas contra PostGIS real: rutas del evaluador (objetivo 4, HU-09).

Lo central es que ninguna respuesta del evaluador lleve información del motor de
priorización y que un orden inválido no guarde nada.
"""

import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from httpx import Response
from sqlalchemy import Connection, text
from sqlalchemy.orm import Session

from app.main import API_V1_PREFIX
from app.modules.reports.domain.photos import PhotoKeys
from app.modules.reports.domain.severity import Severity
from app.modules.validation.domain.blind import shuffle_for
from app.modules.validation.infrastructure.blind_reader import SqlBlindEvaluationRepository
from tests.integration.conftest import (
    TEST_OSM_ID,
    bearer,
    insert_user,
    login_user,
    register_user,
    requires_db,
)
from tests.integration.test_admin_dashboard_api import (
    _admin_token,
    _citizen_token,
    _evaluated,
    _road,
)
from tests.integration.test_zones_api import CENTRO, OBONUCO, _collection, _import

pytestmark = [pytest.mark.integration, requires_db]

CURRENT = f"{API_V1_PREFIX}/evaluation/current"
ROUNDS = f"{API_V1_PREFIX}/admin/evaluation-rounds"
CENTRO_LON = -80.0
OBONUCO_LON = -79.97
CARD_KEYS = {"report_id", "description", "road_name", "severity", "location", "nearby_services"}
# Campos que delatarían al motor o a otros evaluadores en cualquier respuesta del evaluador.
FORBIDDEN_WORDS = (
    "puntaje",
    "score",
    "urgency",
    "priority",
    "orden_motor",
    "engine",
    "motor",
    "factor",
    "flow",
    "proximity",
    "road_class",
    "jerarquia",
    "distance",
    "distancia",
    "confirm",
    "status",
    "estado",
    "created",
    "fecha",
    "author",
    "user",
    "concentra",
    "position",
)


def _evaluator_token(api: TestClient, conn: Connection, email: str = "eva@example.com") -> str:
    register_user(api, email=email)
    conn.execute(text("UPDATE usuario SET rol = 'evaluador' WHERE correo = :c"), {"c": email})
    return str(login_user(api, email=email)["access_token"])


def _user_id(conn: Connection, email: str) -> uuid.UUID:
    user_id: uuid.UUID = conn.execute(
        text("SELECT id_usuario FROM usuario WHERE correo = :c"), {"c": email}
    ).scalar_one()
    return user_id


def _zone_reports(
    conn: Connection, lon: float, count: int, prefix: str, road_id: int | None = None
) -> list[uuid.UUID]:
    author = insert_user(conn, email=f"{prefix}@example.test")
    return [
        _evaluated(
            conn,
            author,
            urgency=f"{9 - index * 0.5:.2f}",
            severity=Severity.HIGH if index % 2 else Severity.LOW,
            lon=lon,
            road_id=road_id,
        )
        for index in range(count)
    ]


def _service(conn: Connection, name: str, lat: float, offset: int) -> None:
    conn.execute(
        text(
            "INSERT INTO servicio_critico (osm_id, nombre, tipo, ubicacion) "
            "VALUES (:osm, :nombre, 'escuela', ST_SetSRID(ST_MakePoint(-80, :lat), 4326))"
        ),
        {"osm": TEST_OSM_ID + 700 + offset, "nombre": name, "lat": lat},
    )


class Pilot:
    """Ronda abierta con dos zonas: Centro (6 reportes) y Obonuco (5)."""

    def __init__(self, api: TestClient, session: Session, conn: Connection) -> None:
        self.admin = _admin_token(api, conn)
        road = _road(conn, name="Carrera 27")
        self.centro = _zone_reports(conn, CENTRO_LON, 6, "c", road_id=road)
        self.obonuco = _zone_reports(conn, OBONUCO_LON, 5, "o")
        conn.execute(
            text("UPDATE reporte SET descripcion = 'Hueco profundo' WHERE id_reporte = :id"),
            {"id": self.centro[0]},
        )
        _service(conn, "Escuela cercana", 0.002, 1)  # ~222 m: entra
        _service(conn, "Escuela lejana", 0.006, 2)  # ~667 m: no entra
        _import(session, _collection(CENTRO, OBONUCO))
        response = api.post(
            ROUNDS, json={"name": "Piloto 1", "sample_size": 10}, headers=bearer(self.admin)
        )
        assert response.status_code == 201, response.json()
        self.round_id = response.json()["id"]
        rows = conn.execute(text("SELECT nombre, id_zona FROM zona")).all()
        self.zone_ids = {row.nombre: row.id_zona for row in rows}

    @property
    def centro_zone(self) -> int:
        return int(self.zone_ids["Centro"])

    @property
    def obonuco_zone(self) -> int:
        return int(self.zone_ids["Obonuco"])


@pytest.fixture
def pilot(api: TestClient, session: Session, conn: Connection) -> Pilot:
    return Pilot(api, session, conn)


def _order_rows(conn: Connection) -> int:
    count: int = conn.execute(text("SELECT count(*) FROM orden_evaluador")).scalar_one()
    return count


def _submit(api: TestClient, token: str, zone_id: int, ids: list[uuid.UUID]) -> Response:
    return api.put(
        f"{CURRENT}/zones/{zone_id}/order",
        json={"report_ids": [str(i) for i in ids]},
        headers=bearer(token),
    )


def _keys(value: object) -> set[str]:
    """Todas las claves de un JSON anidado."""
    if isinstance(value, dict):
        return set(value) | {k for v in value.values() for k in _keys(v)}
    if isinstance(value, list):
        return {k for v in value for k in _keys(v)}
    return set()


def _assert_no_engine_data(body: object) -> None:
    leaked = {key for key in _keys(body) for word in FORBIDDEN_WORDS if word in key.lower()}
    assert leaked == set()


# --- lectura ---------------------------------------------------------------------------


def test_current_round_lists_zones_without_concentration(
    api: TestClient, conn: Connection, pilot: Pilot
) -> None:
    token = _evaluator_token(api, conn)

    response = api.get(CURRENT, headers=bearer(token))

    assert response.status_code == 200, response.json()
    body = response.json()
    assert body == {
        "round": {"id": pilot.round_id, "name": "Piloto 1"},
        "zones": [
            {"id": pilot.centro_zone, "name": "Centro", "n_reports": 6, "submitted": False},
            {"id": pilot.obonuco_zone, "name": "Obonuco", "n_reports": 5, "submitted": False},
        ],
    }
    _assert_no_engine_data(body)


def test_zone_cards_have_exactly_the_blind_fields(
    api: TestClient, conn: Connection, pilot: Pilot
) -> None:
    token = _evaluator_token(api, conn)

    response = api.get(f"{CURRENT}/zones/{pilot.centro_zone}", headers=bearer(token))

    assert response.status_code == 200, response.json()
    body = response.json()
    assert set(body) == {"zone", "cards", "submitted"}
    assert body["zone"] == {"id": pilot.centro_zone, "name": "Centro", "n_reports": 6}
    assert body["submitted"] is False
    assert len(body["cards"]) == 6
    for card in body["cards"]:
        assert set(card) == CARD_KEYS
        assert set(card["location"]) == {"longitude", "latitude"}
        assert card["road_name"] == "Carrera 27"
        assert card["severity"] in {"baja", "alta"}
        assert card["location"] == {"longitude": CENTRO_LON, "latitude": 0.0}
        assert card["nearby_services"] == [
            {
                "name": "Escuela cercana",
                "type": "escuela",
                "location": {"longitude": -80.0, "latitude": 0.002},
            }
        ]
    described = next(c for c in body["cards"] if c["report_id"] == str(pilot.centro[0]))
    assert described["description"] == "Hueco profundo"
    _assert_no_engine_data(body)


def test_cards_of_a_report_without_road_have_null_road_name(
    api: TestClient, conn: Connection, pilot: Pilot
) -> None:
    token = _evaluator_token(api, conn)

    cards = api.get(f"{CURRENT}/zones/{pilot.obonuco_zone}", headers=bearer(token)).json()["cards"]

    assert {c["road_name"] for c in cards} == {None}
    assert {c["description"] for c in cards} == {None}
    assert all(c["nearby_services"] == [] for c in cards)


def test_two_evaluators_see_different_stable_initial_orders(
    api: TestClient, conn: Connection, pilot: Pilot
) -> None:
    token_a = _evaluator_token(api, conn, "eva@example.com")
    token_b = _evaluator_token(api, conn, "beto@example.com")
    eva, beto = _user_id(conn, "eva@example.com"), _user_id(conn, "beto@example.com")
    # Semilla elegida para que los dos órdenes difieran: la prueba no depende del azar de los ids.
    seed = next(
        s
        for s in range(100)
        if shuffle_for(pilot.centro, s, eva) != shuffle_for(pilot.centro, s, beto)
    )
    conn.execute(
        text("UPDATE ronda_evaluacion SET semilla = :s WHERE id_ronda = :r"),
        {"s": seed, "r": pilot.round_id},
    )
    url = f"{CURRENT}/zones/{pilot.centro_zone}"

    def order(token: str) -> list[uuid.UUID]:
        cards = api.get(url, headers=bearer(token)).json()["cards"]
        return [uuid.UUID(c["report_id"]) for c in cards]

    first_a, first_b = order(token_a), order(token_b)

    assert first_a == shuffle_for(pilot.centro, seed, eva)
    assert first_b == shuffle_for(pilot.centro, seed, beto)
    assert first_a != first_b
    assert order(token_a) == first_a
    assert order(token_b) == first_b


def test_unknown_zone_is_404(api: TestClient, conn: Connection, pilot: Pilot) -> None:
    token = _evaluator_token(api, conn)

    response = api.get(f"{CURRENT}/zones/999999", headers=bearer(token))

    assert (response.status_code, response.json()["code"]) == (404, "EVALUATION_ZONE_NOT_FOUND")


@pytest.mark.parametrize("zone_id", [0, -1, 2**31])
def test_zone_id_out_of_range_is_422_not_500(
    api: TestClient, conn: Connection, pilot: Pilot, zone_id: int
) -> None:
    token = _evaluator_token(api, conn)

    view = api.get(f"{CURRENT}/zones/{zone_id}", headers=bearer(token))
    submit = _submit(api, token, zone_id, pilot.centro)

    assert (view.status_code, submit.status_code) == (422, 422)
    assert _order_rows(conn) == 0


def test_without_open_round_every_route_is_404(api: TestClient, conn: Connection) -> None:
    token = _evaluator_token(api, conn)

    for response in (
        api.get(CURRENT, headers=bearer(token)),
        api.get(f"{CURRENT}/zones/1", headers=bearer(token)),
        _submit(api, token, 1, [uuid.uuid4()]),
    ):
        assert (response.status_code, response.json()["code"]) == (
            404,
            "EVALUATION_NO_OPEN_ROUND",
        )


# --- Review Focus 1: rutas laterales ---------------------------------------------------


def test_citizen_and_admin_cannot_use_evaluator_routes(
    api: TestClient, conn: Connection, pilot: Pilot
) -> None:
    citizen = _citizen_token(api)

    for token in (citizen, pilot.admin):
        for response in (
            api.get(CURRENT, headers=bearer(token)),
            api.get(f"{CURRENT}/zones/{pilot.centro_zone}", headers=bearer(token)),
            api.get(f"{CURRENT}/reports/{pilot.centro[0]}/photo", headers=bearer(token)),
            _submit(api, token, pilot.centro_zone, pilot.centro),
        ):
            assert (response.status_code, response.json()["code"]) == (403, "FORBIDDEN")
    assert api.get(CURRENT).status_code == 401
    assert _order_rows(conn) == 0


def test_evaluator_cannot_reach_admin_or_owner_routes(
    api: TestClient, conn: Connection, pilot: Pilot
) -> None:
    token = _evaluator_token(api, conn)

    for path in (
        f"{API_V1_PREFIX}/admin/zones",
        ROUNDS,
        f"{ROUNDS}/{pilot.round_id}",
        f"{API_V1_PREFIX}/admin/ranking",
        f"{API_V1_PREFIX}/admin/reports/{pilot.centro[0]}",
    ):
        response = api.get(path, headers=bearer(token))
        assert response.status_code == 403, path
        assert set(response.json()) <= {"code", "message", "details"}
    for path in (
        f"{API_V1_PREFIX}/reports/{pilot.centro[0]}/photo",
        f"{API_V1_PREFIX}/reports/{pilot.centro[0]}/photo/thumbnail",
        f"{API_V1_PREFIX}/reports/{pilot.centro[0]}",
    ):
        response = api.get(path, headers=bearer(token))
        assert response.status_code in {403, 404}, path
        assert set(response.json()) <= {"code", "message", "details"}


def _store_photo(conn: Connection, photo_dir: Path, report_id: uuid.UUID, name: str) -> None:
    keys = PhotoKeys.for_name(name)
    for key, content in ((keys.photo, b"foto-completa"), (keys.thumbnail, b"mini")):
        path = photo_dir / key
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    conn.execute(
        text(
            "INSERT INTO evidencia (id_reporte, url_foto, formato, tamano_bytes) "
            "VALUES (:id, :url, 'jpg', 13)"
        ),
        {"id": report_id, "url": keys.photo},
    )


def test_photo_of_a_report_in_the_open_round(
    api: TestClient, conn: Connection, pilot: Pilot, photo_dir: Path
) -> None:
    token = _evaluator_token(api, conn)
    _store_photo(conn, photo_dir, pilot.centro[0], "a1" * 16)
    base = f"{CURRENT}/reports/{pilot.centro[0]}/photo"

    photo = api.get(base, headers=bearer(token))
    thumbnail = api.get(f"{base}/thumbnail", headers=bearer(token))

    assert photo.status_code == 200
    assert photo.content == b"foto-completa"
    assert photo.headers["content-type"] == "image/jpeg"
    assert photo.headers["cache-control"] == "private, no-store"
    assert thumbnail.status_code == 200
    assert thumbnail.content == b"mini"


def test_photo_outside_the_round_or_missing_is_404(
    api: TestClient, conn: Connection, pilot: Pilot, photo_dir: Path
) -> None:
    token = _evaluator_token(api, conn)
    author = insert_user(conn, email="fuera@example.test")
    outside = _evaluated(conn, author, urgency="9.00", lon=-79.5)
    _store_photo(conn, photo_dir, outside, "b2" * 16)

    for report_id in (outside, pilot.centro[1], uuid.uuid4()):
        for suffix in ("", "/thumbnail"):
            response = api.get(
                f"{CURRENT}/reports/{report_id}/photo{suffix}", headers=bearer(token)
            )
            assert (response.status_code, response.json()["code"]) == (404, "PHOTO_NOT_FOUND")


def test_photo_of_a_closed_round_is_404(
    api: TestClient, conn: Connection, pilot: Pilot, photo_dir: Path
) -> None:
    token = _evaluator_token(api, conn)
    _store_photo(conn, photo_dir, pilot.centro[0], "c3" * 16)
    api.post(f"{ROUNDS}/{pilot.round_id}/close", headers=bearer(pilot.admin))

    response = api.get(f"{CURRENT}/reports/{pilot.centro[0]}/photo", headers=bearer(token))

    assert (response.status_code, response.json()["code"]) == (404, "PHOTO_NOT_FOUND")


# --- envío del orden y Review Focus 2 --------------------------------------------------


def test_submit_saves_positions_in_the_given_order(
    api: TestClient, conn: Connection, pilot: Pilot
) -> None:
    token = _evaluator_token(api, conn)
    order = list(reversed(pilot.centro))

    response = _submit(api, token, pilot.centro_zone, order)

    assert response.status_code == 201, response.json()
    assert response.json() == {"zone_id": pilot.centro_zone, "submitted": True}
    rows = conn.execute(
        text(
            "SELECT id_reporte, posicion, id_usuario FROM orden_evaluador "
            "WHERE id_ronda = :r ORDER BY posicion"
        ),
        {"r": pilot.round_id},
    ).all()
    assert [row.id_reporte for row in rows] == order
    assert [row.posicion for row in rows] == list(range(1, 7))
    assert {row.id_usuario for row in rows} == {_user_id(conn, "eva@example.com")}
    current = api.get(CURRENT, headers=bearer(token)).json()
    assert [z["submitted"] for z in current["zones"]] == [True, False]
    zone = api.get(f"{CURRENT}/zones/{pilot.centro_zone}", headers=bearer(token)).json()
    assert zone["submitted"] is True


def test_submission_of_one_evaluator_is_not_visible_to_another(
    api: TestClient, conn: Connection, pilot: Pilot
) -> None:
    eva = _evaluator_token(api, conn, "eva@example.com")
    beto = _evaluator_token(api, conn, "beto@example.com")
    assert _submit(api, eva, pilot.centro_zone, pilot.centro).status_code == 201

    current = api.get(CURRENT, headers=bearer(beto)).json()
    zone = api.get(f"{CURRENT}/zones/{pilot.centro_zone}", headers=bearer(beto)).json()

    assert [z["submitted"] for z in current["zones"]] == [False, False]
    assert zone["submitted"] is False
    assert _submit(api, beto, pilot.centro_zone, pilot.centro).status_code == 201


@pytest.mark.parametrize("case", ["repetido", "faltante", "de-otra-zona", "vacio", "desconocido"])
def test_invalid_order_is_422_and_saves_nothing(
    api: TestClient, conn: Connection, pilot: Pilot, case: str
) -> None:
    token = _evaluator_token(api, conn)
    ids = pilot.centro
    orders = {
        "repetido": [*ids[:-1], ids[0]],
        "faltante": ids[:-1],
        "de-otra-zona": [*ids[:-1], pilot.obonuco[0]],
        "vacio": [],
        "desconocido": [*ids[:-1], uuid.uuid4()],
    }

    response = _submit(api, token, pilot.centro_zone, orders[case])

    assert response.status_code == 422, response.json()
    assert response.json()["code"] == "EVALUATION_ORDER_INVALID"
    assert _order_rows(conn) == 0


def test_body_with_unknown_fields_is_422(api: TestClient, conn: Connection, pilot: Pilot) -> None:
    token = _evaluator_token(api, conn)

    response = api.put(
        f"{CURRENT}/zones/{pilot.centro_zone}/order",
        json={"report_ids": [str(i) for i in pilot.centro], "extra": 1},
        headers=bearer(token),
    )

    assert response.status_code == 422
    assert _order_rows(conn) == 0


def test_second_submission_is_409_and_keeps_the_first(
    api: TestClient, conn: Connection, pilot: Pilot
) -> None:
    token = _evaluator_token(api, conn)
    assert _submit(api, token, pilot.centro_zone, pilot.centro).status_code == 201

    again = _submit(api, token, pilot.centro_zone, list(reversed(pilot.centro)))

    assert (again.status_code, again.json()["code"]) == (409, "EVALUATION_ORDER_ALREADY_SUBMITTED")
    first = (
        conn.execute(text("SELECT id_reporte FROM orden_evaluador ORDER BY posicion"))
        .scalars()
        .all()
    )
    assert first == pilot.centro


def test_concurrent_double_submit_is_409_not_500(
    api: TestClient, conn: Connection, pilot: Pilot, monkeypatch: pytest.MonkeyPatch
) -> None:
    token = _evaluator_token(api, conn)
    assert _submit(api, token, pilot.centro_zone, pilot.centro).status_code == 201
    # Simula que la otra petición guardó justo después de la verificación amistosa.
    monkeypatch.setattr(
        SqlBlindEvaluationRepository, "has_submitted", lambda _self, _r, _u, _z: False
    )

    again = _submit(api, token, pilot.centro_zone, pilot.centro)

    assert (again.status_code, again.json()["code"]) == (409, "EVALUATION_ORDER_ALREADY_SUBMITTED")
    assert _order_rows(conn) == 6


def test_submit_to_unknown_zone_is_404(api: TestClient, conn: Connection, pilot: Pilot) -> None:
    token = _evaluator_token(api, conn)

    response = _submit(api, token, 999999, pilot.centro)

    assert (response.status_code, response.json()["code"]) == (404, "EVALUATION_ZONE_NOT_FOUND")
    assert _order_rows(conn) == 0


def test_submit_with_the_round_closed_is_404(
    api: TestClient, conn: Connection, pilot: Pilot
) -> None:
    token = _evaluator_token(api, conn)
    closed = api.post(f"{ROUNDS}/{pilot.round_id}/close", headers=bearer(pilot.admin))
    assert closed.status_code == 200

    response = _submit(api, token, pilot.centro_zone, pilot.centro)

    assert (response.status_code, response.json()["code"]) == (404, "EVALUATION_NO_OPEN_ROUND")
    assert _order_rows(conn) == 0
