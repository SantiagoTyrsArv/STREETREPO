"""Casos de uso de la pantalla «Pesos del modelo» (HU-14).

Guardar delega en ``UpdateWeights`` del módulo de priorización (versión nueva vigente,
recálculo de los activos y 409 si otro administrador guardó antes); aquí solo se leen
las versiones con el nombre de su autor.
"""

import uuid
from collections.abc import Sequence
from dataclasses import dataclass

from app.modules.admin.domain.ports import WeightVersionsReader
from app.modules.admin.domain.ranking_view import MAX_PAGE_SIZE
from app.modules.admin.domain.weights_view import WeightVersionView
from app.modules.priority.application.evaluate_report import WeightsNotConfiguredError
from app.modules.priority.application.update_weights import UpdateWeights
from app.modules.priority.domain.weights import Weights


@dataclass(frozen=True, slots=True)
class SavedWeights:
    version: WeightVersionView
    recalculated_reports: int


class ManageWeights:
    def __init__(self, reader: WeightVersionsReader, update: UpdateWeights) -> None:
        self._reader = reader
        self._update = update

    def current(self) -> WeightVersionView:
        version = self._reader.current()
        if version is None:
            raise WeightsNotConfiguredError("No hay una versión de pesos vigente")
        return version

    def versions(self, limit: int, offset: int) -> Sequence[WeightVersionView]:
        if not 1 <= limit <= MAX_PAGE_SIZE:
            raise ValueError(f"limit debe estar entre 1 y {MAX_PAGE_SIZE}")
        if offset < 0:
            raise ValueError("offset no puede ser negativo")
        return self._reader.list_versions(limit, offset)

    def save(self, weights: Weights, admin_id: uuid.UUID, base_version_id: int) -> SavedWeights:
        """Lanza ``StaleWeightsVersionError`` si ``base_version_id`` ya no es la vigente."""
        result = self._update.execute(weights, admin_id, base_version_id)
        return SavedWeights(
            version=self.current(), recalculated_reports=result.recalculated_reports
        )
