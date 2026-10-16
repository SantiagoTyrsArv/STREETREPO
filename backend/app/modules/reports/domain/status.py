from enum import StrEnum


class ReportStatus(StrEnum):
    """Estado del reporte (guía 2.4). Valores del ENUM ``estado`` del diagrama ER.

    Las transiciones válidas se definen en la máquina de estados (fase 3).
    """

    REGISTERED = "registrado"
    EVALUATED = "evaluado"
    PRIORITIZED = "priorizado"
    REPAIRED = "reparado"
