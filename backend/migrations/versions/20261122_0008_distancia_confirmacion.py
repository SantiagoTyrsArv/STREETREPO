"""Distancia de la confirmación al daño (propuesta 112; ER actualizado en Lucid).

confirmacion.distancia_m guarda, en metros y redondeada a centímetros, a qué distancia del
reporte estaba quien lo confirmó. Las confirmaciones anteriores a esta migración no la tienen
(NULL): se aceptaron sin ubicación.

Revision ID: 0008
Revises: 0007
Create Date: 2026-11-22
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("confirmacion", sa.Column("distancia_m", sa.Numeric(7, 2), nullable=True))
    op.create_check_constraint(
        "ck_confirmacion_distancia_no_negativa", "confirmacion", "distancia_m >= 0"
    )


def downgrade() -> None:
    op.drop_constraint("ck_confirmacion_distancia_no_negativa", "confirmacion", type_="check")
    op.drop_column("confirmacion", "distancia_m")
