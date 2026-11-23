"""Esquema del objetivo 4: zonas con concentración, rondas de evaluación, órdenes a ciegas
y avisos de duplicado (HU-09; sección 9 del diseño del objetivo 4).

- ``zona.concentracion`` (ENUM ``concentracion_zona``: alta, baja) y ``uq_zona_nombre``.
  ``zona`` puede tener filas en una base de desarrollo: la columna se añade nula, se rellena
  con ``baja`` (valor neutro; el piloto no usa zonas hasta cargarlas con su concentración real
  y conviene revisarlas) y recién entonces se vuelve NOT NULL. Si hubiera nombres repetidos,
  la restricción única falla y la migración se detiene sin dejar nada a medias (DDL transaccional).
- ``ronda_evaluacion`` (una sola abierta a la vez), ``ronda_reporte`` (muestra congelada con
  el puntaje U y el orden del motor), ``orden_evaluador`` (orden a ciegas por evaluador) y
  ``aviso_duplicado`` con sus candidatos.
- ``rol_usuario`` gana el valor ``evaluador``.

Downgrade: borra todo lo nuevo salvo el valor ``evaluador`` del ENUM ``rol_usuario``, porque
PostgreSQL no permite quitar valores de un ENUM; queda inofensivo (ningún usuario puede
conservarlo si antes se les cambió el rol).

Revision ID: 0009
Revises: 0008
Create Date: 2026-11-23
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0009"
down_revision: str | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

concentracion_zona = postgresql.ENUM("alta", "baja", name="concentracion_zona")
estado_ronda = postgresql.ENUM("abierta", "cerrada", name="estado_ronda")
decision_aviso = postgresql.ENUM("pendiente", "confirmo", "creo_igual", name="decision_aviso")
ENUM_TYPES = (concentracion_zona, estado_ronda, decision_aviso)


def _ref(enum: postgresql.ENUM) -> postgresql.ENUM:
    """Referencia a un ENUM ya creado (evita que create_table lo cree otra vez)."""
    return postgresql.ENUM(*enum.enums, name=enum.name, create_type=False)


def _timestamp(name: str) -> sa.Column[sa.DateTime]:
    return sa.Column(name, sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False)


def _uuid_pk(name: str) -> sa.Column[sa.Uuid[str]]:
    return sa.Column(name, sa.Uuid(), server_default=sa.text("gen_random_uuid()"), primary_key=True)


def upgrade() -> None:
    # ADD VALUE no puede ejecutarse dentro de una transacción.
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE rol_usuario ADD VALUE IF NOT EXISTS 'evaluador'")

    bind = op.get_bind()
    for enum in ENUM_TYPES:
        enum.create(bind, checkfirst=False)

    op.add_column("zona", sa.Column("concentracion", _ref(concentracion_zona), nullable=True))
    op.execute("UPDATE zona SET concentracion = 'baja'")
    op.alter_column("zona", "concentracion", nullable=False)
    op.create_unique_constraint("uq_zona_nombre", "zona", ["nombre"])

    op.create_table(
        "ronda_evaluacion",
        _uuid_pk("id_ronda"),
        sa.Column("nombre", sa.String(100), nullable=False),
        sa.Column("estado", _ref(estado_ronda), server_default="abierta", nullable=False),
        sa.Column("tamano_muestra", sa.SmallInteger(), nullable=False),
        sa.Column("semilla", sa.BigInteger(), nullable=False),
        sa.Column(
            "id_config",
            sa.Integer(),
            sa.ForeignKey("configuracion_pesos.id_config", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "id_usuario",
            sa.Uuid(),
            sa.ForeignKey("usuario.id_usuario", ondelete="RESTRICT"),
            nullable=False,
        ),
        _timestamp("fecha_apertura"),
        sa.Column("fecha_cierre", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("tamano_muestra > 0", name="ck_ronda_evaluacion_tamano_positivo"),
    )
    # Una sola ronda abierta a la vez: índice único parcial sobre la constante de estado.
    op.create_index(
        "uq_ronda_abierta",
        "ronda_evaluacion",
        ["estado"],
        unique=True,
        postgresql_where=sa.text("estado = 'abierta'"),
    )

    op.create_table(
        "ronda_reporte",
        sa.Column(
            "id_ronda",
            sa.Uuid(),
            sa.ForeignKey("ronda_evaluacion.id_ronda", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "id_reporte",
            sa.Uuid(),
            sa.ForeignKey("reporte.id_reporte", ondelete="RESTRICT"),
            primary_key=True,
        ),
        sa.Column(
            "id_zona",
            sa.Integer(),
            sa.ForeignKey("zona.id_zona", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("puntaje_u", sa.Numeric(4, 2), nullable=False),
        sa.Column("orden_motor", sa.SmallInteger(), nullable=False),
        sa.UniqueConstraint(
            "id_ronda", "id_zona", "orden_motor", name="uq_ronda_reporte_zona_orden"
        ),
    )

    op.create_table(
        "orden_evaluador",
        sa.Column("id_ronda", sa.Uuid(), primary_key=True),
        sa.Column(
            "id_usuario",
            sa.Uuid(),
            sa.ForeignKey("usuario.id_usuario", ondelete="RESTRICT"),
            primary_key=True,
        ),
        sa.Column("id_reporte", sa.Uuid(), primary_key=True),
        sa.Column("posicion", sa.SmallInteger(), nullable=False),
        _timestamp("fecha_envio"),
        sa.ForeignKeyConstraint(
            ["id_ronda", "id_reporte"],
            ["ronda_reporte.id_ronda", "ronda_reporte.id_reporte"],
            ondelete="CASCADE",
        ),
    )

    op.create_table(
        "aviso_duplicado",
        _uuid_pk("id_aviso"),
        sa.Column(
            "id_usuario",
            sa.Uuid(),
            sa.ForeignKey("usuario.id_usuario", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "id_zona", sa.Integer(), sa.ForeignKey("zona.id_zona", ondelete="SET NULL")
        ),
        _timestamp("fecha"),
        sa.Column("decision", _ref(decision_aviso), server_default="pendiente", nullable=False),
        sa.Column(
            "id_reporte_resultante",
            sa.Uuid(),
            sa.ForeignKey("reporte.id_reporte", ondelete="SET NULL"),
            nullable=True,
        ),
    )

    op.create_table(
        "aviso_duplicado_candidato",
        sa.Column(
            "id_aviso",
            sa.Uuid(),
            sa.ForeignKey("aviso_duplicado.id_aviso", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "id_reporte",
            sa.Uuid(),
            sa.ForeignKey("reporte.id_reporte", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("distancia_m", sa.Numeric(6, 2), nullable=False),
    )


def downgrade() -> None:
    for table in (
        "aviso_duplicado_candidato",
        "aviso_duplicado",
        "orden_evaluador",
        "ronda_reporte",
        "ronda_evaluacion",
    ):
        op.drop_table(table)
    op.drop_constraint("uq_zona_nombre", "zona", type_="unique")
    op.drop_column("zona", "concentracion")
    bind = op.get_bind()
    for enum in reversed(ENUM_TYPES):
        enum.drop(bind, checkfirst=False)
