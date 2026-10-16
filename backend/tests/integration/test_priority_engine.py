"""Motor de priorización y versiones de pesos contra PostGIS real.

Como en las pruebas de map-matching, las geometrías están en el océano Pacífico,
sobre el ecuador, lejos de los datos reales de Pasto de la base de desarrollo.
"""

import uuid
from decimal import Decimal

import pytest
from sqlalchemy import Connection, text
from sqlalchemy.orm import Session

from app.modules.critical_services.infrastructure.locator import PostgisCriticalServiceLocator
from app.modules.priority.application.evaluate_report import ReportEvaluator
from app.modules.priority.application.update_weights import UpdateWeights
from app.modules.priority.domain.weights import DEFAULT_WEIGHTS, Weights
from app.modules.priority.infrastructure.evaluation_repository import SqlEvaluationRepository
from app.modules.priority.infrastructure.reports_reader import SqlReportsToEvaluate
from app.modules.priority.infrastructure.weights_repository import SqlWeightVersionRepository
from app.modules.reports.domain.severity import Severity
from app.modules.reports.domain.status import ReportStatus
from app.modules.reports.infrastructure.status_history import SqlStatusHistoryRecorder
from app.modules.roads.infrastructure.matcher import PostgisRoadMatcher
from tests.integration.conftest import TEST_OSM_ID, insert_user, requires_db

pytestmark = [pytest.mark.integration, requires_db]

LON, LAT = -80.0, 0.0
# Desplazamiento hacia el norte en grados: en el ecuador 1° de latitud ≈ 110 574 m.
METERS_PER_DEGREE_LAT = 110_574.0
NEW_WEIGHTS = Weights(Decimal("0.40"), Decimal("0.40"), Decimal("0.20"))


def _insert_report(
    conn: Connection,
    user_id: uuid.UUID,
    *,
    lon: float = LON,
    lat: float = LAT,
    severity: Severity = Severity.HIGH,
    status: ReportStatus = ReportStatus.REGISTERED,
) -> uuid.UUID:
    return conn.execute(
        text(
            "INSERT INTO reporte (id_usuario, ubicacion, severidad, estado) "
            "VALUES (:user_id, ST_SetSRID(ST_MakePoint(:lon, :lat), 4326), :severity, "
            "CAST(:status AS estado_reporte)) RETURNING id_reporte"
        ),
        {"user_id": user_id, "lon": lon, "lat": lat, "severity": severity, "status": status},
    ).scalar_one()


def _insert_secondary_road_through_origin(conn: Connection) -> int:
    return conn.execute(
        text(
            "INSERT INTO via (osm_id, nombre, highway_osm, jerarquia_vial, factor_flujo, geom) "
            "VALUES (:osm_id, 'Vía de prueba', 'secondary', 'secundaria', 7, "
            "ST_GeomFromText(:wkt, 4326)) RETURNING id_via"
        ),
        {
            "osm_id": TEST_OSM_ID + 101,
            "wkt": f"LINESTRING({LON - 0.001} {LAT}, {LON + 0.001} {LAT})",
        },
    ).scalar_one()


def _insert_hospital_north_of_origin(conn: Connection, distance_m: float) -> int:
    return conn.execute(
        text(
            "INSERT INTO servicio_critico (osm_id, nombre, tipo, ubicacion) "
            "VALUES (:osm_id, 'Hospital de prueba', 'hospital', "
            "ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)) RETURNING id_servicio"
        ),
        {"osm_id": TEST_OSM_ID + 102, "lon": LON, "lat": LAT + distance_m / METERS_PER_DEGREE_LAT},
    ).scalar_one()


def _evaluator(session: Session) -> ReportEvaluator:
    return ReportEvaluator(
        reports=SqlReportsToEvaluate(session),
        weights=SqlWeightVersionRepository(session),
        evaluations=SqlEvaluationRepository(session),
        statuses=SqlStatusHistoryRecorder(session),
        road_matcher=PostgisRoadMatcher(session),
        service_locator=PostgisCriticalServiceLocator(session),
    )


def _report_row(conn: Connection, report_id: uuid.UUID) -> tuple[object, ...]:
    return tuple(
        conn.execute(
            text(
                "SELECT estado::text, puntaje_prioridad, id_via FROM reporte WHERE id_reporte = :id"
            ),
            {"id": report_id},
        ).one()
    )


def test_current_weights_are_the_initial_system_version(session: Session) -> None:
    current = SqlWeightVersionRepository(session).get_current()

    assert current is not None
    assert current.weights == DEFAULT_WEIGHTS
    assert current.created_by is None


def test_new_version_replaces_the_current_one_and_keeps_history(
    conn: Connection, session: Session
) -> None:
    admin_id = insert_user(conn, "admin@example.test")
    repository = SqlWeightVersionRepository(session)
    initial = repository.get_current()

    created = repository.add_current(NEW_WEIGHTS, created_by=admin_id)

    assert repository.get_current() == created
    assert created.created_by == admin_id
    versions = repository.list_versions(limit=10, offset=0)
    assert [v.id for v in versions[:2]] == [created.id, initial.id if initial else None]
    assert [v.is_current for v in versions[:2]] == [True, False]
    assert repository.list_versions(limit=1, offset=1)[0].id == versions[1].id


def test_evaluating_a_report_stores_a_reproducible_evaluation(
    conn: Connection, session: Session
) -> None:
    road_id = _insert_secondary_road_through_origin(conn)
    service_id = _insert_hospital_north_of_origin(conn, distance_m=180.0)
    report_id = _insert_report(conn, insert_user(conn))

    result = _evaluator(session).evaluate(report_id)

    # S = 10, F = 7, P ≈ 8 -> U ≈ 8,70 (Av. Los Estudiantes del diseño).
    assert result.urgency_score == Decimal("8.70")
    evaluation = conn.execute(
        text(
            "SELECT e.s_severidad, e.f_flujo, e.p_proximidad, e.u_utilidad, e.id_servicio, "
            "e.distancia_servicio_m, c.vigente "
            "FROM evaluacion_prioridad e JOIN configuracion_pesos c USING (id_config) "
            "WHERE e.id_reporte = :id"
        ),
        {"id": report_id},
    ).one()
    assert evaluation.s_severidad == Decimal("10.00")
    assert evaluation.f_flujo == Decimal("7.00")
    assert evaluation.p_proximidad == result.proximity_score
    assert evaluation.u_utilidad == Decimal("8.70")
    assert evaluation.id_servicio == service_id
    assert abs(evaluation.distancia_servicio_m - Decimal("180")) < 1
    assert evaluation.vigente is True
    assert _report_row(conn, report_id) == ("evaluado", Decimal("8.70"), road_id)


def test_automatic_evaluation_is_recorded_in_the_history(
    conn: Connection, session: Session
) -> None:
    report_id = _insert_report(conn, insert_user(conn))

    _evaluator(session).evaluate(report_id)

    history = conn.execute(
        text(
            "SELECT estado_anterior::text, estado_nuevo::text, id_usuario "
            "FROM historial_estado WHERE id_reporte = :id"
        ),
        {"id": report_id},
    ).all()
    assert [tuple(row) for row in history] == [("registrado", "evaluado", None)]


def test_report_without_road_needs_review(conn: Connection, session: Session) -> None:
    report_id = _insert_report(conn, insert_user(conn), severity=Severity.MEDIUM)

    result = _evaluator(session).evaluate(report_id)

    # Sector Obonuco del diseño: S = 6, F = 2, P = 0 -> U = 3,60.
    assert result.needs_road_review is True
    assert _report_row(conn, report_id) == ("evaluado", Decimal("3.60"), None)


def test_update_weights_recalculates_only_active_reports(
    conn: Connection, session: Session
) -> None:
    _insert_secondary_road_through_origin(conn)
    _insert_hospital_north_of_origin(conn, distance_m=180.0)
    user_id = insert_user(conn)
    admin_id = insert_user(conn, "admin@example.test")
    prioritized = _insert_report(conn, user_id, status=ReportStatus.PRIORITIZED)
    repaired = _insert_report(conn, user_id, status=ReportStatus.REPAIRED)
    reports = SqlReportsToEvaluate(session)
    use_case = UpdateWeights(
        weights=SqlWeightVersionRepository(session),
        reports=reports,
        evaluator=_evaluator(session),
        transaction=session,
    )

    result = use_case.execute(NEW_WEIGHTS, admin_id)

    assert result.recalculated_reports == len(reports.list_active())
    # 0,4·10 + 0,4·7 + 0,2·8 = 8,40; el estado no cambia en un recálculo.
    assert _report_row(conn, prioritized)[:2] == ("priorizado", Decimal("8.40"))
    assert _report_row(conn, repaired)[:2] == ("reparado", None)
    config_ids = conn.execute(
        text("SELECT id_config FROM evaluacion_prioridad WHERE id_reporte = :id"),
        {"id": prioritized},
    ).scalars()
    assert list(config_ids) == [result.version.id]
