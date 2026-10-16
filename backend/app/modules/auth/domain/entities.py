import uuid
from dataclasses import dataclass
from datetime import datetime

from app.modules.users.domain.role import UserRole


@dataclass(frozen=True, slots=True)
class AccessClaims:
    """Contenido verificado de un token de acceso."""

    user_id: uuid.UUID
    role: UserRole
    expires_at: datetime


@dataclass(frozen=True, slots=True)
class StoredRefreshToken:
    """Token de refresco guardado (solo su hash vive en la base)."""

    id: uuid.UUID
    user_id: uuid.UUID
    expires_at: datetime
    revoked: bool
    replaced_by: uuid.UUID | None


@dataclass(frozen=True, slots=True)
class TokenPair:
    access_token: str
    access_expires_in_s: int
    refresh_token: str
