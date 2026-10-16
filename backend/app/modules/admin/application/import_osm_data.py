"""Caso de uso: cargar vías y servicios críticos de OSM a PostGIS (HU-13, guía 3.1)."""

import logging
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

from app.modules.critical_services.domain.entities import OsmCriticalService
from app.modules.critical_services.domain.ports import CriticalServiceRepository
from app.modules.roads.domain.entities import OsmRoad
from app.modules.roads.domain.ports import RoadRepository
from app.shared.domain.geo import BoundingBox

logger = logging.getLogger(__name__)


class OsmSourceError(Exception):
    """La fuente de datos OSM no respondió o devolvió datos inválidos."""


class OsmDataSource(Protocol):
    def fetch_roads(self, area: BoundingBox) -> Sequence[OsmRoad]: ...

    def fetch_critical_services(self, area: BoundingBox) -> Sequence[OsmCriticalService]: ...


class TransactionManager(Protocol):
    def commit(self) -> None: ...

    def rollback(self) -> None: ...


@dataclass(frozen=True, slots=True)
class OsmImportResult:
    roads: int
    critical_services: int


class ImportOsmData:
    """Descarga los datos una sola vez y los guarda en una transacción.

    Es idempotente: se puede repetir y actualiza por ``osm_id`` sin duplicar.
    Si algo falla, no se guarda nada (todo o nada).
    """

    def __init__(
        self,
        source: OsmDataSource,
        roads: RoadRepository,
        critical_services: CriticalServiceRepository,
        transaction: TransactionManager,
    ) -> None:
        self._source = source
        self._roads = roads
        self._critical_services = critical_services
        self._transaction = transaction

    def execute(self, area: BoundingBox) -> OsmImportResult:
        # Descargar todo antes de escribir: un fallo de red no deja la base a medias.
        roads = self._source.fetch_roads(area)
        services = self._source.fetch_critical_services(area)
        try:
            result = OsmImportResult(
                roads=self._roads.upsert_many(roads),
                critical_services=self._critical_services.upsert_many(services),
            )
            self._transaction.commit()
        except Exception:
            self._transaction.rollback()
            raise
        logger.info(
            "Carga OSM completada: %d vías, %d servicios críticos",
            result.roads,
            result.critical_services,
        )
        return result
