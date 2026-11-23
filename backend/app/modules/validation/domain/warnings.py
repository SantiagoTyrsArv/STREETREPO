"""Avisos de «Posible duplicado» y la decisión del ciudadano (objetivo 4, HU-09).

Cada vez que el servidor ofrece candidatos a 25 m (``GET /reports/nearby`` con resultados o
el 409 de ``POST /reports``) queda un aviso ``pendiente``. Si el ciudadano confirma uno de
los candidatos pasa a ``confirmo``; si crea el suyo de todos modos, a ``creo_igual``. Uno
que sigue pendiente al exportar se informa como «sin decisión» (sección 8.1 del diseño).
"""

from enum import StrEnum


class WarningDecision(StrEnum):
    """Valores del ENUM ``decision_aviso`` de la base."""

    PENDING = "pendiente"
    CONFIRMED = "confirmo"
    CREATED_ANYWAY = "creo_igual"
