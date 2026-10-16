from geoalchemy2 import Geometry
from sqlalchemy import BigInteger, Index, Integer, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.db_types import pg_enum, point
from app.modules.critical_services.domain.service_type import CriticalServiceType


class CriticalServiceModel(Base):
    __tablename__ = "servicio_critico"
    __table_args__ = (
        Index("ix_servicio_critico_ubicacion", "ubicacion", postgresql_using="gist"),
        # Las distancias en metros se miden sobre geography (ADR 0003).
        Index(
            "ix_servicio_critico_ubicacion_geog",
            text("(ubicacion::geography)"),
            postgresql_using="gist",
        ),
    )

    id: Mapped[int] = mapped_column("id_servicio", Integer, primary_key=True)
    osm_id: Mapped[int] = mapped_column("osm_id", BigInteger, unique=True)
    name: Mapped[str | None] = mapped_column("nombre", String(150))
    service_type: Mapped[CriticalServiceType] = mapped_column(
        "tipo", pg_enum(CriticalServiceType, "tipo_servicio")
    )
    location: Mapped[Geometry] = mapped_column("ubicacion", point())
