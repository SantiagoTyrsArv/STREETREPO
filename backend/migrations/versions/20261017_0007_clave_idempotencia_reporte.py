"""Clave de idempotencia del reporte (propuesta 11; ER actualizado en Lucid).

reporte.clave_idempotencia guarda la cabecera Idempotency-Key del envío. Es opcional y única
por par (usuario, clave), no global, para que dos usuarios no choquen con la misma clave.

Revision ID: 0007
Revises: 0006
Create Date: 2026-10-17
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("reporte", sa.Column("clave_idempotencia", sa.Uuid(), nullable=True))
    op.create_unique_constraint(
        "uq_reporte_usuario_clave_idempotencia",
        "reporte",
        ["id_usuario", "clave_idempotencia"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_reporte_usuario_clave_idempotencia", "reporte", type_="unique")
    op.drop_column("reporte", "clave_idempotencia")
