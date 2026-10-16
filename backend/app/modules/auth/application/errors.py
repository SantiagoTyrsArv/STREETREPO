class InvalidCredentialsError(Exception):
    """Correo o contraseña incorrectos, o cuenta inactiva (sin decir cuál, anti enumeración)."""


class InvalidRefreshTokenError(Exception):
    """Token de refresco desconocido, vencido, revocado o reutilizado."""


class PolicyNotAcceptedError(Exception):
    """El registro exige aceptar la política de tratamiento de datos (Ley 1581)."""


class PolicyVersionMismatchError(Exception):
    """El ciudadano aceptó una versión de la política que ya no está vigente."""
