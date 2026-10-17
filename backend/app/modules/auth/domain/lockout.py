"""Bloqueo progresivo por intentos fallidos de inicio de sesión (guía 7.1, OWASP ASVS V2.2.1)."""

from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass(frozen=True, slots=True)
class FailedLogins:
    """Fallos consecutivos de una cuenta y, si está bloqueada, hasta cuándo."""

    count: int
    last_failure_at: datetime
    locked_until: datetime | None


@dataclass(frozen=True, slots=True)
class LockoutPolicy:
    """Tras ``free_attempts`` fallos seguidos, cada fallo bloquea la cuenta el doble que el
    anterior, empezando en ``base_lock`` y sin pasar de ``max_lock``. Los fallos se olvidan
    tras ``forget_after`` sin fallar.
    """

    free_attempts: int
    base_lock: timedelta
    max_lock: timedelta
    forget_after: timedelta

    def lock_duration(self, consecutive_failures: int) -> timedelta | None:
        extra_failures = consecutive_failures - self.free_attempts
        if extra_failures < 0:
            return None
        # Se acota el exponente: desde ahí el resultado ya es max_lock.
        doublings = min(extra_failures, 20)
        lock: timedelta = self.base_lock * (1 << doublings)
        return min(lock, self.max_lock)

    def register_failure(self, previous: FailedLogins | None, now: datetime) -> FailedLogins:
        if previous is None or now - previous.last_failure_at >= self.forget_after:
            count = 1
        else:
            count = previous.count + 1
        lock = self.lock_duration(count)
        return FailedLogins(count, now, now + lock if lock is not None else None)

    @staticmethod
    def remaining_lock(record: FailedLogins | None, now: datetime) -> timedelta | None:
        """Tiempo que le queda al bloqueo, o ``None`` si la cuenta no está bloqueada."""
        if record is None or record.locked_until is None or record.locked_until <= now:
            return None
        return record.locked_until - now


# 5 intentos libres; luego 1, 2, 4, 8 y 15 min. Corta el ataque de fuerza bruta sobre una
# cuenta sin dejarla bloqueada más de 15 min si alguien la bloquea a propósito.
DEFAULT_LOCKOUT_POLICY = LockoutPolicy(
    free_attempts=5,
    base_lock=timedelta(minutes=1),
    max_lock=timedelta(minutes=15),
    forget_after=timedelta(hours=1),
)
