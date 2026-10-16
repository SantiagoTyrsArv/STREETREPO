import uuid
from dataclasses import dataclass
from datetime import datetime

from app.modules.users.domain.role import UserRole


def normalize_email(email: str) -> str:
    """El correo se guarda y se busca en minúsculas y sin espacios (``correo`` es UNIQUE)."""
    return email.strip().lower()


@dataclass(frozen=True, slots=True)
class PolicyConsent:
    """Consentimiento informado (Ley 1581): qué versión aceptó y cuándo."""

    version: str
    accepted_at: datetime


@dataclass(frozen=True, slots=True)
class NewUser:
    name: str
    email: str
    password_hash: str
    role: UserRole
    consent: PolicyConsent | None


@dataclass(frozen=True, slots=True)
class User:
    id: uuid.UUID
    name: str
    email: str
    password_hash: str
    role: UserRole
    is_active: bool
    consent: PolicyConsent | None
    registered_at: datetime
