"""Reporte nuevo enviado por un ciudadano (HU-02): foto, ubicación y severidad obligatorias."""

import uuid
from dataclasses import dataclass

from app.modules.reports.domain.severity import Severity
from app.shared.domain.geo import BoundingBox, GeoPoint

# Texto libre opcional; corto a propósito porque puede contener datos personales
# y se borra en la supresión (propuesta 10).
DESCRIPTION_MAX_LENGTH = 500


class InvalidReportError(ValueError):
    """Los datos del reporte no cumplen las reglas del dominio."""


class IdempotencyKeyReusedError(ValueError):
    """La clave de idempotencia ya se usó para un reporte con otros datos (decisión 46a).

    Un reintento legítimo repite exactamente el envío; si cambió la ubicación, la severidad
    o la descripción, devolver el reporte anterior haría creer que se guardó lo nuevo.
    """


class LocationOutsideServiceAreaError(ValueError):
    """La ubicación está fuera del área de servicio configurada (propuesta 37)."""


def ensure_in_service_area(location: GeoPoint, service_area: BoundingBox) -> None:
    """Lanza ``LocationOutsideServiceAreaError`` si el punto está fuera del área."""
    if not service_area.contains(location):
        raise LocationOutsideServiceAreaError(
            "La ubicación está fuera del área de servicio del sistema"
        )


def clean_description(description: str | None) -> str | None:
    """Recorta la descripción; una descripción en blanco se guarda como NULL."""
    if description is None:
        return None
    cleaned = description.strip()
    if len(cleaned) > DESCRIPTION_MAX_LENGTH:
        raise InvalidReportError(
            f"La descripción admite como máximo {DESCRIPTION_MAX_LENGTH} caracteres"
        )
    return cleaned or None


@dataclass(frozen=True, slots=True)
class NewReport:
    """Reporte válido listo para guardarse. Se construye con ``NewReport.create``."""

    user_id: uuid.UUID
    location: GeoPoint
    severity: Severity
    description: str | None
    # Cabecera Idempotency-Key: un reintento con la misma clave no crea otro reporte.
    idempotency_key: uuid.UUID | None

    @classmethod
    def create(
        cls,
        *,
        user_id: uuid.UUID,
        location: GeoPoint,
        severity: Severity,
        description: str | None,
        idempotency_key: uuid.UUID | None,
        service_area: BoundingBox,
    ) -> "NewReport":
        """Valida la descripción y que la ubicación esté dentro del área de servicio."""
        ensure_in_service_area(location, service_area)
        return cls(
            user_id=user_id,
            location=location,
            severity=severity,
            description=clean_description(description),
            idempotency_key=idempotency_key,
        )
