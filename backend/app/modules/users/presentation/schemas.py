import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

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
