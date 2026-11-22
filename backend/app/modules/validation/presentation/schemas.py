"""Esquemas HTTP del módulo de validación (objetivo 4)."""

import uuid
from collections.abc import Sequence
from datetime import datetime
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from app.modules.critical_services.domain.service_type import CriticalServiceType
from app.modules.reports.presentation.schemas import LocationResponse, SeverityLevel
from app.modules.validation.domain.blind import (
    BlindCard,
    BlindZone,
    CurrentRoundView,
    EvaluatorZone,
    ServicePoint,
    ZoneView,
)
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


# --- Evaluador (vista a ciegas) ----------------------------------------------------------
# Estos esquemas son la frontera de la prueba a ciegas: no llevan U, factores, jerarquía
# vial, distancias, confirmaciones, estado, fechas, autor, orden del motor ni la
# concentración de la zona. Agregar un campo aquí exige revisar la vista a ciegas.


class _Strict(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


def _location(longitude: float, latitude: float) -> LocationResponse:
    return LocationResponse(longitude=longitude, latitude=latitude)


class BlindRoundResponse(_Strict):
    id: uuid.UUID
    name: str


class BlindZoneResponse(_Strict):
    id: int
    name: str
    n_reports: int

    @classmethod
    def from_zone(cls, zone: BlindZone) -> "BlindZoneResponse":
        return cls(id=zone.id, name=zone.name, n_reports=zone.n_reports)


class EvaluatorZoneResponse(BlindZoneResponse):
    submitted: bool

    @classmethod
    def from_evaluator_zone(cls, item: EvaluatorZone) -> "EvaluatorZoneResponse":
        zone = item.zone
        return cls(id=zone.id, name=zone.name, n_reports=zone.n_reports, submitted=item.submitted)


class CurrentRoundResponse(_Strict):
    round: BlindRoundResponse
    zones: list[EvaluatorZoneResponse]

    @classmethod
    def from_view(cls, view: CurrentRoundView) -> "CurrentRoundResponse":
        return cls(
            round=BlindRoundResponse(id=view.round_id, name=view.name),
            zones=[EvaluatorZoneResponse.from_evaluator_zone(z) for z in view.zones],
        )


class ServicePointResponse(_Strict):
    name: str | None
    type: CriticalServiceType
    location: LocationResponse

    @classmethod
    def from_point(cls, point: ServicePoint) -> "ServicePointResponse":
        return cls(
            name=point.name,
            type=point.type,
            location=_location(point.location.longitude, point.location.latitude),
        )


class BlindCardResponse(_Strict):
    report_id: uuid.UUID
    description: str | None
    road_name: str | None
    severity: SeverityLevel
    # Ubicación exacta: el evaluador es parte del equipo de la prueba, como el administrador.
    location: LocationResponse
    nearby_services: list[ServicePointResponse]

    @classmethod
    def from_card(cls, card: BlindCard) -> "BlindCardResponse":
        return cls(
            report_id=card.report_id,
            description=card.description,
            road_name=card.road_name,
            severity=SeverityLevel.from_domain(card.severity),
            location=_location(card.location.longitude, card.location.latitude),
            nearby_services=[ServicePointResponse.from_point(s) for s in card.nearby_services],
        )


class ZoneCardsResponse(_Strict):
    zone: BlindZoneResponse
    # En el orden inicial propio del evaluador (shuffle_for).
    cards: list[BlindCardResponse]
    submitted: bool

    @classmethod
    def from_view(cls, view: ZoneView) -> "ZoneCardsResponse":
        return cls(
            zone=BlindZoneResponse.from_zone(view.zone),
            cards=[BlindCardResponse.from_card(card) for card in view.cards],
            submitted=view.submitted,
        )


class SubmitOrderRequest(_Strict):
    # Sin mínimo aquí: la lista vacía la rechaza el dominio con EVALUATION_ORDER_INVALID.
    report_ids: Annotated[list[uuid.UUID], Field(max_length=MAX_SAMPLE_SIZE)]


class OrderSubmittedResponse(_Strict):
    zone_id: int
    submitted: bool
