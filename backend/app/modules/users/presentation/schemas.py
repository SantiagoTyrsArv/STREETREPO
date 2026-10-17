import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.modules.auth.presentation.schemas import Email, Name, Password
from app.modules.users.domain.deletion_request import DeletionRequest, DeletionRequestStatus
from app.modules.users.domain.entities import User
from app.modules.users.domain.role import UserRole


class UserResponse(BaseModel):
    """Datos del propio titular. Nunca incluye el hash de la contraseña."""

    model_config = ConfigDict(frozen=True)

    id: uuid.UUID
    name: str
    email: str
    role: UserRole
    registered_at: datetime
    policy_version: str | None
    policy_accepted_at: datetime | None

    @classmethod
    def from_user(cls, user: User) -> "UserResponse":
        consent = user.consent
        return cls(
            id=user.id,
            name=user.name,
            email=user.email,
            role=user.role,
            registered_at=user.registered_at,
            policy_version=None if consent is None else consent.version,
            policy_accepted_at=None if consent is None else consent.accepted_at,
        )


class _Request(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class UpdateMyDataRequest(_Request):
    """Solo cambian los campos enviados. Cambiar el correo exige ``current_password``."""

    name: Name | None = None
    email: Email | None = None
    current_password: Password | None = None


class DataDeletionRequestBody(_Request):
    """La supresión es irreversible: se confirma con la contraseña actual."""

    current_password: Password


class DataDeletionResponse(BaseModel):
    """Constancia del trámite. Tras recibirla la cuenta ya no existe: la app descarta sus tokens."""

    model_config = ConfigDict(frozen=True)

    id: uuid.UUID
    status: DeletionRequestStatus
    requested_at: datetime
    attended_at: datetime | None

    @classmethod
    def from_request(cls, request: DeletionRequest) -> "DataDeletionResponse":
        return cls(
            id=request.id,
            status=request.status,
            requested_at=request.requested_at,
            attended_at=request.attended_at,
        )
