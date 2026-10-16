import uuid
from typing import Protocol

from app.modules.users.domain.entities import NewUser, User


class EmailAlreadyRegisteredError(Exception):
    """Ya existe una cuenta con ese correo."""


class UserRepository(Protocol):
    def get_by_id(self, user_id: uuid.UUID) -> User | None: ...

    def get_by_email(self, email: str) -> User | None:
        """Busca por correo ya normalizado."""
        ...

    def update_password_hash(self, user_id: uuid.UUID, password_hash: str) -> None: ...

    def add(self, user: NewUser) -> User:
        """Crea el usuario; lanza ``EmailAlreadyRegisteredError`` si el correo existe."""
        ...
