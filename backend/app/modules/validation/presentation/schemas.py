"""Esquemas HTTP del módulo de validación (objetivo 4)."""

import uuid
from collections.abc import Sequence
from datetime import datetime
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from app.modules.critical_services.domain.service_type import CriticalServiceType
from app.modules.reports.presentation.schemas import LocationResponse, SeverityLevel
from app.modules.validation.domain.agreement import (
    NEIGHBOR_TOLERANCE,
    BetweenZones,
    Correlation,
    KendallW,
    ZoneAgreement,
)
from app.modules.validation.domain.blind import (
    BlindCard,
    BlindZone,
    CurrentRoundView,
    EvaluatorZone,
    ServicePoint,
    ZoneView,
)
from app.modules.validation.domain.ports import ZoneSummary
from app.modules.validation.domain.results import DedupSummary, RoundResults, ZoneResult
from app.modules.validation.domain.rounds import (
    EvaluatorLabel,
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


# --- Resultados de la ronda (solo el administrador) ------------------------------------


class CorrelationResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    coefficient: float
    p_value: float

    @classmethod
    def maybe(cls, value: Correlation | None) -> "CorrelationResponse | None":
        return None if value is None else cls(coefficient=value.coefficient, p_value=value.p_value)


class KendallWResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    w: float
    chi2: float
    p_value: float

    @classmethod
    def maybe(cls, value: KendallW | None) -> "KendallWResponse | None":
        return None if value is None else cls(w=value.w, chi2=value.chi2, p_value=value.p_value)


class EvaluatorAgreementResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    # «Evaluador k»: nunca nombre, correo ni id (Ley 1581).
    evaluator: str
    spearman: CorrelationResponse | None
    kendall: CorrelationResponse | None


class ZoneAgreementResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    n_evaluators: int
    spearman: CorrelationResponse | None
    kendall: CorrelationResponse | None
    # null con un solo evaluador: la W necesita al menos dos.
    kendall_w: KendallWResponse | None
    within_one_pct: float
    per_evaluator: list[EvaluatorAgreementResponse]


class ResultReportResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_id: uuid.UUID
    # Solo para el administrador: identifica el reporte en el ranking comparado.
    road_name: str | None
    urgency_score: float
    motor_order: int
    # null si nadie envió el orden de la zona.
    panel_order: float | None
    disagreement: float | None
    within_one: bool | None


class DedupResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    reports: int
    reports_confirmed: int
    confirmations: int
    warnings_total: int
    warnings_confirmed: int
    warnings_created_anyway: int
    warnings_pending: int

    @classmethod
    def from_summary(cls, dedup: DedupSummary) -> "DedupResponse":
        return cls(
            reports=dedup.reports,
            reports_confirmed=dedup.reports_confirmed,
            confirmations=dedup.confirmations,
            warnings_total=dedup.warnings_total,
            warnings_confirmed=dedup.warnings_confirmed,
            warnings_created_anyway=dedup.warnings_created_anyway,
            warnings_pending=dedup.warnings_pending,
        )


def _agreement(
    agreement: ZoneAgreement | None, numbers: dict[uuid.UUID, int]
) -> ZoneAgreementResponse | None:
    if agreement is None:
        return None
    per_evaluator = sorted(agreement.per_evaluator.items(), key=lambda item: numbers[item[0]])
    return ZoneAgreementResponse(
        n_evaluators=agreement.n_evaluators,
        spearman=CorrelationResponse.maybe(agreement.spearman),
        kendall=CorrelationResponse.maybe(agreement.kendall),
        kendall_w=KendallWResponse.maybe(agreement.kendall_w),
        within_one_pct=agreement.within_one_pct,
        per_evaluator=[
            EvaluatorAgreementResponse(
                evaluator=EvaluatorLabel(numbers[evaluator]).text,
                spearman=CorrelationResponse.maybe(values.spearman),
                kendall=CorrelationResponse.maybe(values.kendall),
            )
            for evaluator, values in per_evaluator
        ],
    )


class ZoneResultResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    zone_id: int
    name: str
    concentration: Concentration
    n_reports: int
    agreement: ZoneAgreementResponse | None
    dedup: DedupResponse
    reports: list[ResultReportResponse]

    @classmethod
    def from_result(cls, result: ZoneResult, numbers: dict[uuid.UUID, int]) -> "ZoneResultResponse":
        zone, agreement = result.zone, result.agreement
        reports = []
        for entry in zone.entries:
            panel = agreement.panel_order[entry.report_id] if agreement else None
            reports.append(
                ResultReportResponse(
                    report_id=entry.report_id,
                    road_name=zone.road_names.get(entry.report_id),
                    urgency_score=float(entry.urgency_score),
                    motor_order=entry.motor_order,
                    panel_order=panel,
                    disagreement=agreement.disagreement[entry.report_id] if agreement else None,
                    within_one=(
                        None
                        if panel is None
                        else abs(entry.motor_order - panel) <= NEIGHBOR_TOLERANCE
                    ),
                )
            )
        return cls(
            zone_id=zone.zone_id,
            name=zone.name,
            concentration=zone.concentration,
            n_reports=len(zone.entries),
            agreement=_agreement(agreement, numbers),
            dedup=DedupResponse.from_summary(result.dedup),
            reports=reports,
        )


class BetweenZonesResponse(BaseModel):
    """Prueba entre zonas; ``computable`` es false con ``reason`` cuando no se pudo hacer."""

    model_config = ConfigDict(frozen=True)

    computable: bool
    test: str | None = None
    statistic: float | None = None
    p_value: float | None = None
    significant: bool | None = None
    reason: str | None = None


class RoundResultsResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    round: RoundSummaryResponse
    zones: list[ZoneResultResponse]
    between: BetweenZonesResponse

    @classmethod
    def from_results(cls, results: RoundResults) -> "RoundResultsResponse":
        numbers = dict(results.evaluator_numbers)
        between = results.between
        return cls(
            round=RoundSummaryResponse.from_summary(results.round),
            zones=[ZoneResultResponse.from_result(z, numbers) for z in results.zones],
            between=(
                BetweenZonesResponse(
                    computable=True,
                    test=between.test,
                    statistic=between.statistic,
                    p_value=between.p_value,
                    significant=between.significant,
                )
                if isinstance(between, BetweenZones)
                else BetweenZonesResponse(computable=False, reason=between.reason)
            ),
        )
