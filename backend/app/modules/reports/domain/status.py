from enum import StrEnum


class ReportStatus(StrEnum):
    """Estado del reporte (guía 2.4). Valores del ENUM ``estado`` del diagrama ER.

    Las transiciones válidas se definen en ``status_machine``.
    """

    REGISTERED = "registrado"
    EVALUATED = "evaluado"
    PRIORITIZED = "priorizado"
    REPAIRED = "reparado"
