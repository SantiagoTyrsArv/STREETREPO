"""Guardar la etiqueta highway original de OSM en via (propuesta 7).

Conserva el valor de origen (trunk, primary_link, service…) para que la
clasificación en jerarquia_vial sea auditable y se pueda recalcular si la
regla cambia. La tabla está vacía hasta la primera carga OSM.

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-15
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("via", sa.Column("highway_osm", sa.String(30), nullable=False))


def downgrade() -> None:
    op.drop_column("via", "highway_osm")
