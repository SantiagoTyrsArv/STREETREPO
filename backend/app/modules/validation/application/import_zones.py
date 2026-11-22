"""Casos de uso de zonas de validación (objetivo 4)."""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from app.modules.validation.domain.ports import ZoneRepository, ZoneSummary
from app.modules.validation.domain.zones import parse_zones
from app.shared.application.transaction import TransactionManager


@dataclass(frozen=True, slots=True)
class ImportZonesResult:
    zones: int
    reports_assigned: int


class ImportZones:
    """Carga las zonas del piloto y asigna su zona a los reportes, en una sola transacción."""

    def __init__(self, zones: ZoneRepository, transaction: TransactionManager) -> None:
        self._zones = zones
        self._transaction = transaction

    def execute(self, geojson: Mapping[str, Any]) -> ImportZonesResult:
        definitions = parse_zones(geojson)
        try:
            self._zones.upsert(definitions)
            assigned = self._zones.assign_reports()
            self._transaction.commit()
        except BaseException:
            self._transaction.rollback()
            raise
        return ImportZonesResult(zones=len(definitions), reports_assigned=assigned)


class ListZones:
    def __init__(self, zones: ZoneRepository) -> None:
        self._zones = zones

    def execute(self) -> list[ZoneSummary]:
        return self._zones.list_with_counts()
