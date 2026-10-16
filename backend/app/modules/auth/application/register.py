"""Caso de uso: registro de un ciudadano con consentimiento informado (HU-10, HU-11)."""

from dataclasses import dataclass

from app.modules.auth.application.errors import (
    PolicyNotAcceptedError,
    PolicyVersionMismatchError,
)
from app.modules.auth.domain.passwords import check_password_policy
from app.modules.auth.domain.ports import PasswordHasher
from app.modules.users.domain.entities import NewUser, PolicyConsent, User, normalize_email
from app.modules.users.domain.ports import UserRepository
from app.modules.users.domain.role import UserRole
from app.shared.application.clock import Clock
from app.shared.application.transaction import TransactionManager


@dataclass(frozen=True, slots=True)
class Registration:
    name: str
    email: str
    password: str
    accepted_policy: bool
    policy_version: str


class RegisterCitizen:
    """Crea siempre un ciudadano: el rol de administrador nunca se obtiene por registro."""

    def __init__(
        self,
        users: UserRepository,
        hasher: PasswordHasher,
        clock: Clock,
        transaction: TransactionManager,
        current_policy_version: str,
    ) -> None:
        self._users = users
        self._hasher = hasher
        self._clock = clock
        self._transaction = transaction
        self._current_policy_version = current_policy_version

    def execute(self, data: Registration) -> User:
        if not data.accepted_policy:
            raise PolicyNotAcceptedError("Debes aceptar la política de tratamiento de datos")
        if data.policy_version != self._current_policy_version:
            raise PolicyVersionMismatchError(
                f"La política vigente es la versión {self._current_policy_version}"
            )
        check_password_policy(data.password)
        try:
            user = self._users.add(
                NewUser(
                    name=data.name.strip(),
                    email=normalize_email(data.email),
                    password_hash=self._hasher.hash(data.password),
                    role=UserRole.CITIZEN,
                    consent=PolicyConsent(
                        version=data.policy_version, accepted_at=self._clock.now()
                    ),
                )
            )
            self._transaction.commit()
        except Exception:
            self._transaction.rollback()
            raise
        return user
