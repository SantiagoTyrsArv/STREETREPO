import uuid
from collections.abc import Sequence
from datetime import datetime
from typing import Protocol

from app.modules.users.domain.deletion_request import DeletionRequest
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

    def update_profile(self, user_id: uuid.UUID, name: str, email: str) -> User:
        """Actualiza nombre y correo (ya normalizado); lanza ``EmailAlreadyRegisteredError``
        si el correo es de otra cuenta."""
        ...

    def anonymize(self, user_id: uuid.UUID) -> None:
        """Borra nombre, correo y hash de la contraseña y desactiva la cuenta."""
        ...


class DeletionRequestRepository(Protocol):
    def add_attended(self, user_id: uuid.UUID, at: datetime) -> DeletionRequest:
        """Registra una solicitud atendida en el mismo momento en que se pidió (decisión 23)."""
        ...


class ReportTextEraser(Protocol):
    """Borra el texto libre que el titular escribió en sus reportes: puede contener datos
    personales (propuesta 10). El reporte, su ubicación y su severidad se conservan."""

    def clear_descriptions(self, user_id: uuid.UUID) -> None: ...


class ReportPhotoEraser(Protocol):
    """Quita la evidencia fotográfica de los reportes del titular: las fotos pueden mostrar
    rostros o placas y no se distinguen de forma automática (propuestas 10 y 39)."""

    def detach_photos(self, user_id: uuid.UUID) -> Sequence[str]:
        """Borra las filas de ``evidencia`` de sus reportes y devuelve las claves de las
        fotos, para borrar los archivos después de confirmar la transacción."""
        ...


class PhotoFileRemover(Protocol):
    def remove(self, photo_keys: Sequence[str]) -> Sequence[str]:
        """Borra cada foto y su miniatura, con reintentos. No lanza: devuelve las claves que
        no pudo borrar, que recoge después la limpieza de fotos huérfanas."""
        ...
