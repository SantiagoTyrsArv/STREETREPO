from argon2 import PasswordHasher as Argon2Hasher
from argon2.exceptions import InvalidHashError, VerificationError


class Argon2PasswordHasher:
    """Implementa ``PasswordHasher`` con Argon2id (guía 7.1).

    Usa los parámetros por defecto de argon2-cffi (perfil de RFC 9106 de baja
    memoria: 64 MiB, 3 iteraciones, 4 hilos). Si suben en una versión futura,
    ``needs_rehash`` permite rehacer el hash en el siguiente inicio de sesión.
    """

    def __init__(self, hasher: Argon2Hasher | None = None) -> None:
        self._hasher = hasher or Argon2Hasher()

    def hash(self, password: str) -> str:
        return self._hasher.hash(password)

    def verify(self, password_hash: str, password: str) -> bool:
        try:
            return self._hasher.verify(password_hash, password)
        except (VerificationError, InvalidHashError):
            return False

    def needs_rehash(self, password_hash: str) -> bool:
        try:
            return self._hasher.check_needs_rehash(password_hash)
        except InvalidHashError:
            return True
