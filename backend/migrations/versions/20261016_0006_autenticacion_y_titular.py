"""Autenticación y derechos del titular (propuestas 8, 9 y 10; ER actualizado en Lucid).

- usuario.version_politica: versión de la política de datos aceptada (Ley 1581).
- token_refresco: tokens de refresco rotatorios y revocables; solo se guarda el hash.
- solicitud_supresion: constancia del trámite de supresión de datos.

Revision ID: 0006
Revises: 0005
Create Date: 2026-10-16
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

estado_solicitud = postgresql.ENUM("pendiente", "atendida", name="estado_solicitud")


def _uuid_pk(name: str) -> sa.Column[sa.Uuid[str]]:
    return sa.Column(name, sa.Uuid(), server_default=sa.text("gen_random_uuid()"), primary_key=True)


def _timestamp(name: str) -> sa.Column[sa.DateTime]:
    return sa.Column(name, sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False)


def upgrade() -> None:
    op.add_column("usuario", sa.Column("version_politica", sa.String(20), nullable=True))
    # Ley 1581: si aceptó la política debe constar qué versión aceptó.
    op.create_check_constraint(
        "ck_usuario_aceptacion_con_version",
        "usuario",
        "NOT acepta_politica OR version_politica IS NOT NULL",
    )

    op.create_table(
        "token_refresco",
        _uuid_pk("id_token"),
        sa.Column(
            "id_usuario",
            sa.Uuid(),
            sa.ForeignKey("usuario.id_usuario", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("hash_token", sa.String(255), nullable=False),
        _timestamp("emitido"),
        sa.Column("expira", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revocado", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column(
            "reemplazado_por",
            sa.Uuid(),
            sa.ForeignKey("token_refresco.id_token", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.CheckConstraint("expira > emitido", name="ck_token_refresco_expira_despues"),
        sa.UniqueConstraint("hash_token", name="uq_token_refresco_hash_token"),
    )
    op.create_index("ix_token_refresco_id_usuario", "token_refresco", ["id_usuario"])

    bind = op.get_bind()
    estado_solicitud.create(bind, checkfirst=False)
    op.create_table(
        "solicitud_supresion",
        _uuid_pk("id_solicitud"),
        sa.Column(
            "id_usuario",
            sa.Uuid(),
            # La constancia del trámite debe sobrevivir: el usuario se anonimiza, no se borra.
            sa.ForeignKey("usuario.id_usuario", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "estado",
            postgresql.ENUM(*estado_solicitud.enums, name="estado_solicitud", create_type=False),
            server_default="pendiente",
            nullable=False,
        ),
        _timestamp("fecha_solicitud"),
        sa.Column("fecha_atencion", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "(estado = 'atendida') = (fecha_atencion IS NOT NULL)",
            name="ck_solicitud_supresion_atencion_con_fecha",
        ),
    )
    op.create_index("ix_solicitud_supresion_id_usuario", "solicitud_supresion", ["id_usuario"])
    # Una sola solicitud pendiente por titular.
    op.create_index(
        "uq_solicitud_supresion_pendiente",
        "solicitud_supresion",
        ["id_usuario"],
        unique=True,
        postgresql_where=sa.text("estado = 'pendiente'"),
    )


def downgrade() -> None:
    op.drop_table("solicitud_supresion")
    estado_solicitud.drop(op.get_bind(), checkfirst=False)
    op.drop_table("token_refresco")
    op.drop_constraint("ck_usuario_aceptacion_con_version", "usuario", type_="check")
    op.drop_column("usuario", "version_politica")
