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
