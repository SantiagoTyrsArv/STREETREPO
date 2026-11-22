import uuid
from dataclasses import dataclass
from typing import Protocol

from app.modules.reports.domain.status import ReportStatus
from app.shared.domain.geo import GeoPoint


@dataclass(frozen=True, slots=True)
class ConfirmationTarget:
    """Lo que hace falta saber del reporte para decidir si se puede confirmar."""

    owner_id: uuid.UUID
    status: ReportStatus
    # Distancia en metros, redondeada a centímetros, entre el punto de quien confirma y la
    # ubicación exacta del reporte.
    distance_m: float


class ConfirmationRepository(Protocol):
    def find_target(
        self, report_id: uuid.UUID, location: GeoPoint
    ) -> ConfirmationTarget | None: ...

    def add(self, report_id: uuid.UUID, user_id: uuid.UUID, distance_m: float) -> None:
        """Guarda la confirmación; lanza ``AlreadyConfirmedError`` si ya existía.

        La restricción única de la tabla decide, no una consulta previa: así un doble
        toque simultáneo tampoco crea dos filas.
        """
        ...

    def count(self, report_id: uuid.UUID) -> int: ...
