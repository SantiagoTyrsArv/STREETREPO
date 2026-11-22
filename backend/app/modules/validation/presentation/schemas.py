"""Esquemas HTTP del módulo de validación (objetivo 4)."""

from collections.abc import Sequence
from typing import Any

from pydantic import BaseModel, ConfigDict

from app.modules.validation.domain.ports import ZoneSummary
from app.modules.validation.domain.zones import Concentration


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
