"""Confirmación de la contraseña antes de una acción sensible (propuesta 26, OWASP ASVS V3.7).

Comparte el bloqueo progresivo del inicio de sesión: con un token de acceso robado no se
puede adivinar la contraseña por esta vía sin bloquear también el inicio de sesión.
"""

from app.modules.auth.application.errors import (
    AccountLockedError,
    PasswordConfirmationRequiredError,
    WrongPasswordError,
)
from app.modules.auth.application.login import login_attempt_key
from app.modules.auth.domain.lockout import LockoutPolicy
from app.modules.auth.domain.ports import LoginAttemptStore, PasswordHasher
from app.modules.users.domain.entities import User
from app.shared.application.clock import Clock


class PasswordConfirmation:
    def __init__(
        self,
        hasher: PasswordHasher,
        attempts: LoginAttemptStore,
        lockout: LockoutPolicy,
        clock: Clock,
    ) -> None:
        self._hasher = hasher
        self._attempts = attempts
        self._lockout = lockout
        self._clock = clock

    def confirm(self, user: User, password: str | None) -> None:
        """Lanza ``PasswordConfirmationRequiredError`` si no llega la contraseña,
        ``AccountLockedError`` si la cuenta está bloqueada o ``WrongPasswordError``."""
        if password is None:
            raise PasswordConfirmationRequiredError("Confirma tu contraseña actual")
        now = self._clock.now()
        key = login_attempt_key(user.email)
        record = self._attempts.get(key)
        remaining = self._lockout.remaining_lock(record, now)
        if remaining is not None:
            raise AccountLockedError(remaining)
        if not self._hasher.verify(user.password_hash, password):
            self._attempts.save(key, self._lockout.register_failure(record, now))
            raise WrongPasswordError("La contraseña no coincide")
        self._attempts.clear(key)
