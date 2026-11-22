import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Numeric,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ConfirmationModel(Base):
    __tablename__ = "confirmacion"
    __table_args__ = (
        # Una confirmación por usuario y reporte (guía 2.1, diagrama ER).
        UniqueConstraint("id_reporte", "id_usuario", name="uq_confirmacion_reporte_usuario"),
        CheckConstraint("distancia_m >= 0", name="ck_confirmacion_distancia_no_negativa"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        "id_confirmacion", primary_key=True, server_default=text("gen_random_uuid()")
    )
    report_id: Mapped[uuid.UUID] = mapped_column(
        "id_reporte", ForeignKey("reporte.id_reporte", ondelete="CASCADE")
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        "id_usuario", ForeignKey("usuario.id_usuario", ondelete="CASCADE")
    )
    confirmed_at: Mapped[datetime] = mapped_column(
        "fecha", DateTime(timezone=True), server_default=func.now()
    )
    # A qué distancia del daño estaba quien confirmó (propuesta 112). NULL en las
    # confirmaciones anteriores a la migración 0008, que se aceptaron sin ubicación.
    distance_m: Mapped[Decimal | None] = mapped_column("distancia_m", Numeric(7, 2))
