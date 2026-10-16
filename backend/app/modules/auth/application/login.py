"""Casos de uso de sesión: iniciar, refrescar (rotación) y cerrar (guía 7.1)."""

from functools import cached_property

from app.modules.auth.application.errors import InvalidCredentialsError, InvalidRefreshTokenError
from app.modules.auth.application.sessions import SessionIssuer, hash_refresh_token
from app.modules.auth.domain.entities import TokenPair
from app.modules.auth.domain.ports import PasswordHasher, RefreshTokenRepository
from app.modules.users.domain.entities import normalize_email
from app.modules.users.domain.ports import UserRepository
from app.shared.application.clock import Clock
from app.shared.application.transaction import TransactionManager


class Login:
    def __init__(
        self,
        users: UserRepository,
        hasher: PasswordHasher,
        sessions: SessionIssuer,
        clock: Clock,
        transaction: TransactionManager,
    ) -> None:
        self._users = users
        self._hasher = hasher
        self._sessions = sessions
        self._clock = clock
        self._transaction = transaction

    @cached_property
    def _dummy_hash(self) -> str:
        return self._hasher.hash("contraseña-de-relleno-para-igualar-tiempos")

    def execute(self, email: str, password: str) -> TokenPair:
        user = self._users.get_by_email(normalize_email(email))
        # Se verifica un hash aunque el correo no exista, para que el tiempo de
        # respuesta no revele qué correos están registrados.
        password_ok = self._hasher.verify(
            user.password_hash if user else self._dummy_hash, password
        )
        if user is None or not password_ok or not user.is_active:
            raise InvalidCredentialsError("Correo o contraseña incorrectos")
        try:
            if self._hasher.needs_rehash(user.password_hash):
                self._users.update_password_hash(user.id, self._hasher.hash(password))
            session = self._sessions.issue(user, self._clock.now())
            self._transaction.commit()
        except Exception:
            self._transaction.rollback()
            raise
        return session.tokens


class RefreshSession:
    """Rota el token de refresco: cada uno sirve una sola vez.

    Si llega un token ya rotado, alguien lo copió: se revoca la sesión entera
    (detección de reutilización, OWASP ASVS V3.5).
    """

    def __init__(
        self,
        users: UserRepository,
        refresh_tokens: RefreshTokenRepository,
        sessions: SessionIssuer,
        clock: Clock,
        transaction: TransactionManager,
    ) -> None:
        self._users = users
        self._refresh_tokens = refresh_tokens
        self._sessions = sessions
        self._clock = clock
        self._transaction = transaction

    def execute(self, refresh_token: str) -> TokenPair:
        now = self._clock.now()
        stored = self._refresh_tokens.get_by_hash(hash_refresh_token(refresh_token))
        if stored is None:
            raise InvalidRefreshTokenError("Sesión no válida")
        if stored.revoked:
            if stored.replaced_by is not None:
                self._refresh_tokens.revoke_chain(stored.id)
                self._transaction.commit()
            raise InvalidRefreshTokenError("Sesión no válida")
        if stored.expires_at <= now:
            raise InvalidRefreshTokenError("La sesión venció")
        user = self._users.get_by_id(stored.user_id)
        if user is None or not user.is_active:
            self._refresh_tokens.revoke_all_for_user(stored.user_id)
            self._transaction.commit()
            raise InvalidRefreshTokenError("Sesión no válida")
        try:
            session = self._sessions.issue(user, now)
            self._refresh_tokens.mark_replaced(stored.id, session.refresh_token_id)
            self._transaction.commit()
        except Exception:
            self._transaction.rollback()
            raise
        return session.tokens


class Logout:
    """Revoca la sesión del token. Es idempotente: un token desconocido no da error."""

    def __init__(
        self, refresh_tokens: RefreshTokenRepository, transaction: TransactionManager
    ) -> None:
        self._refresh_tokens = refresh_tokens
        self._transaction = transaction

    def execute(self, refresh_token: str) -> None:
        stored = self._refresh_tokens.get_by_hash(hash_refresh_token(refresh_token))
        if stored is None or stored.revoked:
            return
        self._refresh_tokens.revoke_chain(stored.id)
        self._transaction.commit()
