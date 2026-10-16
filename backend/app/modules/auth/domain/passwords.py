"""Política de contraseñas (guía 7.1; OWASP ASVS 4.0, V2.1)."""

from typing import Final

# ASVS V2.1.1: al menos 12 caracteres. V2.1.2: admitir al menos 64; se fija un
# tope para que nadie envíe megabytes a Argon2.
MIN_PASSWORD_LENGTH: Final = 12
MAX_PASSWORD_LENGTH: Final = 128


class WeakPasswordError(ValueError):
    """La contraseña no cumple la política."""


def check_password_policy(password: str) -> None:
    """Solo longitud: ASVS V2.1.9 desaconseja exigir tipos de caracteres."""
    if len(password) < MIN_PASSWORD_LENGTH:
        raise WeakPasswordError(
            f"La contraseña debe tener al menos {MIN_PASSWORD_LENGTH} caracteres"
        )
    if len(password) > MAX_PASSWORD_LENGTH:
        raise WeakPasswordError(
            f"La contraseña puede tener como máximo {MAX_PASSWORD_LENGTH} caracteres"
        )
