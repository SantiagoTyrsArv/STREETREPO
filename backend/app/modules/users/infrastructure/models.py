import uuid
from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, String, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.db_types import pg_enum
from app.modules.users.domain.deletion_request import DeletionRequestStatus
from app.modules.users.domain.role import UserRole


class UserModel(Base):
    __tablename__ = "usuario"
    __table_args__ = (
        # Ley 1581: si aceptó la política debe quedar la fecha del consentimiento.
        CheckConstraint(
            "NOT acepta_politica OR fecha_aceptacion IS NOT NULL",
            name="ck_usuario_aceptacion_con_fecha",
        ),
        # ... y la versión de la política que aceptó (propuesta 8).
        CheckConstraint(
            "NOT acepta_politica OR version_politica IS NOT NULL",
            name="ck_usuario_aceptacion_con_version",
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
    accepted_policy_at: Mapped[datetime | None] = mapped_column(
        "fecha_aceptacion", DateTime(timezone=True)
    )
    policy_version: Mapped[str | None] = mapped_column("version_politica", String(20))
    registered_at: Mapped[datetime] = mapped_column(
        "fecha_registro", DateTime(timezone=True), server_default=func.now()
    )


DELETION_REQUEST_STATUS_TYPE = "estado_solicitud"


class DataDeletionRequestModel(Base):
    """Constancia del trámite de supresión de datos (Ley 1581, propuesta 10)."""

    __tablename__ = "solicitud_supresion"
    __table_args__ = (
        CheckConstraint(
            "(estado = 'atendida') = (fecha_atencion IS NOT NULL)",
            name="ck_solicitud_supresion_atencion_con_fecha",
        ),
        Index("ix_solicitud_supresion_id_usuario", "id_usuario"),
        Index(
            "uq_solicitud_supresion_pendiente",
            "id_usuario",
            unique=True,
            postgresql_where=text("estado = 'pendiente'"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        "id_solicitud", primary_key=True, server_default=text("gen_random_uuid()")
    )
    # RESTRICT: la constancia sobrevive; el titular se anonimiza, no se borra.
    user_id: Mapped[uuid.UUID] = mapped_column(
        "id_usuario", ForeignKey("usuario.id_usuario", ondelete="RESTRICT")
    )
    status: Mapped[DeletionRequestStatus] = mapped_column(
        "estado",
        pg_enum(DeletionRequestStatus, DELETION_REQUEST_STATUS_TYPE),
        server_default=DeletionRequestStatus.PENDING.value,
    )
    requested_at: Mapped[datetime] = mapped_column(
        "fecha_solicitud", DateTime(timezone=True), server_default=func.now()
    )
    attended_at: Mapped[datetime | None] = mapped_column("fecha_atencion", DateTime(timezone=True))
