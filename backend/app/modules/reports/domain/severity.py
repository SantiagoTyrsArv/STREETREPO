from enum import IntEnum


class Severity(IntEnum):
    """Severidad declarada por el ciudadano, guardada como SMALLINT en ``reporte.severidad``.

    El valor es un código ordinal; la normalización a S (3 / 6 / 10) vive en el
    módulo de priorización para poder ajustarla sin migrar datos.
    """

    LOW = 1
    MEDIUM = 2
    HIGH = 3
