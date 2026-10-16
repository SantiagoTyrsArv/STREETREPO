import uuid
from collections.abc import Sequence
from typing import Protocol

from app.modules.priority.domain.entities import ReportToEvaluate, WeightVersion
from app.modules.priority.domain.urgency import UrgencyEvaluation
from app.modules.priority.domain.weights import Weights


class WeightVersionRepository(Protocol):
    def get_current(self) -> WeightVersion | None:
        """Versión vigente, o ``None`` si nunca se configuraron pesos."""
        ...

    def list_versions(self, limit: int, offset: int) -> Sequence[WeightVersion]:
        """Versiones de la más reciente a la más antigua."""
        ...

    def add_current(self, weights: Weights, created_by: uuid.UUID | None) -> WeightVersion:
        """Guarda una versión nueva como vigente y retira la vigencia de la anterior."""
        ...


class ReportsToEvaluate(Protocol):
    def get(self, report_id: uuid.UUID) -> ReportToEvaluate | None: ...

    def list_active(self) -> Sequence[ReportToEvaluate]:
        """Reportes que siguen abiertos (todo estado salvo reparado)."""
        ...


class EvaluationRepository(Protocol):
    def add(self, report_id: uuid.UUID, evaluation: UrgencyEvaluation, config_id: int) -> None:
        """Guarda la evaluación y actualiza en el reporte la U vigente y la vía asociada."""
        ...
