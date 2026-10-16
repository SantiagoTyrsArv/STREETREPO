import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, UniqueConstraint, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ConfirmationModel(Base):
    __tablename__ = "confirmacion"
    __table_args__ = (
        # Una confirmación por usuario y reporte (guía 2.1, diagrama ER).
        UniqueConstraint("id_reporte", "id_usuario", name="uq_confirmacion_reporte_usuario"),
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
