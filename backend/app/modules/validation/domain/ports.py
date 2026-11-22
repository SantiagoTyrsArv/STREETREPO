"""Puertos del módulo de validación (objetivo 4)."""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Protocol

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
