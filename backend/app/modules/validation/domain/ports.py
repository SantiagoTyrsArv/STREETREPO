"""Puertos del módulo de validación (objetivo 4)."""

import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Protocol

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
