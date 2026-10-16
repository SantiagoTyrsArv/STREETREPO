import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class RefreshTokenModel(Base):
    """Token de refresco rotatorio y revocable (guía 7.1, propuesta 9).

    Solo se guarda el hash del token. ``reemplazado_por`` encadena las rotaciones
    de una sesión para revocarla entera si se reutiliza un token ya usado.
    """

    __tablename__ = "token_refresco"
    __table_args__ = (
        CheckConstraint("expira > emitido", name="ck_token_refresco_expira_despues"),
        UniqueConstraint("hash_token", name="uq_token_refresco_hash_token"),
        Index("ix_token_refresco_id_usuario", "id_usuario"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        "id_token", primary_key=True, server_default=text("gen_random_uuid()")
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        "id_usuario", ForeignKey("usuario.id_usuario", ondelete="CASCADE")
    )
    token_hash: Mapped[str] = mapped_column("hash_token", String(255))
    issued_at: Mapped[datetime] = mapped_column(
        "emitido", DateTime(timezone=True), server_default=func.now()
    )
    expires_at: Mapped[datetime] = mapped_column("expira", DateTime(timezone=True))
    revoked: Mapped[bool] = mapped_column("revocado", Boolean, server_default=text("false"))
    replaced_by: Mapped[uuid.UUID | None] = mapped_column(
        "reemplazado_por", ForeignKey("token_refresco.id_token", ondelete="SET NULL")
    )
