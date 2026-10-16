import uuid
from datetime import UTC, datetime, timedelta
from typing import Final

import jwt

from app.modules.auth.domain.entities import AccessClaims
from app.modules.auth.domain.ports import InvalidAccessTokenError
from app.modules.users.domain.role import UserRole

# HS256 fijado al firmar y al verificar: nunca se acepta el algoritmo que diga el
# token (evita "alg": "none" y la confusión de algoritmos, guía 7.1).
ALGORITHM: Final = "HS256"
ISSUER: Final = "street-repo"
TOKEN_TYPE: Final = "access"  # noqa: S105 - tipo de token, no un secreto
# RFC 7518 §3.2: la clave de HS256 debe tener al menos 256 bits.
MIN_SECRET_LENGTH: Final = 32


class JwtAccessTokenService:
    """Implementa ``AccessTokenService`` con JWT firmados (PyJWT)."""

    def __init__(self, secret_key: str, ttl_minutes: int) -> None:
        if len(secret_key) < MIN_SECRET_LENGTH:
            raise ValueError(f"JWT_SECRET_KEY debe tener al menos {MIN_SECRET_LENGTH} caracteres")
        self._secret_key = secret_key
        self._ttl = timedelta(minutes=ttl_minutes)

    @property
    def ttl_seconds(self) -> int:
        return int(self._ttl.total_seconds())

    def issue(self, user_id: uuid.UUID, role: UserRole, now: datetime) -> str:
        payload = {
            "sub": str(user_id),
            "role": role.value,
            "typ": TOKEN_TYPE,
            "iss": ISSUER,
            "iat": now,
            "exp": now + self._ttl,
        }
        return jwt.encode(payload, self._secret_key, algorithm=ALGORITHM)

    def verify(self, token: str) -> AccessClaims:
        try:
            payload = jwt.decode(
                token,
                self._secret_key,
                algorithms=[ALGORITHM],
                issuer=ISSUER,
                options={"require": ["sub", "role", "typ", "iss", "iat", "exp"]},
            )
            if payload["typ"] != TOKEN_TYPE:
                raise InvalidAccessTokenError("El token no es de acceso")
            return AccessClaims(
                user_id=uuid.UUID(payload["sub"]),
                role=UserRole(payload["role"]),
                expires_at=datetime.fromtimestamp(payload["exp"], UTC),
            )
        except (jwt.PyJWTError, ValueError) as exc:
            raise InvalidAccessTokenError("Token de acceso no válido") from exc
