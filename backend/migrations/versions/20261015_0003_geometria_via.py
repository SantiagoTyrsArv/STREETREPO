"""Añadir la geometría de la vía (propuesta 6).

Sin la línea de la vía no se puede asociar un reporte a la vía OSM más cercana
dentro de 30 m (guía 2.2). La tabla está vacía hasta la primera carga OSM, por
eso la columna se crea directamente como NOT NULL.

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-15
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from geoalchemy2 import Geometry

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "via",
        sa.Column(
            "geom", Geometry("LINESTRING", srid=4326, spatial_index=False), nullable=False
        ),
    )
    op.create_index("ix_via_geom", "via", ["geom"], postgresql_using="gist")
    op.create_index(
        "ix_via_geom_geog", "via", [sa.literal_column("(geom::geography)")], postgresql_using="gist"
    )


def downgrade() -> None:
    op.drop_index("ix_via_geom_geog", table_name="via")
    op.drop_index("ix_via_geom", table_name="via")
    op.drop_column("via", "geom")
