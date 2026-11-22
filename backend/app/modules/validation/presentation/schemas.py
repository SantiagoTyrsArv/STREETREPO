"""Esquemas HTTP del módulo de validación (objetivo 4)."""

import uuid
from collections.abc import Sequence
from datetime import datetime
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from app.modules.validation.domain.ports import ZoneSummary
from app.modules.validation.domain.rounds import (
    RoundProgress,
    RoundStatus,
    RoundSummary,
    ZoneProgress,
)
from app.modules.validation.domain.zones import Concentration

MAX_SAMPLE_SIZE = 100


class ZoneResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: int
    name: str
    concentration: Concentration
    active_reports: int
    total_reports: int
    # Polígono GeoJSON simplificado para dibujarlo en el mapa del panel.
    geometry: dict[str, Any]

    @classmethod
    def from_summary(cls, zone: ZoneSummary) -> "ZoneResponse":
        return cls(
            id=zone.id,
            name=zone.name,
            concentration=zone.concentration,
            active_reports=zone.active_reports,
            total_reports=zone.total_reports,
            geometry=zone.geometry_geojson,
        )


class ZonesResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    items: list[ZoneResponse]

    @classmethod
    def from_summaries(cls, zones: Sequence[ZoneSummary]) -> "ZonesResponse":
        return cls(items=[ZoneResponse.from_summary(zone) for zone in zones])


class OpenRoundRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
    sample_size: Annotated[int, Field(ge=1, le=MAX_SAMPLE_SIZE)]


class RoundCreatedResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: uuid.UUID


class RoundSummaryResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: uuid.UUID
    name: str
    status: RoundStatus
    sample_size: int
    opened_at: datetime
    closed_at: datetime | None

    @classmethod
    def from_summary(cls, summary: RoundSummary) -> "RoundSummaryResponse":
        return cls(
            id=summary.round_id,
            name=summary.name,
            status=summary.status,
            sample_size=summary.sample_size,
            opened_at=summary.opened_at,
            closed_at=summary.closed_at,
        )


class RoundsResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    items: list[RoundSummaryResponse]
    limit: int
    offset: int


class ZoneProgressResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    zone_id: int
    name: str
    concentration: Concentration
    n_reports: int
    # Etiquetas anónimas «Evaluador k»; nunca nombres ni correos.
    submitted_by: list[str]

    @classmethod
    def from_progress(cls, zone: ZoneProgress) -> "ZoneProgressResponse":
        return cls(
            zone_id=zone.zone_id,
            name=zone.name,
            concentration=zone.concentration,
            n_reports=zone.n_reports,
            submitted_by=[label.text for label in zone.submitted_by],
        )


class RoundProgressResponse(RoundSummaryResponse):
    zones: list[ZoneProgressResponse]

    @classmethod
    def from_round_progress(cls, progress: RoundProgress) -> "RoundProgressResponse":
        summary = progress.summary
        return cls(
            id=summary.round_id,
            name=summary.name,
            status=summary.status,
            sample_size=summary.sample_size,
            opened_at=summary.opened_at,
            closed_at=summary.closed_at,
            zones=[ZoneProgressResponse.from_progress(z) for z in progress.zones],
        )
