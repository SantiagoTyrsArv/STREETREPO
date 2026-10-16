from enum import StrEnum


class CriticalServiceType(StrEnum):
    """Tipo de servicio crítico. Valores del ENUM ``tipo`` del diagrama ER."""

    HOSPITAL = "hospital"
    SCHOOL = "escuela"
