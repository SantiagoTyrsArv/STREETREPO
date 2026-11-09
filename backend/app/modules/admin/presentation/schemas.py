"""Esquemas HTTP del panel administrativo.

Los puntajes (S, F, P, U) se envían como número JSON: el panel solo los muestra con coma
decimal. En la base y el dominio son ``Decimal`` con dos cifras.
"""

import uuid
from collections.abc import Sequence
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.modules.admin.domain.ranking_view import (
    HeatPoint,
    RankingItem,
    RankingPage,
    StatusSummary,
)
from app.modules.admin.domain.report_detail import (
    AdminHistoryEntry,
    AdminReportDetail,
    EvaluationBreakdown,
)
from app.modules.reports.domain.status import ReportStatus
from app.modules.reports.presentation.schemas import SeverityLevel


class RankingItemResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: uuid.UUID
    status: ReportStatus
    severity: SeverityLevel
    s: float
    f: float
    p: float
    u: float
    # Sin vía OSM a 30 m: chip «Revisar vía» (guía 2.2).
    needs_road_review: bool
    # Nombre de la vía OSM o un texto de reserva (propuesta 41).
    address: str
    confirmations: int
    created_at: datetime

    @classmethod
    def from_item(cls, item: RankingItem) -> "RankingItemResponse":
        return cls(
            id=item.report_id,
            status=item.status,
            severity=SeverityLevel.from_domain(item.severity),
            s=float(item.severity_score),
            f=float(item.flow_score),
            p=float(item.proximity_score),
            u=float(item.urgency_score),
            needs_road_review=item.needs_road_review,
            address=item.address,
            confirmations=item.confirmations,
            created_at=item.created_at,
        )


class RankingResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    items: list[RankingItemResponse]
    total: int
    limit: int
    offset: int

    @classmethod
    def from_page(cls, page: RankingPage, limit: int, offset: int) -> "RankingResponse":
        return cls(
            items=[RankingItemResponse.from_item(item) for item in page.items],
            total=page.total,
            limit=limit,
            offset=offset,
        )


class SummaryResponse(BaseModel):
    """Activos (todo salvo Reparado) · Evaluados · Priorizados · Reparados."""

    model_config = ConfigDict(frozen=True)

    active: int
    evaluated: int
    prioritized: int
    repaired: int

    @classmethod
    def from_summary(cls, summary: StatusSummary) -> "SummaryResponse":
        return cls(
            active=summary.active,
            evaluated=summary.evaluated,
            prioritized=summary.prioritized,
            repaired=summary.repaired,
        )


class HeatPointResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    lat: float
    lon: float
    u: float


class HeatmapResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    points: list[HeatPointResponse]

    @classmethod
    def from_points(cls, points: Sequence[HeatPoint]) -> "HeatmapResponse":
        return cls(
            points=[
                HeatPointResponse(lat=point.lat, lon=point.lon, u=float(point.urgency_score))
                for point in points
            ]
        )


class AdminLocationResponse(BaseModel):
    """Ubicación exacta: el detalle es solo para administradores."""

    model_config = ConfigDict(frozen=True)

    lat: float
    lon: float


class RoadResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str | None
    # Etiqueta ``highway`` de OSM (primary, secondary…), que define F.
    highway: str


class NearestServiceResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str | None
    service_type: str
    distance_m: float


class EvaluationResponse(BaseModel):
    """Desglose del cálculo con los pesos de la versión usada (guía 4.5)."""

    model_config = ConfigDict(frozen=True)

    s: float
    f: float
    p: float
    u: float
    w_severity: float
    w_flow: float
    w_proximity: float
    config_id: int
    # null = ningún servicio crítico a menos de 500 m (P = 0).
    service: NearestServiceResponse | None
    calculated_at: datetime

    @classmethod
    def from_breakdown(cls, evaluation: EvaluationBreakdown) -> "EvaluationResponse":
        service = evaluation.service
        return cls(
            s=float(evaluation.severity_score),
            f=float(evaluation.flow_score),
            p=float(evaluation.proximity_score),
            u=float(evaluation.urgency_score),
            w_severity=float(evaluation.w_severity),
            w_flow=float(evaluation.w_flow),
            w_proximity=float(evaluation.w_proximity),
            config_id=evaluation.config_id,
            service=(
                NearestServiceResponse(
                    name=service.name,
                    service_type=service.service_type,
                    distance_m=float(service.distance_m),
                )
                if service
                else None
            ),
            calculated_at=evaluation.calculated_at,
        )


class AdminHistoryEntryResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    previous_status: ReportStatus | None
    status: ReportStatus
    changed_at: datetime
    note: str | None
    # null = cambio automático del sistema (o cuenta suprimida).
    changed_by_name: str | None

    @classmethod
    def from_entry(cls, entry: AdminHistoryEntry) -> "AdminHistoryEntryResponse":
        return cls(
            previous_status=entry.previous_status,
            status=entry.status,
            changed_at=entry.changed_at,
            note=entry.note,
            changed_by_name=entry.changed_by_name,
        )


class AdminReportResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: uuid.UUID
    status: ReportStatus
    # Estados a los que el administrador puede llevar el reporte (máquina de estados).
    allowed_next_statuses: list[ReportStatus]
    severity: SeverityLevel
    description: str | None
    location: AdminLocationResponse
    address: str
    needs_road_review: bool
    road: RoadResponse | None
    # Solo en el panel (guía 7.2 y 10.3).
    reporter_name: str
    created_at: datetime
    confirmations: int
    # null = el motor aún no lo evaluó.
    evaluation: EvaluationResponse | None
    history: list[AdminHistoryEntryResponse]

    @classmethod
    def from_detail(cls, detail: AdminReportDetail) -> "AdminReportResponse":
        return cls(
            id=detail.id,
            status=detail.status,
            allowed_next_statuses=list(detail.allowed_next_statuses),
            severity=SeverityLevel.from_domain(detail.severity),
            description=detail.description,
            location=AdminLocationResponse(
                lat=detail.location.latitude, lon=detail.location.longitude
            ),
            address=detail.address,
            needs_road_review=detail.needs_road_review,
            road=(
                RoadResponse(name=detail.road.name, highway=detail.road.highway)
                if detail.road
                else None
            ),
            reporter_name=detail.reporter_name,
            created_at=detail.created_at,
            confirmations=detail.confirmations,
            evaluation=(
                EvaluationResponse.from_breakdown(detail.evaluation) if detail.evaluation else None
            ),
            history=[AdminHistoryEntryResponse.from_entry(entry) for entry in detail.history],
        )
