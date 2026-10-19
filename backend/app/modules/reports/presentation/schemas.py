import uuid
from collections.abc import Sequence
from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, ConfigDict

from app.modules.reports.domain.duplicates import DuplicateCandidate
from app.modules.reports.domain.entities import ReportDetails
from app.modules.reports.domain.public_location import PUBLIC_COORDINATE_DECIMALS
from app.modules.reports.domain.severity import Severity
from app.modules.reports.domain.status import ReportStatus
from app.shared.domain.geo_parameters import DEDUPLICATION_RADIUS_M


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


class DuplicateCandidateResponse(BaseModel):
    """Reporte cercano: sin autor ni ubicación exacta (guía 7.2, propuesta 36).

    ``is_mine`` dice si es del propio ciudadano, que no puede confirmarlo (propuesta 48).
    """

    model_config = ConfigDict(frozen=True)

    id: uuid.UUID
    # Ubicación pública: redondeada a 4 decimales (unos 11 m), nunca la exacta.
    location: LocationResponse
    # Metros del punto enviado a la ubicación pública, con un decimal (propuesta 43).
    distance_m: float
    status: ReportStatus
    severity: SeverityLevel
    confirmations: int
    address: str
    created_at: datetime
    is_mine: bool

    @classmethod
    def from_candidate(cls, candidate: DuplicateCandidate) -> "DuplicateCandidateResponse":
        return cls(
            id=candidate.id,
            location=LocationResponse(
                longitude=round(candidate.location.longitude, PUBLIC_COORDINATE_DECIMALS),
                latitude=round(candidate.location.latitude, PUBLIC_COORDINATE_DECIMALS),
            ),
            distance_m=round(candidate.distance_m, 1),
            status=candidate.status,
            severity=SeverityLevel.from_domain(candidate.severity),
            confirmations=candidate.confirmations,
            address=candidate.address,
            created_at=candidate.created_at,
            is_mine=candidate.is_mine,
        )


class NearbyReportsResponse(BaseModel):
    """Reportes activos a 25 m, del más cercano al más lejano."""

    model_config = ConfigDict(frozen=True)

    radius_m: float = DEDUPLICATION_RADIUS_M
    items: list[DuplicateCandidateResponse]

    @classmethod
    def from_candidates(cls, candidates: Sequence[DuplicateCandidate]) -> "NearbyReportsResponse":
        return cls(items=[DuplicateCandidateResponse.from_candidate(c) for c in candidates])
