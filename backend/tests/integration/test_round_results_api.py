"""Resultados de la ronda y ficha comparativa contra PostGIS real (objetivo 4, HU-09)."""

import csv
import io
import uuid

import pytest
from fastapi.testclient import TestClient
from httpx import Response
from sqlalchemy import Connection, text
from sqlalchemy.orm import Session

from app.modules.validation.domain.agreement import (
    BetweenZones,
    ZoneAgreement,
    ZoneRanking,
    between_zones,
    zone_agreement,
)
from app.modules.validation.domain.zones import Concentration
from tests.integration.conftest import bearer, insert_user, requires_db
from tests.integration.test_blind_evaluation_api import (
    ROUNDS,
    Pilot,
    _evaluator_token,
    _submit,
    _user_id,
)

pytestmark = [pytest.mark.integration, requires_db]

BOM = "﻿"
EVA_1 = "eva.uno@example.com"
EVA_2 = "eva.dos@example.com"


def _motor_order(conn: Connection, round_id: str, zone_id: int) -> dict[uuid.UUID, int]:
    rows = conn.execute(
        text(
            "SELECT id_reporte, orden_motor FROM ronda_reporte "
            "WHERE id_ronda = :r AND id_zona = :z ORDER BY orden_motor"
        ),
        {"r": round_id, "z": zone_id},
    ).all()
    return {row.id_reporte: row.orden_motor for row in rows}


class Evaluated:
    """El piloto con dos evaluadores que enviaron sus órdenes en ambas zonas."""

    def __init__(self, api: TestClient, conn: Connection, pilot: Pilot) -> None:
        self.pilot = pilot
        self.motor = {
            zone: _motor_order(conn, pilot.round_id, zone)
            for zone in (pilot.centro_zone, pilot.obonuco_zone)
        }
        first, second = _evaluator_token(api, conn, EVA_1), _evaluator_token(api, conn, EVA_2)
        self.evaluators: dict[uuid.UUID, dict[int, dict[uuid.UUID, int]]] = {
            _user_id(conn, EVA_1): {},
            _user_id(conn, EVA_2): {},
        }
        for zone, motor in self.motor.items():
            by_motor = list(motor)
            # Uno coincide con el motor salvo un intercambio; el otro lo invierte.
            swapped = [by_motor[1], by_motor[0], *by_motor[2:]]
            for token, evaluator, ids in (
                (first, _user_id(conn, EVA_1), swapped),
                (second, _user_id(conn, EVA_2), list(reversed(by_motor))),
            ):
                assert _submit(api, token, zone, ids).status_code == 201
                self.evaluators[evaluator][zone] = {r: i for i, r in enumerate(ids, start=1)}

    def close(self, api: TestClient) -> None:
        response = api.post(
            f"{ROUNDS}/{self.pilot.round_id}/close", headers=bearer(self.pilot.admin)
        )
        assert response.status_code == 200

    def expected(self, zone: int, concentration: Concentration) -> ZoneAgreement:
        agreement = zone_agreement(
            ZoneRanking(
                zone_id=zone,
                concentration=concentration,
                motor_order=self.motor[zone],
                evaluator_orders={e: orders[zone] for e, orders in self.evaluators.items()},
            )
        )
        assert agreement is not None
        return agreement


@pytest.fixture(name="pilot")
def _pilot(api: TestClient, session: Session, conn: Connection) -> Pilot:
    return Pilot(api, session, conn)


@pytest.fixture
def evaluated(api: TestClient, conn: Connection, pilot: Pilot) -> Evaluated:
    return Evaluated(api, conn, pilot)


def _get(api: TestClient, pilot: Pilot, path: str) -> Response:
    return api.get(f"{ROUNDS}/{pilot.round_id}/{path}", headers=bearer(pilot.admin))


def _csv_rows(response: Response) -> list[dict[str, str]]:
    body = response.content.decode("utf-8")
    assert body.startswith(BOM)
    return list(csv.DictReader(io.StringIO(body[len(BOM) :])))


def test_results_match_the_agreement_functions_on_the_stored_orders(
    api: TestClient, evaluated: Evaluated
) -> None:
    evaluated.close(api)
    pilot = evaluated.pilot

    response = _get(api, pilot, "results")

    assert response.status_code == 200, response.json()
    body = response.json()
    zones = {zone["name"]: zone for zone in body["zones"]}
    centro = evaluated.expected(pilot.centro_zone, Concentration.HIGH)
    obonuco = evaluated.expected(pilot.obonuco_zone, Concentration.LOW)
    for name, expected in (("Centro", centro), ("Obonuco", obonuco)):
        agreement = zones[name]["agreement"]
        assert expected.spearman is not None
        assert expected.kendall_w is not None
        assert agreement["spearman"]["coefficient"] == pytest.approx(expected.spearman.coefficient)
        assert agreement["kendall_w"]["w"] == pytest.approx(expected.kendall_w.w)
        assert agreement["within_one_pct"] == pytest.approx(expected.within_one_pct)
        assert [e["evaluator"] for e in agreement["per_evaluator"]] == [
            "Evaluador 1",
            "Evaluador 2",
        ]
        panel = {r["report_id"]: r["panel_order"] for r in zones[name]["reports"]}
        assert panel == {str(k): pytest.approx(v) for k, v in expected.panel_order.items()}
    between = between_zones([(Concentration.HIGH, centro), (Concentration.LOW, obonuco)])
    assert body["between"]["computable"] == isinstance(between, BetweenZones)
    if isinstance(between, BetweenZones):
        assert body["between"]["p_value"] == pytest.approx(between.p_value)
    assert (zones["Centro"]["n_reports"], zones["Obonuco"]["n_reports"]) == (6, 5)
    assert zones["Centro"]["dedup"]["reports"] == 6
    # El panel identifica cada reporte por su vía (Figma «Ranking comparado»).
    assert {r["road_name"] for r in zones["Centro"]["reports"]} == {"Carrera 27"}
    assert {r["road_name"] for r in zones["Obonuco"]["reports"]} == {None}


def test_a_zone_nobody_ordered_has_no_agreement(
    api: TestClient,
    conn: Connection,
    pilot: Pilot,
) -> None:
    token = _evaluator_token(api, conn, EVA_1)
    ids = list(_motor_order(conn, pilot.round_id, pilot.centro_zone))
    assert _submit(api, token, pilot.centro_zone, ids).status_code == 201
    api.post(f"{ROUNDS}/{pilot.round_id}/close", headers=bearer(pilot.admin))

    body = _get(api, pilot, "results").json()

    zones = {zone["name"]: zone for zone in body["zones"]}
    assert zones["Obonuco"]["agreement"] is None
    assert {r["panel_order"] for r in zones["Obonuco"]["reports"]} == {None}
    assert body["between"]["computable"] is False


def test_results_of_an_open_round_are_409(api: TestClient, pilot: Pilot) -> None:
    for path in ("results", "export/ficha.csv", "export/resumen.csv"):
        response = _get(api, pilot, path)

        assert response.status_code == 409, path
        assert response.json()["code"] == "EVALUATION_ROUND_STILL_OPEN"


def test_review_files_are_served_while_the_round_is_open(
    api: TestClient,
    pilot: Pilot,
) -> None:
    reports = _get(api, pilot, "export/reportes.csv")
    warnings = _get(api, pilot, "export/avisos.csv")

    assert reports.status_code == 200
    assert len(_csv_rows(reports)) == 11
    assert warnings.status_code == 200
    assert _csv_rows(warnings) == []


def test_unknown_round_is_404(api: TestClient, pilot: Pilot) -> None:
    for path in ("results", "export/ficha.csv", "export/reportes.csv", "export/avisos.csv"):
        response = api.get(f"{ROUNDS}/{uuid.uuid4()}/{path}", headers=bearer(pilot.admin))

        assert response.status_code == 404, path


def test_the_ficha_is_a_csv_download_without_evaluator_identities(
    api: TestClient, evaluated: Evaluated
) -> None:
    evaluated.close(api)

    response = _get(api, evaluated.pilot, "export/ficha.csv")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert response.headers["content-disposition"] == (
        'attachment; filename="ronda-piloto-1-ficha.csv"'
    )
    assert response.headers["cache-control"] == "private, no-store"
    rows = _csv_rows(response)
    assert len(rows) == 11
    assert {"orden_evaluador_1", "orden_evaluador_2"} <= set(rows[0])
    text_body = response.content.decode("utf-8") + _get(
        api, evaluated.pilot, "export/resumen.csv"
    ).content.decode("utf-8")
    for secret in (EVA_1, EVA_2, "eva.uno", *map(str, evaluated.evaluators)):
        assert secret not in text_body


def test_the_summary_csv_has_zones_and_the_test_between_zones(
    api: TestClient, evaluated: Evaluated
) -> None:
    evaluated.close(api)

    rows = _csv_rows(_get(api, evaluated.pilot, "export/resumen.csv"))

    assert [row["zona"] for row in rows] == ["Centro", "Obonuco", "entre_zonas"]
    assert rows[0]["evaluadores"] == "2"


def test_the_warnings_csv_lists_the_warnings_of_the_zones(
    api: TestClient,
    conn: Connection,
    pilot: Pilot,
) -> None:
    citizen = insert_user(conn, "vecina@example.test")
    target = pilot.centro[0]
    warning_id = conn.execute(
        text(
            "INSERT INTO aviso_duplicado (id_usuario, id_zona, decision, id_reporte_resultante) "
            "VALUES (:u, :z, 'confirmo', :r) RETURNING id_aviso"
        ),
        {"u": citizen, "z": pilot.centro_zone, "r": target},
    ).scalar_one()
    conn.execute(
        text(
            "INSERT INTO aviso_duplicado_candidato (id_aviso, id_reporte, distancia_m) "
            "VALUES (:w, :r, 4.25)"
        ),
        {"w": warning_id, "r": target},
    )
    # Un aviso fuera de toda zona no entra en la revisión de la ronda.
    conn.execute(text("INSERT INTO aviso_duplicado (id_usuario) VALUES (:u)"), {"u": citizen})

    rows = _csv_rows(_get(api, pilot, "export/avisos.csv"))

    assert rows == [
        {
            "id_aviso": str(warning_id),
            "zona": "Centro",
            "fecha": rows[0]["fecha"],
            "decision": "confirmo",
            "id_reporte_resultante": str(target),
            "candidatos": f"{target}:4.25",
        }
    ]
    assert "vecina" not in _get(api, pilot, "export/avisos.csv").text


def test_evaluators_cannot_read_results(
    api: TestClient,
    conn: Connection,
    pilot: Pilot,
) -> None:
    token = _evaluator_token(api, conn, EVA_1)

    for path in ("results", "export/ficha.csv", "export/avisos.csv"):
        response = api.get(f"{ROUNDS}/{pilot.round_id}/{path}", headers=bearer(token))

        assert response.status_code == 403, path
