"""Caso de uso: crear una cuenta de administrador desde la línea de comandos.

El registro público solo crea ciudadanos; los administradores (Secretaría de
Infraestructura) se crean con ``python -m app.cli create-admin``.
"""

from app.modules.auth.domain.passwords import check_password_policy
from app.modules.auth.domain.ports import PasswordHasher
from app.modules.users.domain.entities import NewUser, User, normalize_email
from app.modules.users.domain.ports import UserRepository
from app.modules.users.domain.role import UserRole
from app.shared.application.transaction import TransactionManager


class CreateAdmin:
    def __init__(
        self, users: UserRepository, hasher: PasswordHasher, transaction: TransactionManager
    ) -> None:
        self._users = users
        self._hasher = hasher
        self._transaction = transaction

    def execute(self, name: str, email: str, password: str) -> User:
        check_password_policy(password)
        try:
            user = self._users.add(
                NewUser(
                    name=name.strip(),
                    email=normalize_email(email),
                    password_hash=self._hasher.hash(password),
                    role=UserRole.ADMIN,
                    consent=None,
                )
            )
            self._transaction.commit()
        except Exception:
            self._transaction.rollback()
            raise
        return user
