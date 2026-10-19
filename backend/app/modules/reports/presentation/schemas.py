import uuid
from collections.abc import Sequence
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.modules.reports.domain.duplicates import DuplicateCandidate
from app.modules.reports.domain.entities import ReportDetails
from app.modules.reports.domain.my_reports import (
    MyReportsPage,
    OwnReport,
    PublicReportView,
)
from app.modules.reports.domain.public_location import PUBLIC_COORDINATE_DECIMALS
from app.modules.reports.domain.report_view import (
    FullReportView,
    LimitedReportView,
    StatusHistoryEntry,
)
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


class OwnReportItem(ReportResponse):
    """Reporte creado por el usuario, completo."""

    relation: Literal["own"] = "own"
    confirmations: int

    @classmethod
    def from_own(cls, item: OwnReport) -> "OwnReportItem":
        base = ReportResponse.from_details(item.details)
        return cls(**base.model_dump(), confirmations=item.confirmations)


class ConfirmedReportItem(BaseModel):
    """Reporte ajeno que el usuario confirmó: vista pública, sin autor ni descripción."""

    model_config = ConfigDict(frozen=True)

    relation: Literal["confirmed"] = "confirmed"
    id: uuid.UUID
    # Ubicación pública: redondeada a 4 decimales, nunca la exacta.
    location: LocationResponse
    status: ReportStatus
    severity: SeverityLevel
    address: str
    confirmations: int
    created_at: datetime
    confirmed_at: datetime

    @classmethod
    def from_public(cls, view: PublicReportView, confirmed_at: datetime) -> "ConfirmedReportItem":
        return cls(
            id=view.id,
            location=LocationResponse(
                longitude=view.location.longitude, latitude=view.location.latitude
            ),
            status=view.status,
            severity=SeverityLevel.from_domain(view.severity),
            address=view.address,
            confirmations=view.confirmations,
            created_at=view.created_at,
            confirmed_at=confirmed_at,
        )


MyReportItem = Annotated[OwnReportItem | ConfirmedReportItem, Field(discriminator="relation")]


class MyReportsResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    items: list[MyReportItem]
    total: int
    limit: int
    offset: int

    @classmethod
    def from_page(cls, page: MyReportsPage) -> "MyReportsResponse":
        items: list[OwnReportItem | ConfirmedReportItem] = [
            OwnReportItem.from_own(item)
            if isinstance(item, OwnReport)
            else ConfirmedReportItem.from_public(item.public, item.confirmed_at)
            for item in page.items
        ]
        return cls(items=items, total=page.total, limit=page.limit, offset=page.offset)


class StatusHistoryEntryResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: ReportStatus
    changed_at: datetime
    # null para quien solo confirmó el reporte: la observación puede mencionar al autor.
    note: str | None

    @classmethod
    def from_entry(cls, entry: StatusHistoryEntry) -> "StatusHistoryEntryResponse":
        return cls(status=entry.status, changed_at=entry.changed_at, note=entry.note)


class OwnReportDetail(OwnReportItem):
    """Detalle completo: para el autor y los administradores."""

    history: list[StatusHistoryEntryResponse]

    @classmethod
    def from_full(cls, view: FullReportView) -> "OwnReportDetail":
        item = OwnReportItem.from_own(
            OwnReport(details=view.details, confirmations=view.confirmations)
        )
        return cls(
            **item.model_dump(),
            history=[StatusHistoryEntryResponse.from_entry(e) for e in view.history],
        )


class ConfirmedReportDetail(ConfirmedReportItem):
    """Detalle limitado: para quien confirmó el reporte."""

    history: list[StatusHistoryEntryResponse]

    @classmethod
    def from_limited(cls, view: LimitedReportView) -> "ConfirmedReportDetail":
        item = ConfirmedReportItem.from_public(view.public, view.confirmed_at)
        return cls(
            **item.model_dump(),
            history=[StatusHistoryEntryResponse.from_entry(e) for e in view.history],
        )


ReportDetailResponse = Annotated[
    OwnReportDetail | ConfirmedReportDetail, Field(discriminator="relation")
]
