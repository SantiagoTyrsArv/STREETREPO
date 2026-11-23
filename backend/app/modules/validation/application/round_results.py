"""Caso de uso: resultados de una ronda cerrada y datos de revisión (objetivo 4, HU-09)."""

import uuid

from app.modules.validation.domain.agreement import ZoneRanking, between_zones, zone_agreement
from app.modules.validation.domain.ports import RoundResultsReader
from app.modules.validation.domain.results import (
    ReviewReport,
    ReviewWarning,
    RoundResults,
    RoundStillOpenError,
    ZoneResult,
    ZoneRoundData,
)
from app.modules.validation.domain.rounds import RoundNotFoundError, RoundStatus, RoundSummary


def _ranking(zone: ZoneRoundData) -> ZoneRanking:
    return ZoneRanking(
        zone_id=zone.zone_id,
        concentration=zone.concentration,
        motor_order={entry.report_id: entry.motor_order for entry in zone.entries},
        evaluator_orders=zone.evaluator_orders,
    )


class RoundResultsService:
    """Las métricas solo se calculan con la ronda cerrada: mientras está abierta, otro
    evaluador podría cambiarlas. Los archivos de revisión manual se sirven siempre."""

    def __init__(self, reader: RoundResultsReader) -> None:
        self._reader = reader

    def results(self, round_id: uuid.UUID) -> RoundResults:
        data = self._reader.load(round_id)
        if data is None:
            raise RoundNotFoundError(round_id)
        if data.summary.status is not RoundStatus.CLOSED:
            raise RoundStillOpenError(round_id)
        zones = [ZoneResult(zone, zone_agreement(_ranking(zone))) for zone in data.zones]
        # Una zona sin órdenes no tiene desacuerdos que comparar: queda fuera de la prueba.
        compared = [
            (result.zone.concentration, result.agreement)
            for result in zones
            if result.agreement is not None
        ]
        return RoundResults(
            round=data.summary,
            zones=zones,
            between=between_zones(compared),
            evaluator_numbers=data.evaluator_numbers,
        )

    def review_reports(self, round_id: uuid.UUID) -> tuple[RoundSummary, list[ReviewReport]]:
        return self._existing(round_id), self._reader.review_reports(round_id)

    def review_warnings(self, round_id: uuid.UUID) -> tuple[RoundSummary, list[ReviewWarning]]:
        return self._existing(round_id), self._reader.review_warnings(round_id)

    def _existing(self, round_id: uuid.UUID) -> RoundSummary:
        summary = self._reader.summary(round_id)
        if summary is None:
            raise RoundNotFoundError(round_id)
        return summary
