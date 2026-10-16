"""Emisión de pares de tokens: acceso (JWT corto) + refresco (opaco, rotatorio)."""

import hashlib
import secrets
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta

from app.modules.auth.domain.entities import TokenPair
from app.modules.auth.domain.ports import AccessTokenService, RefreshTokenRepository
from app.modules.users.domain.entities import User

# 32 bytes aleatorios: imposible de adivinar, así que basta un hash rápido (SHA-256)
# para guardarlo; un hash lento como Argon2 solo hace falta para contraseñas.
_REFRESH_TOKEN_BYTES = 32


def hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


@dataclass(frozen=True, slots=True)
class IssuedSession:
    tokens: TokenPair
    refresh_token_id: uuid.UUID


class SessionIssuer:
    def __init__(
        self,
        access_tokens: AccessTokenService,
        refresh_tokens: RefreshTokenRepository,
        refresh_ttl: timedelta,
    ) -> None:
        self._access_tokens = access_tokens
        self._refresh_tokens = refresh_tokens
        self._refresh_ttl = refresh_ttl

    def issue(self, user: User, now: datetime) -> IssuedSession:
        refresh_token = secrets.token_urlsafe(_REFRESH_TOKEN_BYTES)
        refresh_id = self._refresh_tokens.add(
            user_id=user.id,
            token_hash=hash_refresh_token(refresh_token),
            issued_at=now,
            expires_at=now + self._refresh_ttl,
        )
        access_token = self._access_tokens.issue(user.id, user.role, now)
        return IssuedSession(
            tokens=TokenPair(
                access_token=access_token,
                access_expires_in_s=self._access_tokens.ttl_seconds,
                refresh_token=refresh_token,
            ),
            refresh_token_id=refresh_id,
        )
