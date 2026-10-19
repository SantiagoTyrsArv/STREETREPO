import uuid
from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, ConfigDict

from app.modules.reports.domain.entities import ReportDetails
from app.modules.reports.domain.severity import Severity
from app.modules.reports.domain.status import ReportStatus


class SeverityLevel(StrEnum):
    """Severidad en la API; en la base es un código ordinal (``Severity``)."""

    LOW = "baja"
    MEDIUM = "media"
    HIGH = "alta"

    def to_domain(self) -> Severity:
        return _TO_DOMAIN[self]

    @classmethod
    def from_domain(cls, severity: Severity) -> "SeverityLevel":
        return next(level for level, value in _TO_DOMAIN.items() if value is severity)


_TO_DOMAIN: dict[SeverityLevel, Severity] = {
    SeverityLevel.LOW: Severity.LOW,
    SeverityLevel.MEDIUM: Severity.MEDIUM,
    SeverityLevel.HIGH: Severity.HIGH,
}


class LocationResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    longitude: float
    latitude: float


class ReportResponse(BaseModel):
    """Reporte visto por su autor: ubicación exacta (propuesta 40), sin datos de otros."""

    model_config = ConfigDict(frozen=True)

    id: uuid.UUID
    status: ReportStatus
    severity: SeverityLevel
    description: str | None
    location: LocationResponse
    # Nombre de la vía OSM o un texto de reserva (propuesta 41).
    address: str
    # Urgencia U en escala 0-10; null si aún no se evaluó.
    priority_score: Decimal | None
    needs_road_review: bool
    created_at: datetime

    @classmethod
    def from_details(cls, report: ReportDetails) -> "ReportResponse":
        return cls(
            id=report.id,
            status=report.status,
            severity=SeverityLevel.from_domain(report.severity),
            description=report.description,
            location=LocationResponse(
                longitude=report.location.longitude, latitude=report.location.latitude
            ),
            address=report.address,
            priority_score=report.priority_score,
            needs_road_review=report.needs_road_review,
            created_at=report.created_at,
        )
