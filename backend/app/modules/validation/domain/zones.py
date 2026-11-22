"""Zonas de validación (objetivo 4)."""

from enum import StrEnum


class Concentration(StrEnum):
    """Concentración de reportes de una zona de validación."""

    HIGH = "alta"
    LOW = "baja"
