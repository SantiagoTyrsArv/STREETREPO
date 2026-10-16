"""El esquema creado por las migraciones cumple el diagrama ER y las reglas de integridad."""

from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import Connection, inspect, text
from sqlalchemy.exc import IntegrityError

from app.core.database import get_engine
from tests.integration.conftest import insert_report, insert_user, requires_db

pytestmark = [pytest.mark.integration, requires_db]

BACKEND_DIR = Path(__file__).resolve().parents[2]

# Centro de Pasto, solo como coordenada de prueba.
PASTO_LON, PASTO_LAT = -77.2811, 1.2136

ER_TABLES = {
    "usuario": {
        "id_usuario", "nombre", "correo", "password_hash", "rol", "activo",
        "acepta_politica", "fecha_aceptacion", "fecha_registro",
    },
    "reporte": {
        "id_reporte", "id_usuario", "id_zona", "id_via", "ubicacion", "direccion",
        "severidad", "descripcion", "estado", "puntaje_prioridad", "fecha_creacion",
    },
    "confirmacion": {"id_confirmacion", "id_reporte", "id_usuario", "fecha"},
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
    "zona": {"id_zona", "nombre", "geom"},
}  # fmt: skip


def _alembic_config() -> Config:
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_DIR / "migrations"))
    return config


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
    command.check(_alembic_config())


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


def test_weights_summing_one_are_accepted(conn: Connection) -> None:
    _insert_weights(conn, "0.50", "0.30", "0.20", current=True)

    count = conn.execute(text("SELECT count(*) FROM configuracion_pesos")).scalar_one()
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


def test_only_one_weight_config_can_be_current(conn: Connection) -> None:
    _insert_weights(conn, "0.50", "0.30", "0.20", current=True)
    _insert_weights(conn, "0.40", "0.40", "0.20", current=False)

    with pytest.raises(IntegrityError, match="uq_configuracion_pesos_vigente"):
        _insert_weights(conn, "0.60", "0.20", "0.20", current=True)


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
    config = _alembic_config()

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
