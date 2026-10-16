import uuid
from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, String, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.db_types import pg_enum
from app.modules.users.domain.role import UserRole


class UserModel(Base):
    __tablename__ = "usuario"
    __table_args__ = (
        # Ley 1581: si aceptó la política debe quedar la fecha del consentimiento.
        CheckConstraint(
            "NOT acepta_politica OR fecha_aceptacion IS NOT NULL",
            name="ck_usuario_aceptacion_con_fecha",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        "id_usuario", primary_key=True, server_default=text("gen_random_uuid()")
    )
    name: Mapped[str] = mapped_column("nombre", String(100))
    email: Mapped[str] = mapped_column("correo", String(150), unique=True)
    password_hash: Mapped[str] = mapped_column("password_hash", String(255))
    role: Mapped[UserRole] = mapped_column(
        "rol", pg_enum(UserRole, "rol_usuario"), server_default=UserRole.CITIZEN.value
    )
    is_active: Mapped[bool] = mapped_column("activo", Boolean, server_default=text("true"))
    accepted_policy: Mapped[bool] = mapped_column(
        "acepta_politica", Boolean, server_default=text("false")
    )
    # TODO(propuesta-8): registrar también la versión de la política aceptada (guía 7.2).
    accepted_policy_at: Mapped[datetime | None] = mapped_column(
        "fecha_aceptacion", DateTime(timezone=True)
    )
    registered_at: Mapped[datetime] = mapped_column(
        "fecha_registro", DateTime(timezone=True), server_default=func.now()
    )
