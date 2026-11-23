"""Puertos del módulo de validación (objetivo 4)."""

import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Protocol

from app.modules.validation.domain.blind import (
    BlindCard,
    BlindZone,
    EvaluatorZone,
    OpenRoundRef,
)
from app.modules.validation.domain.results import ReviewReport, ReviewWarning, RoundData
from app.modules.validation.domain.rounds import (
    RoundCandidate,
    RoundEntry,
    RoundProgress,
    RoundStatus,
    RoundSummary,
)
from app.modules.validation.domain.zones import Concentration, ZoneDefinition


@dataclass(frozen=True, slots=True)
class ZoneSummary:
    id: int
    name: str
    concentration: Concentration
    active_reports: int
    total_reports: int
    geometry_geojson: dict[str, Any]


class ZoneRepository(Protocol):
    def upsert(self, zones: Sequence[ZoneDefinition]) -> None:
        """Crea o actualiza (por nombre) las zonas; no confirma.

        Lanza ``InvalidZonesError`` si una geometría no es válida o dos zonas se solapan.
        Las zonas que ya están en la base y no vienen en ``zones`` no se tocan.
        """
        ...

    def assign_reports(self) -> int:
        """Recalcula la zona de todos los reportes; devuelve cuántos quedaron con zona."""
        ...

    def list_with_counts(self) -> list[ZoneSummary]: ...


class RoundRepository(Protocol):
    def has_open(self) -> bool: ...

    def list_candidates(self) -> list[RoundCandidate]:
        """Reportes activos con U guardada dentro de una zona (los elegibles para la muestra)."""
        ...

    def add(
        self,
        name: str,
        *,
        sample_size: int,
        seed: int,
        config_id: int,
        admin_id: uuid.UUID,
        entries: Sequence[RoundEntry],
    ) -> uuid.UUID:
        """Guarda la ronda abierta y sus reportes congelados; no confirma.

        Lanza ``RoundAlreadyOpenError`` si otra transacción abrió una ronda entre tanto.
        """
        ...

    def lock_status(self, round_id: uuid.UUID) -> RoundStatus | None:
        """Estado de la ronda bloqueada hasta el fin de la transacción; ``None`` si no existe."""
        ...

    def mark_closed(self, round_id: uuid.UUID) -> None: ...

    def get_progress(self, round_id: uuid.UUID) -> RoundProgress | None: ...

    def list_rounds(self, limit: int, offset: int) -> list[RoundSummary]:
        """Rondas de la más reciente a la más antigua."""
        ...


class BlindEvaluationRepository(Protocol):
    """Lecturas y escrituras de la evaluación a ciegas. Ninguna lectura devuelve datos del
    motor (U, factores, orden del motor) ni de otros evaluadores."""

    def find_open_round(self, *, lock: bool = False) -> OpenRoundRef | None:
        """La ronda abierta; con ``lock`` la fila queda bloqueada (compartida) hasta el fin
        de la transacción, para que no se cierre mientras se guarda un orden."""
        ...

    def list_zones(self, round_id: uuid.UUID, evaluator_id: uuid.UUID) -> list[EvaluatorZone]:
        """Zonas de la ronda por nombre, con sus reportes y si el evaluador ya envió."""
        ...

    def get_zone(self, round_id: uuid.UUID, zone_id: int) -> BlindZone | None:
        """La zona si forma parte de la ronda; ``None`` si no."""
        ...

    def zone_report_ids(self, round_id: uuid.UUID, zone_id: int) -> list[uuid.UUID]: ...

    def zone_cards(self, round_id: uuid.UUID, zone_id: int) -> list[BlindCard]:
        """Tarjetas de la zona con los servicios críticos a ``PROXIMITY_MAX_RADIUS_M``."""
        ...

    def has_submitted(self, round_id: uuid.UUID, evaluator_id: uuid.UUID, zone_id: int) -> bool: ...

    def save_order(
        self, round_id: uuid.UUID, evaluator_id: uuid.UUID, report_ids: Sequence[uuid.UUID]
    ) -> None:
        """Guarda las posiciones 1..n en el orden dado; no confirma.

        Lanza ``OrderAlreadySubmittedError`` si otra petición guardó el mismo orden antes.
        """
        ...

    def photo_key(self, round_id: uuid.UUID, report_id: uuid.UUID) -> str | None:
        """Clave de la foto más reciente si el reporte está en la ronda; ``None`` si no
        está o no tiene foto."""
        ...


class RoundResultsReader(Protocol):
    """Lecturas para los resultados y la ficha comparativa; solo las usa el administrador."""

    def summary(self, round_id: uuid.UUID) -> RoundSummary | None: ...

    def load(self, round_id: uuid.UUID) -> RoundData | None:
        """Reportes congelados por zona, órdenes de los evaluadores y deduplicación."""
        ...

    def review_reports(self, round_id: uuid.UUID) -> list[ReviewReport]:
        """Todos los reportes de las zonas de la ronda, para la revisión manual."""
        ...

    def review_warnings(self, round_id: uuid.UUID) -> list[ReviewWarning]:
        """Los avisos de duplicado mostrados en las zonas de la ronda, con sus candidatos."""
        ...
