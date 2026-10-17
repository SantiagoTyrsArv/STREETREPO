from datetime import timedelta


class InvalidCredentialsError(Exception):
    """Correo o contraseña incorrectos, o cuenta inactiva (sin decir cuál, anti enumeración)."""


class InvalidRefreshTokenError(Exception):
    """Token de refresco desconocido, vencido, revocado o reutilizado."""


class PolicyNotAcceptedError(Exception):
    """El registro exige aceptar la política de tratamiento de datos (Ley 1581)."""


class PolicyVersionMismatchError(Exception):
    """El ciudadano aceptó una versión de la política que ya no está vigente."""


class AccountLockedError(Exception):
    """Demasiados intentos fallidos seguidos: la cuenta está bloqueada por un tiempo."""

    def __init__(self, retry_after: timedelta) -> None:
        super().__init__(f"Cuenta bloqueada; reintentar en {retry_after}")
        self.retry_after = retry_after


class PasswordConfirmationRequiredError(Exception):
    """La acción es sensible y exige confirmar la contraseña actual (propuesta 26)."""


class WrongPasswordError(Exception):
    """La contraseña de confirmación no coincide."""
