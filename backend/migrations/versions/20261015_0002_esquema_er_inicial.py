"""Esquema inicial según el diagrama ER (Lucid: "Street Repo - Diagrama Entidad-Relación").

Crea las 10 entidades del diagrama con sus claves, restricciones de integridad
(guía 5) e índices espaciales y de ranking (guía 11).

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-15
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from geoalchemy2 import Geometry
from sqlalchemy.dialects import postgresql

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SRID = 4326

rol_usuario = postgresql.ENUM("ciudadano", "administrador", name="rol_usuario")
estado_reporte = postgresql.ENUM(
    "registrado", "evaluado", "priorizado", "reparado", name="estado_reporte"
)
jerarquia_vial = postgresql.ENUM(
    "primaria", "secundaria", "terciaria", "residencial", name="jerarquia_vial"
)
tipo_servicio = postgresql.ENUM("hospital", "escuela", name="tipo_servicio")
ENUM_TYPES = (rol_usuario, estado_reporte, jerarquia_vial, tipo_servicio)


def _ref(enum: postgresql.ENUM) -> postgresql.ENUM:
    """Referencia a un ENUM ya creado (evita que create_table lo cree otra vez)."""
    return postgresql.ENUM(*enum.enums, name=enum.name, create_type=False)


def _point() -> Geometry:
    return Geometry("POINT", srid=SRID, spatial_index=False)


def _timestamp(name: str) -> sa.Column[sa.DateTime]:
    return sa.Column(name, sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False)


def _uuid_pk(name: str) -> sa.Column[sa.Uuid[str]]:
    return sa.Column(name, sa.Uuid(), server_default=sa.text("gen_random_uuid()"), primary_key=True)


def _gist(name: str, table: str, column: str) -> None:
    op.create_index(name, table, [column], postgresql_using="gist")


def _gist_geography(name: str, table: str, column: str) -> None:
    # Las distancias en metros se calculan sobre geography (ADR 0003).
    op.create_index(
        name, table, [sa.literal_column(f"({column}::geography)")], postgresql_using="gist"
    )


def upgrade() -> None:
    bind = op.get_bind()
    for enum in ENUM_TYPES:
        enum.create(bind, checkfirst=False)

    op.create_table(
        "usuario",
        _uuid_pk("id_usuario"),
        sa.Column("nombre", sa.String(100), nullable=False),
        sa.Column("correo", sa.String(150), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("rol", _ref(rol_usuario), server_default="ciudadano", nullable=False),
        sa.Column("activo", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column(
            "acepta_politica", sa.Boolean(), server_default=sa.text("false"), nullable=False
        ),
        sa.Column("fecha_aceptacion", sa.DateTime(timezone=True), nullable=True),
        _timestamp("fecha_registro"),
        sa.CheckConstraint(
            "NOT acepta_politica OR fecha_aceptacion IS NOT NULL",
            name="ck_usuario_aceptacion_con_fecha",
        ),
    )

    op.create_table(
        "zona",
        sa.Column("id_zona", sa.Integer(), primary_key=True),
        sa.Column("nombre", sa.String(100), nullable=False),
        sa.Column("geom", Geometry("POLYGON", srid=SRID, spatial_index=False), nullable=False),
    )
    _gist("ix_zona_geom", "zona", "geom")

    op.create_table(
        "via",
        sa.Column("id_via", sa.Integer(), primary_key=True),
        sa.Column("osm_id", sa.BigInteger(), nullable=False, unique=True),
        sa.Column("nombre", sa.String(150), nullable=True),
        sa.Column("jerarquia_vial", _ref(jerarquia_vial), nullable=False),
        sa.Column("factor_flujo", sa.Numeric(4, 2), nullable=False),
        sa.CheckConstraint("factor_flujo BETWEEN 0 AND 10", name="ck_via_factor_flujo_rango"),
    )

    op.create_table(
        "servicio_critico",
        sa.Column("id_servicio", sa.Integer(), primary_key=True),
        sa.Column("osm_id", sa.BigInteger(), nullable=False, unique=True),
        sa.Column("nombre", sa.String(150), nullable=True),
        sa.Column("tipo", _ref(tipo_servicio), nullable=False),
        sa.Column("ubicacion", _point(), nullable=False),
    )
    _gist("ix_servicio_critico_ubicacion", "servicio_critico", "ubicacion")
    _gist_geography("ix_servicio_critico_ubicacion_geog", "servicio_critico", "ubicacion")

    op.create_table(
        "configuracion_pesos",
        sa.Column("id_config", sa.Integer(), primary_key=True),
        sa.Column(
            "id_usuario",
            sa.Uuid(),
            sa.ForeignKey("usuario.id_usuario", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("w_severidad", sa.Numeric(3, 2), nullable=False),
        sa.Column("w_flujo", sa.Numeric(3, 2), nullable=False),
        sa.Column("w_proximidad", sa.Numeric(3, 2), nullable=False),
        sa.Column("vigente", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        _timestamp("fecha_creacion"),
        sa.CheckConstraint(
            "w_severidad BETWEEN 0 AND 1 AND w_flujo BETWEEN 0 AND 1 "
            "AND w_proximidad BETWEEN 0 AND 1",
            name="ck_configuracion_pesos_rango",
        ),
        sa.CheckConstraint(
            "w_severidad + w_flujo + w_proximidad = 1.00", name="ck_configuracion_pesos_suma"
        ),
    )
    op.create_index(
        "uq_configuracion_pesos_vigente",
        "configuracion_pesos",
        ["vigente"],
        unique=True,
        postgresql_where=sa.text("vigente"),
    )

    op.create_table(
        "reporte",
        _uuid_pk("id_reporte"),
        sa.Column(
            "id_usuario",
            sa.Uuid(),
            sa.ForeignKey("usuario.id_usuario", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "id_zona", sa.Integer(), sa.ForeignKey("zona.id_zona", ondelete="SET NULL"), nullable=True
        ),
        sa.Column(
            "id_via", sa.Integer(), sa.ForeignKey("via.id_via", ondelete="SET NULL"), nullable=True
        ),
        sa.Column("ubicacion", _point(), nullable=False),
        sa.Column("direccion", sa.String(255), nullable=True),
        sa.Column("severidad", sa.SmallInteger(), nullable=False),
        sa.Column("descripcion", sa.Text(), nullable=True),
        sa.Column("estado", _ref(estado_reporte), server_default="registrado", nullable=False),
        sa.Column("puntaje_prioridad", sa.Numeric(4, 2), nullable=True),
        _timestamp("fecha_creacion"),
        sa.CheckConstraint("severidad BETWEEN 1 AND 3", name="ck_reporte_severidad_valida"),
        sa.CheckConstraint(
            "puntaje_prioridad BETWEEN 0 AND 10", name="ck_reporte_puntaje_prioridad_rango"
        ),
    )
    _gist("ix_reporte_ubicacion", "reporte", "ubicacion")
    _gist_geography("ix_reporte_ubicacion_geog", "reporte", "ubicacion")
    op.create_index(
        "ix_reporte_estado_puntaje",
        "reporte",
        ["estado", sa.literal_column("puntaje_prioridad DESC")],
    )
    op.create_index("ix_reporte_fecha_creacion", "reporte", ["fecha_creacion"])
    op.create_index("ix_reporte_id_usuario", "reporte", ["id_usuario"])

    op.create_table(
        "evidencia",
        _uuid_pk("id_evidencia"),
        sa.Column(
            "id_reporte",
            sa.Uuid(),
            sa.ForeignKey("reporte.id_reporte", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("url_foto", sa.String(255), nullable=False),
        sa.Column("formato", sa.String(10), nullable=False),
        sa.Column("tamano_bytes", sa.Integer(), nullable=False),
        _timestamp("fecha_subida"),
        sa.CheckConstraint("tamano_bytes > 0", name="ck_evidencia_tamano_positivo"),
    )
    op.create_index("ix_evidencia_id_reporte", "evidencia", ["id_reporte"])

    op.create_table(
        "confirmacion",
        _uuid_pk("id_confirmacion"),
        sa.Column(
            "id_reporte",
            sa.Uuid(),
            sa.ForeignKey("reporte.id_reporte", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "id_usuario",
            sa.Uuid(),
            sa.ForeignKey("usuario.id_usuario", ondelete="CASCADE"),
            nullable=False,
        ),
        _timestamp("fecha"),
        sa.UniqueConstraint("id_reporte", "id_usuario", name="uq_confirmacion_reporte_usuario"),
    )

    op.create_table(
        "historial_estado",
        sa.Column("id_historial", sa.BigInteger(), primary_key=True),
        sa.Column(
            "id_reporte",
            sa.Uuid(),
            sa.ForeignKey("reporte.id_reporte", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "id_usuario",
            sa.Uuid(),
            sa.ForeignKey("usuario.id_usuario", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("estado_anterior", _ref(estado_reporte), nullable=True),
        sa.Column("estado_nuevo", _ref(estado_reporte), nullable=False),
        sa.Column("observacion", sa.Text(), nullable=True),
        _timestamp("fecha_cambio"),
    )
    op.create_index(
        "ix_historial_estado_reporte_fecha", "historial_estado", ["id_reporte", "fecha_cambio"]
    )

    op.create_table(
        "evaluacion_prioridad",
        sa.Column("id_evaluacion", sa.BigInteger(), primary_key=True),
        sa.Column(
            "id_reporte",
            sa.Uuid(),
            sa.ForeignKey("reporte.id_reporte", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "id_config",
            sa.Integer(),
            sa.ForeignKey("configuracion_pesos.id_config", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "id_servicio",
            sa.Integer(),
            sa.ForeignKey("servicio_critico.id_servicio", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("distancia_servicio_m", sa.Numeric(8, 2), nullable=True),
        sa.Column("s_severidad", sa.Numeric(4, 2), nullable=False),
        sa.Column("f_flujo", sa.Numeric(4, 2), nullable=False),
        sa.Column("p_proximidad", sa.Numeric(4, 2), nullable=False),
        sa.Column("u_utilidad", sa.Numeric(4, 2), nullable=False),
        _timestamp("fecha_calculo"),
        sa.CheckConstraint(
            "s_severidad BETWEEN 0 AND 10 AND f_flujo BETWEEN 0 AND 10 "
            "AND p_proximidad BETWEEN 0 AND 10 AND u_utilidad BETWEEN 0 AND 10",
            name="ck_evaluacion_prioridad_factores_rango",
        ),
        sa.CheckConstraint(
            "distancia_servicio_m >= 0", name="ck_evaluacion_prioridad_distancia_positiva"
        ),
    )
    op.create_index(
        "ix_evaluacion_prioridad_reporte_fecha",
        "evaluacion_prioridad",
        ["id_reporte", "fecha_calculo"],
    )
    op.create_index("ix_evaluacion_prioridad_id_config", "evaluacion_prioridad", ["id_config"])


def downgrade() -> None:
    # Orden inverso a las dependencias; los índices caen con sus tablas.
    for table in (
        "evaluacion_prioridad",
        "historial_estado",
        "confirmacion",
        "evidencia",
        "reporte",
        "configuracion_pesos",
        "servicio_critico",
        "via",
        "zona",
        "usuario",
    ):
        op.drop_table(table)
    bind = op.get_bind()
    for enum in reversed(ENUM_TYPES):
        enum.drop(bind, checkfirst=False)
