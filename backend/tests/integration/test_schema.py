"""El esquema creado por las migraciones cumple el diagrama ER y las reglas de integridad."""

import uuid
from decimal import Decimal

import pytest
from alembic import command
from sqlalchemy import Connection, inspect, text
from sqlalchemy.exc import IntegrityError

from app.core.database import get_engine
from tests.integration.conftest import alembic_config, insert_report, insert_user, requires_db

pytestmark = [pytest.mark.integration, requires_db]

# Centro de Pasto, solo como coordenada de prueba.
PASTO_LON, PASTO_LAT = -77.2811, 1.2136

ER_TABLES = {
    "usuario": {
        "id_usuario", "nombre", "correo", "password_hash", "rol", "activo",
        "acepta_politica", "fecha_aceptacion", "version_politica", "fecha_registro",
    },
    "reporte": {
        "id_reporte", "id_usuario", "id_zona", "id_via", "ubicacion", "direccion",
        "severidad", "descripcion", "estado", "puntaje_prioridad", "fecha_creacion",
        "clave_idempotencia",
    },
    "confirmacion": {"id_confirmacion", "id_reporte", "id_usuario", "fecha", "distancia_m"},
    "evidencia": {
        "id_evidencia", "id_reporte", "url_foto", "formato", "tamano_bytes", "fecha_subida",
    },
    "historial_estado": {
        "id_historial", "id_reporte", "id_usuario", "estado_anterior", "estado_nuevo",
        "observacion", "fecha_cambio",
    },
    "configuracion_pesos": {
        "id_config", "id_usuario", "w_severidad", "w_flujo", "w_proximidad", "vigente",
        "fecha_creacion",
    },
    "evaluacion_prioridad": {
        "id_evaluacion", "id_reporte", "id_config", "id_servicio", "distancia_servicio_m",
        "s_severidad", "f_flujo", "p_proximidad", "u_utilidad", "fecha_calculo",
    },
    "servicio_critico": {"id_servicio", "osm_id", "nombre", "tipo", "ubicacion"},
    "via": {
        "id_via", "osm_id", "nombre", "jerarquia_vial", "factor_flujo", "geom", "highway_osm",
    },
    "zona": {"id_zona", "nombre", "geom", "concentracion"},
    "token_refresco": {
        "id_token", "id_usuario", "hash_token", "emitido", "expira", "revocado", "reemplazado_por",
    },
    "solicitud_supresion": {
        "id_solicitud", "id_usuario", "estado", "fecha_solicitud", "fecha_atencion",
    },
    "ronda_evaluacion": {
        "id_ronda", "nombre", "estado", "tamano_muestra", "semilla", "id_config", "id_usuario",
        "fecha_apertura", "fecha_cierre",
    },
    "ronda_reporte": {"id_ronda", "id_reporte", "id_zona", "puntaje_u", "orden_motor"},
    "orden_evaluador": {"id_ronda", "id_usuario", "id_reporte", "posicion", "fecha_envio"},
    "aviso_duplicado": {
        "id_aviso", "id_usuario", "id_zona", "fecha", "decision", "id_reporte_resultante",
    },
    "aviso_duplicado_candidato": {"id_aviso", "id_reporte", "distancia_m"},
}  # fmt: skip


def _insert_weights(conn: Connection, s: str, f: str, p: str, current: bool = False) -> None:
    conn.execute(
        text(
            "INSERT INTO configuracion_pesos (w_severidad, w_flujo, w_proximidad, vigente) "
            "VALUES (:s, :f, :p, :current)"
        ),
        {"s": s, "f": f, "p": p, "current": current},
    )


def test_tables_and_columns_match_er_diagram() -> None:
    inspector = inspect(get_engine())

    for table, expected_columns in ER_TABLES.items():
        columns = {column["name"] for column in inspector.get_columns(table)}
        assert columns == expected_columns, table


def test_models_and_migrations_are_in_sync() -> None:
    # Falla si un modelo ORM cambió sin su migración correspondiente.
    command.check(alembic_config())


def test_spatial_columns_use_srid_4326(conn: Connection) -> None:
    rows = conn.execute(
        text(
            "SELECT f_table_name, srid, type FROM geometry_columns "
            "WHERE f_table_schema = 'public' ORDER BY f_table_name"
        )
    ).all()

    assert {(row.f_table_name, row.srid, row.type) for row in rows} == {
        ("reporte", 4326, "POINT"),
        ("servicio_critico", 4326, "POINT"),
        ("via", 4326, "LINESTRING"),
        ("zona", 4326, "POLYGON"),
    }


def test_geography_index_is_used_for_distance_filter(conn: Connection) -> None:
    conn.execute(text("SET LOCAL enable_seqscan = off"))
    plan = "\n".join(
        conn.execute(
            text(
                "EXPLAIN SELECT id_reporte FROM reporte WHERE ST_DWithin("
                "ubicacion::geography, ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography, 25)"
            ),
            {"lon": PASTO_LON, "lat": PASTO_LAT},
        ).scalars()
    )

    assert "ix_reporte_ubicacion_geog" in plan


def test_report_defaults_to_registered_status(conn: Connection) -> None:
    report_id = insert_report(conn, insert_user(conn), PASTO_LON, PASTO_LAT)

    status = conn.execute(
        text("SELECT estado FROM reporte WHERE id_reporte = :id"), {"id": report_id}
    ).scalar_one()

    assert status == "registrado"


@pytest.mark.parametrize("severity", [0, 4])
def test_report_rejects_invalid_severity(conn: Connection, severity: int) -> None:
    user_id = insert_user(conn)

    with pytest.raises(IntegrityError, match="ck_reporte_severidad_valida"):
        conn.execute(
            text(
                "INSERT INTO reporte (id_usuario, ubicacion, severidad) "
                "VALUES (:user_id, ST_SetSRID(ST_MakePoint(-77.28, 1.21), 4326), :severity)"
            ),
            {"user_id": user_id, "severity": severity},
        )


def test_confirmation_is_unique_per_user_and_report(conn: Connection) -> None:
    user_id = insert_user(conn)
    report_id = insert_report(conn, user_id, PASTO_LON, PASTO_LAT)
    confirm = text("INSERT INTO confirmacion (id_reporte, id_usuario) VALUES (:r, :u)")
    conn.execute(confirm, {"r": report_id, "u": user_id})

    with pytest.raises(IntegrityError, match="uq_confirmacion_reporte_usuario"):
        conn.execute(confirm, {"r": report_id, "u": user_id})


def test_email_is_unique(conn: Connection) -> None:
    insert_user(conn, "repetido@example.test")

    with pytest.raises(IntegrityError, match="usuario_correo_key"):
        insert_user(conn, "repetido@example.test")


def test_accepted_policy_requires_date(conn: Connection) -> None:
    with pytest.raises(IntegrityError, match="ck_usuario_aceptacion_con_fecha"):
        conn.execute(
            text(
                "INSERT INTO usuario (nombre, correo, password_hash, acepta_politica) "
                "VALUES ('Prueba', 'sin-fecha@example.test', 'hash', true)"
            )
        )


@pytest.fixture
def empty_weights(conn: Connection) -> Connection:
    """Sin la versión inicial de la migración 0005 (se restaura al revertir la prueba)."""
    conn.execute(text("DELETE FROM configuracion_pesos"))
    return conn


def test_initial_weights_are_loaded_by_the_migration(conn: Connection) -> None:
    rows = conn.execute(
        text(
            "SELECT w_severidad, w_flujo, w_proximidad, id_usuario FROM configuracion_pesos "
            "WHERE vigente"
        )
    ).all()

    assert [tuple(row) for row in rows] == [
        (Decimal("0.50"), Decimal("0.30"), Decimal("0.20"), None)
    ]


def test_weights_summing_one_are_accepted(empty_weights: Connection) -> None:
    _insert_weights(empty_weights, "0.50", "0.30", "0.20", current=True)

    count = empty_weights.execute(text("SELECT count(*) FROM configuracion_pesos")).scalar_one()
    assert count == 1


@pytest.mark.parametrize(
    ("s", "f", "p", "constraint"),
    [
        ("0.50", "0.30", "0.30", "ck_configuracion_pesos_suma"),
        ("0.50", "0.30", "0.19", "ck_configuracion_pesos_suma"),
        ("1.20", "-0.10", "-0.10", "ck_configuracion_pesos_rango"),
    ],
)
def test_weights_outside_rules_are_rejected(
    conn: Connection, s: str, f: str, p: str, constraint: str
) -> None:
    with pytest.raises(IntegrityError, match=constraint):
        _insert_weights(conn, s, f, p)


def test_only_one_weight_config_can_be_current(empty_weights: Connection) -> None:
    _insert_weights(empty_weights, "0.50", "0.30", "0.20", current=True)
    _insert_weights(empty_weights, "0.40", "0.40", "0.20", current=False)

    with pytest.raises(IntegrityError, match="uq_configuracion_pesos_vigente"):
        _insert_weights(empty_weights, "0.60", "0.20", "0.20", current=True)


def test_deleting_report_cascades_to_dependents(conn: Connection) -> None:
    user_id = insert_user(conn)
    report_id = insert_report(conn, user_id, PASTO_LON, PASTO_LAT)
    params = {"r": report_id, "u": user_id}
    conn.execute(text("INSERT INTO confirmacion (id_reporte, id_usuario) VALUES (:r, :u)"), params)
    conn.execute(
        text(
            "INSERT INTO historial_estado (id_reporte, id_usuario, estado_nuevo) "
            "VALUES (:r, :u, 'registrado')"
        ),
        params,
    )

    conn.execute(text("DELETE FROM reporte WHERE id_reporte = :r"), params)

    for table in ("confirmacion", "historial_estado"):
        remaining = conn.execute(
            text(f"SELECT count(*) FROM {table} WHERE id_reporte = :r"),  # noqa: S608
            params,
        ).scalar_one()
        assert remaining == 0, table


def test_user_with_reports_cannot_be_deleted(conn: Connection) -> None:
    user_id = insert_user(conn)
    insert_report(conn, user_id, PASTO_LON, PASTO_LAT)

    with pytest.raises(IntegrityError, match="reporte_id_usuario_fkey"):
        conn.execute(text("DELETE FROM usuario WHERE id_usuario = :u"), {"u": user_id})


def test_downgrade_and_upgrade_round_trip() -> None:
    config = alembic_config()

    command.downgrade(config, "0001")
    assert "reporte" not in inspect(get_engine()).get_table_names()

    command.upgrade(config, "head")
    assert set(ER_TABLES) <= set(inspect(get_engine()).get_table_names())


def test_geography_index_is_used_for_road_matching(conn: Connection) -> None:
    conn.execute(text("SET LOCAL enable_seqscan = off"))
    plan = "\n".join(
        conn.execute(
            text(
                "EXPLAIN SELECT id_via FROM via WHERE ST_DWithin("
                "geom::geography, ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography, 30)"
            ),
            {"lon": PASTO_LON, "lat": PASTO_LAT},
        ).scalars()
    )

    assert "ix_via_geom_geog" in plan


def test_accepted_policy_requires_its_version(conn: Connection) -> None:
    insert = text(
        "INSERT INTO usuario (nombre, correo, password_hash, acepta_politica, "
        "fecha_aceptacion) VALUES ('Prueba', 'v@example.test', 'hash', true, now())"
    )

    with pytest.raises(IntegrityError, match="ck_usuario_aceptacion_con_version"):
        conn.execute(insert)


def _insert_refresh_token(conn: Connection, user_id: object, token_hash: str) -> None:
    conn.execute(
        text(
            "INSERT INTO token_refresco (id_usuario, hash_token, expira) "
            "VALUES (:u, :h, now() + interval '7 days')"
        ),
        {"u": user_id, "h": token_hash},
    )


def test_refresh_token_hash_is_unique(conn: Connection) -> None:
    user_id = insert_user(conn)
    _insert_refresh_token(conn, user_id, "hash-1")

    with pytest.raises(IntegrityError, match="uq_token_refresco_hash_token"):
        _insert_refresh_token(conn, user_id, "hash-1")


def test_refresh_token_must_expire_after_issue(conn: Connection) -> None:
    user_id = insert_user(conn)
    insert = text(
        "INSERT INTO token_refresco (id_usuario, hash_token, expira) "
        "VALUES (:u, 'hash-2', now() - interval '1 second')"
    )

    with pytest.raises(IntegrityError, match="ck_token_refresco_expira_despues"):
        conn.execute(insert, {"u": user_id})


def test_only_one_pending_deletion_request_per_user(conn: Connection) -> None:
    user_id = insert_user(conn)
    insert = text("INSERT INTO solicitud_supresion (id_usuario) VALUES (:u)")
    conn.execute(insert, {"u": user_id})

    with pytest.raises(IntegrityError, match="uq_solicitud_supresion_pendiente"):
        conn.execute(insert, {"u": user_id})


def test_attended_deletion_request_requires_its_date(conn: Connection) -> None:
    user_id = insert_user(conn)
    insert = text("INSERT INTO solicitud_supresion (id_usuario, estado) VALUES (:u, 'atendida')")

    with pytest.raises(IntegrityError, match="ck_solicitud_supresion_atencion_con_fecha"):
        conn.execute(insert, {"u": user_id})


def test_user_with_deletion_request_cannot_be_deleted(conn: Connection) -> None:
    user_id = insert_user(conn)
    conn.execute(text("INSERT INTO solicitud_supresion (id_usuario) VALUES (:u)"), {"u": user_id})

    delete = text("DELETE FROM usuario WHERE id_usuario = :u")

    with pytest.raises(IntegrityError, match="solicitud_supresion_id_usuario_fkey"):
        conn.execute(delete, {"u": user_id})


_INSERT_WITH_KEY = text(
    "INSERT INTO reporte (id_usuario, ubicacion, severidad, clave_idempotencia) "
    "VALUES (:u, ST_SetSRID(ST_MakePoint(-77.28, 1.21), 4326), 2, :k)"
)


def test_idempotency_key_is_unique_per_user(conn: Connection) -> None:
    user_id, key = insert_user(conn), uuid.uuid4()
    conn.execute(_INSERT_WITH_KEY, {"u": user_id, "k": key})

    with pytest.raises(IntegrityError, match="uq_reporte_usuario_clave_idempotencia"):
        conn.execute(_INSERT_WITH_KEY, {"u": user_id, "k": key})


def test_same_idempotency_key_is_allowed_for_another_user(conn: Connection) -> None:
    # Única por par (usuario, clave) y no global: dos clientes no chocan (propuesta 11).
    key = uuid.uuid4()
    first, second = insert_user(conn, "a@example.test"), insert_user(conn, "b@example.test")

    conn.execute(_INSERT_WITH_KEY, {"u": first, "k": key})
    conn.execute(_INSERT_WITH_KEY, {"u": second, "k": key})


def test_idempotency_key_is_optional(conn: Connection) -> None:
    user_id = insert_user(conn)

    conn.execute(_INSERT_WITH_KEY, {"u": user_id, "k": None})
    conn.execute(_INSERT_WITH_KEY, {"u": user_id, "k": None})


# --- Objetivo 4: zonas, rondas de evaluación y avisos de duplicado ----------------------

_POLYGON_WKT = "POLYGON((-77.3 1.2, -77.2 1.2, -77.2 1.3, -77.3 1.3, -77.3 1.2))"


def _insert_zone(
    conn: Connection, name: str = "Zona de prueba", concentration: str = "alta"
) -> int:
    return conn.execute(
        text(
            "INSERT INTO zona (nombre, geom, concentracion) "
            "VALUES (:name, ST_GeomFromText(:wkt, 4326), :concentration) RETURNING id_zona"
        ),
        {"name": name, "wkt": _POLYGON_WKT, "concentration": concentration},
    ).scalar_one()


def _insert_round(conn: Connection, user_id: uuid.UUID, state: str = "abierta") -> uuid.UUID:
    config_id = conn.execute(text("SELECT id_config FROM configuracion_pesos LIMIT 1")).scalar_one()
    return conn.execute(
        text(
            "INSERT INTO ronda_evaluacion (nombre, estado, tamano_muestra, semilla, id_config, "
            "id_usuario) VALUES ('Ronda', :state, 10, 42, :config, :user) RETURNING id_ronda"
        ),
        {"state": state, "config": config_id, "user": user_id},
    ).scalar_one()


def _insert_round_report(
    conn: Connection, round_id: uuid.UUID, report_id: uuid.UUID, zone_id: int, order: int
) -> None:
    conn.execute(
        text(
            "INSERT INTO ronda_reporte (id_ronda, id_reporte, id_zona, puntaje_u, orden_motor) "
            "VALUES (:round, :report, :zone, 7.50, :order)"
        ),
        {"round": round_id, "report": report_id, "zone": zone_id, "order": order},
    )


def test_zone_concentration_is_required_and_valid(conn: Connection) -> None:
    with pytest.raises(IntegrityError, match="concentracion"):
        conn.execute(
            text(
                "INSERT INTO zona (nombre, geom) "
                "VALUES ('Sin concentración', ST_GeomFromText(:wkt, 4326))"
            ),
            {"wkt": _POLYGON_WKT},
        )


def test_zone_name_is_unique(conn: Connection) -> None:
    _insert_zone(conn, "Repetida")

    with pytest.raises(IntegrityError, match="uq_zona_nombre"):
        _insert_zone(conn, "Repetida", "baja")


def test_only_one_open_round(conn: Connection) -> None:
    user_id = insert_user(conn)
    _insert_round(conn, user_id)

    with pytest.raises(IntegrityError, match="uq_ronda_abierta"):
        _insert_round(conn, user_id)


def test_many_closed_rounds_are_allowed(conn: Connection) -> None:
    user_id = insert_user(conn)
    _insert_round(conn, user_id, "cerrada")
    _insert_round(conn, user_id, "cerrada")
    _insert_round(conn, user_id)


def test_round_sample_size_must_be_positive(conn: Connection) -> None:
    user_id = insert_user(conn)

    with pytest.raises(IntegrityError, match="ck_ronda_evaluacion_tamano_positivo"):
        conn.execute(
            text(
                "INSERT INTO ronda_evaluacion (nombre, tamano_muestra, semilla, id_config, "
                "id_usuario) VALUES ('Ronda', 0, 1, "
                "(SELECT id_config FROM configuracion_pesos LIMIT 1), :user)"
            ),
            {"user": user_id},
        )


def test_round_report_order_is_unique_per_zone(conn: Connection) -> None:
    user_id = insert_user(conn)
    zone_id = _insert_zone(conn)
    round_id = _insert_round(conn, user_id)
    first = insert_report(conn, user_id, PASTO_LON, PASTO_LAT)
    second = insert_report(conn, user_id, PASTO_LON + 0.01, PASTO_LAT)
    _insert_round_report(conn, round_id, first, zone_id, 1)

    with pytest.raises(IntegrityError, match="uq_ronda_reporte_zona_orden"):
        _insert_round_report(conn, round_id, second, zone_id, 1)


def test_report_in_round_cannot_be_deleted(conn: Connection) -> None:
    user_id = insert_user(conn)
    zone_id = _insert_zone(conn)
    round_id = _insert_round(conn, user_id)
    report_id = insert_report(conn, user_id, PASTO_LON, PASTO_LAT)
    _insert_round_report(conn, round_id, report_id, zone_id, 1)

    with pytest.raises(IntegrityError, match="ronda_reporte_id_reporte_fkey"):
        conn.execute(text("DELETE FROM reporte WHERE id_reporte = :r"), {"r": report_id})


def test_evaluator_order_requires_the_report_to_be_in_the_round(conn: Connection) -> None:
    user_id = insert_user(conn)
    round_id = _insert_round(conn, user_id)
    outside = insert_report(conn, user_id, PASTO_LON, PASTO_LAT)

    with pytest.raises(IntegrityError, match="orden_evaluador_id_ronda_id_reporte_fkey"):
        conn.execute(
            text(
                "INSERT INTO orden_evaluador (id_ronda, id_usuario, id_reporte, posicion) "
                "VALUES (:round, :user, :report, 1)"
            ),
            {"round": round_id, "user": user_id, "report": outside},
        )


def test_evaluator_order_is_unique_per_report_and_evaluator(conn: Connection) -> None:
    user_id = insert_user(conn)
    zone_id = _insert_zone(conn)
    round_id = _insert_round(conn, user_id)
    report_id = insert_report(conn, user_id, PASTO_LON, PASTO_LAT)
    _insert_round_report(conn, round_id, report_id, zone_id, 1)
    params = {"round": round_id, "user": user_id, "report": report_id}
    insert = text(
        "INSERT INTO orden_evaluador (id_ronda, id_usuario, id_reporte, posicion) "
        "VALUES (:round, :user, :report, 1)"
    )
    conn.execute(insert, params)

    with pytest.raises(IntegrityError, match="orden_evaluador_pkey"):
        conn.execute(insert, params)


def test_deleting_round_cascades_to_its_reports_and_orders(conn: Connection) -> None:
    user_id = insert_user(conn)
    zone_id = _insert_zone(conn)
    round_id = _insert_round(conn, user_id)
    report_id = insert_report(conn, user_id, PASTO_LON, PASTO_LAT)
    _insert_round_report(conn, round_id, report_id, zone_id, 1)
    conn.execute(
        text(
            "INSERT INTO orden_evaluador (id_ronda, id_usuario, id_reporte, posicion) "
            "VALUES (:round, :user, :report, 1)"
        ),
        {"round": round_id, "user": user_id, "report": report_id},
    )

    conn.execute(text("DELETE FROM ronda_evaluacion WHERE id_ronda = :r"), {"r": round_id})

    for table in ("ronda_reporte", "orden_evaluador"):
        remaining = conn.execute(text(f"SELECT count(*) FROM {table}")).scalar_one()  # noqa: S608
        assert remaining == 0, table


def test_duplicate_warning_defaults_to_pending_and_cascades_candidates(conn: Connection) -> None:
    user_id = insert_user(conn)
    report_id = insert_report(conn, user_id, PASTO_LON, PASTO_LAT)
    warning_id = conn.execute(
        text("INSERT INTO aviso_duplicado (id_usuario) VALUES (:u) RETURNING id_aviso"),
        {"u": user_id},
    ).scalar_one()
    conn.execute(
        text(
            "INSERT INTO aviso_duplicado_candidato (id_aviso, id_reporte, distancia_m) "
            "VALUES (:w, :r, 12.50)"
        ),
        {"w": warning_id, "r": report_id},
    )

    decision = conn.execute(
        text("SELECT decision FROM aviso_duplicado WHERE id_aviso = :w"), {"w": warning_id}
    ).scalar_one()
    conn.execute(text("DELETE FROM reporte WHERE id_reporte = :r"), {"r": report_id})
    candidates = conn.execute(text("SELECT count(*) FROM aviso_duplicado_candidato")).scalar_one()

    assert decision == "pendiente"
    assert candidates == 0


def test_duplicate_warning_keeps_its_row_when_the_resulting_report_is_deleted(
    conn: Connection,
) -> None:
    user_id = insert_user(conn)
    report_id = insert_report(conn, user_id, PASTO_LON, PASTO_LAT)
    warning_id = conn.execute(
        text(
            "INSERT INTO aviso_duplicado (id_usuario, decision, id_reporte_resultante) "
            "VALUES (:u, 'creo_igual', :r) RETURNING id_aviso"
        ),
        {"u": user_id, "r": report_id},
    ).scalar_one()

    conn.execute(text("DELETE FROM reporte WHERE id_reporte = :r"), {"r": report_id})

    result = conn.execute(
        text("SELECT id_reporte_resultante FROM aviso_duplicado WHERE id_aviso = :w"),
        {"w": warning_id},
    ).scalar_one()
    assert result is None


def test_user_with_duplicate_warnings_cannot_be_deleted(conn: Connection) -> None:
    # Las cuentas se anonimizan (decisión 23a): borrar una no debe llevarse sus avisos.
    user_id = insert_user(conn)
    conn.execute(text("INSERT INTO aviso_duplicado (id_usuario) VALUES (:u)"), {"u": user_id})

    with pytest.raises(IntegrityError, match="aviso_duplicado_id_usuario_fkey"):
        conn.execute(text("DELETE FROM usuario WHERE id_usuario = :u"), {"u": user_id})


def test_evaluator_role_exists(conn: Connection) -> None:
    user_id = insert_user(conn)

    conn.execute(text("UPDATE usuario SET rol = 'evaluador' WHERE id_usuario = :u"), {"u": user_id})

    role = conn.execute(
        text("SELECT rol FROM usuario WHERE id_usuario = :u"), {"u": user_id}
    ).scalar_one()
    assert role == "evaluador"
