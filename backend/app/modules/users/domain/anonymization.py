"""Valores con los que se anonimiza a un titular que pide la supresión (propuesta 10).

Se borran los datos personales de la cuenta, pero la fila se conserva: sus reportes son
datos de la vía y la constancia del trámite (``solicitud_supresion``) debe sobrevivir.
"""

import uuid

ANONYMIZED_NAME = "Titular suprimido"
# No es un hash Argon2: ninguna contraseña puede coincidir con él.
DISABLED_CREDENTIAL_MARKER = "!suprimido"
# ``.invalid`` está reservado (RFC 2606): el correo no puede pertenecer a nadie.
_ANONYMIZED_EMAIL_DOMAIN = "anonimo.invalid"


def anonymized_email(user_id: uuid.UUID) -> str:
    """Correo de relleno único por usuario (``usuario.correo`` es UNIQUE y obligatorio)."""
    return f"suprimido-{user_id.hex}@{_ANONYMIZED_EMAIL_DOMAIN}"
