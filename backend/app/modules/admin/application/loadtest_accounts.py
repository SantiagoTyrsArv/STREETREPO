"""Cuentas de ciudadano para la prueba de carga con Locust (fase 8, decisión 68).

Solo para el entorno de carga local: ``loadtest-accounts --count N`` las crea con una
contraseña común y ``loadtest-accounts --remove`` las borra con todo lo que crearon.
"""

from typing import Protocol

from app.modules.admin.domain.demo import DemoDataStore
from app.modules.admin.domain.loadtest import LOADTEST_NAME, loadtest_email
from app.modules.auth.domain.ports import PasswordHasher
from app.modules.users.domain.entities import NewUser, PolicyConsent, User
from app.modules.users.domain.ports import PhotoFileRemover
from app.modules.users.domain.role import UserRole
from app.shared.application.clock import Clock
from app.shared.application.transaction import TransactionManager


class LoadTestUsers(Protocol):
    def get_by_email(self, email: str) -> User | None: ...

    def add(self, user: NewUser) -> User: ...


class LoadTestAccounts:
    def __init__(
        self,
        *,
        users: LoadTestUsers,
        hasher: PasswordHasher,
        data: DemoDataStore,
        photo_files: PhotoFileRemover,
        transaction: TransactionManager,
        clock: Clock,
        policy_version: str,
    ) -> None:
        self._users = users
        self._hasher = hasher
        self._data = data
        self._photo_files = photo_files
        self._transaction = transaction
        self._clock = clock
        self._policy_version = policy_version

    def create(self, count: int, password: str) -> list[str]:
        """Crea las cuentas que falten de ``carga-001`` a ``carga-<count>``; devuelve los correos.

        Aceptan la política vigente, como exige el registro (Ley 1581).
        """
        if count < 1:
            raise ValueError("count debe ser al menos 1")
        emails = [loadtest_email(n) for n in range(1, count + 1)]
        # Un solo hash para todas: Argon2 es lento a propósito y la contraseña es la misma.
        password_hash = self._hasher.hash(password)
        consent = PolicyConsent(version=self._policy_version, accepted_at=self._clock.now())
        try:
            for email in emails:
                if self._users.get_by_email(email) is None:
                    self._users.add(
                        NewUser(
                            name=LOADTEST_NAME,
                            email=email,
                            password_hash=password_hash,
                            role=UserRole.CITIZEN,
                            consent=consent,
                        )
                    )
            self._transaction.commit()
        except Exception:
            self._transaction.rollback()
            raise
        return emails

    def remove(self) -> int:
        """Borra las cuentas de carga y todo lo que crearon; devuelve cuántos reportes."""
        try:
            removal = self._data.delete_all()
            self._transaction.commit()
        except Exception:
            self._transaction.rollback()
            raise
        # Después de confirmar, como en la supresión (propuesta 39).
        self._photo_files.remove(removal.photo_keys)
        return removal.reports
