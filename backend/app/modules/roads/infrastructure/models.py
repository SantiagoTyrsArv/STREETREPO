from decimal import Decimal

from geoalchemy2 import Geometry
from sqlalchemy import BigInteger, CheckConstraint, Index, Integer, Numeric, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.db_types import linestring, pg_enum, polygon
from app.modules.roads.domain.road_class import RoadClass


class RoadModel(Base):
    __tablename__ = "via"
    __table_args__ = (
        CheckConstraint("factor_flujo BETWEEN 0 AND 10", name="ck_via_factor_flujo_rango"),
        Index("ix_via_geom", "geom", postgresql_using="gist"),
        # Map-matching a 30 m sobre geography (ADR 0003).
        Index("ix_via_geom_geog", text("(geom::geography)"), postgresql_using="gist"),
    )

    id: Mapped[int] = mapped_column("id_via", Integer, primary_key=True)
    osm_id: Mapped[int] = mapped_column("osm_id", BigInteger, unique=True)
    # Muchas vías de OSM no tienen nombre.
    name: Mapped[str | None] = mapped_column("nombre", String(150))
    road_class: Mapped[RoadClass] = mapped_column(
        "jerarquia_vial", pg_enum(RoadClass, "jerarquia_vial")
    )
    flow_factor: Mapped[Decimal] = mapped_column("factor_flujo", Numeric(4, 2))
    geom: Mapped[Geometry] = mapped_column("geom", linestring())


class ZoneModel(Base):
    __tablename__ = "zona"
    __table_args__ = (Index("ix_zona_geom", "geom", postgresql_using="gist"),)

    id: Mapped[int] = mapped_column("id_zona", Integer, primary_key=True)
    name: Mapped[str] = mapped_column("nombre", String(100))
    geom: Mapped[Geometry] = mapped_column("geom", polygon())
