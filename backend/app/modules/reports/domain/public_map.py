"""Mapa de reportes de la app ciudadana: reportes dentro del área visible (guía 6.2).

Lo ve cualquier ciudadano con sesión, así que cada reporte va con la vista pública: sin
autor, descripción, foto ni ubicación exacta (guía 7.2, propuesta 43).
"""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Final

from app.modules.reports.domain.my_reports import PublicReportView

# Tope de reportes por consulta; el mapa pide solo el área visible (guía 11).
MAX_MAP_REPORTS: Final = 200


@dataclass(frozen=True, slots=True)
class MapReport:
    public: PublicReportView
    # Del ciudadano que consulta: no puede confirmarlo (propuesta 48).
    is_mine: bool
    # Ya lo confirmó: no puede repetir la confirmación.
    confirmed_by_me: bool


@dataclass(frozen=True, slots=True)
class MapReportsPage:
    """Del más reciente al más antiguo. ``truncated`` avisa que el área tiene más reportes
    que el tope: el mapa pide acercarse."""

    items: Sequence[MapReport]
    limit: int
    truncated: bool
