"""Cargar la versión inicial de pesos del modelo U (0,50 / 0,30 / 0,20).

Es un dato de referencia del modelo de la tesis, no un dato de prueba: sin una
versión vigente el motor de priorización no puede evaluar reportes. Se registra
como configuración del sistema (id_usuario NULL). Solo se inserta si la tabla no
tiene ninguna versión, para no pisar pesos ya configurados.

Revision ID: 0005
Revises: 0004
Create Date: 2026-10-16
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        "INSERT INTO configuracion_pesos (w_severidad, w_flujo, w_proximidad, vigente) "
        "SELECT 0.50, 0.30, 0.20, true "
        "WHERE NOT EXISTS (SELECT 1 FROM configuracion_pesos)"
    )


def downgrade() -> None:
    # Solo se borra la versión inicial del sistema si ninguna evaluación la usa; si
    # hay evaluaciones, la FK (RESTRICT) detiene el downgrade en lugar de perder datos.
    op.execute(
        "DELETE FROM configuracion_pesos "
        "WHERE id_usuario IS NULL AND w_severidad = 0.50 AND w_flujo = 0.30 "
        "AND w_proximidad = 0.20 "
        "AND id_config = (SELECT min(id_config) FROM configuracion_pesos)"
    )
