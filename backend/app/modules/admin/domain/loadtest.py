"""Cuentas de la prueba de carga (fase 8, decisión 68): qué las identifica.

Viven en un subdominio de ``example.com``, reservado para ejemplos (RFC 2606), así que nunca
es un correo real y se reconocen y se borran enteras sin tocar cuentas reales. No se usa
``.invalid`` como en la demostración: esas cuentas no pueden iniciar sesión (la API rechaza
el dominio), y las de carga sí lo necesitan.
"""

from typing import Final

LOADTEST_EMAIL_DOMAIN: Final = "carga.example.com"
LOADTEST_NAME: Final = "Cuenta de carga"


def loadtest_email(number: int) -> str:
    """``carga-001@carga.example.com``, ``carga-002@carga.example.com``…"""
    return f"carga-{number:03d}@{LOADTEST_EMAIL_DOMAIN}"
