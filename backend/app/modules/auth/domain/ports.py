import uuid
from datetime import datetime
from typing import Protocol

from app.modules.auth.domain.entities import AccessClaims, StoredRefreshToken
from app.modules.users.domain.role import UserRole


class InvalidAccessTokenError(Exception):
    """Token de acceso ausente, mal formado, con firma inválida o vencido."""


class PasswordHasher(Protocol):
    def hash(self, password: str) -> str: ...

    def verify(self, password_hash: str, password: str) -> bool:
        """``True`` si coincide; nunca lanza por una contraseña incorrecta."""
        ...

    def needs_rehash(self, password_hash: str) -> bool:
        """``True`` si el hash se hizo con parámetros más débiles que los actuales."""
        ...


class AccessTokenService(Protocol):
    @property
    def ttl_seconds(self) -> int: ...

    def issue(self, user_id: uuid.UUID, role: UserRole, now: datetime) -> str: ...

    def verify(self, token: str) -> AccessClaims:
        """Lanza ``InvalidAccessTokenError`` si el token no es válido."""
        ...


class RefreshTokenRepository(Protocol):
    def add(
        self, user_id: uuid.UUID, token_hash: str, issued_at: datetime, expires_at: datetime
    ) -> uuid.UUID: ...

    def get_by_hash(self, token_hash: str) -> StoredRefreshToken | None: ...

    def mark_replaced(self, token_id: uuid.UUID, replaced_by: uuid.UUID) -> None:
        """Revoca el token y apunta al que lo reemplaza (rotación)."""
        ...

    def revoke_chain(self, token_id: uuid.UUID) -> None:
        """Revoca el token y todos los que lo reemplazaron después (la sesión entera)."""
        ...

    def revoke_all_for_user(self, user_id: uuid.UUID) -> None: ...
