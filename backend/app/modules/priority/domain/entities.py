import uuid
from dataclasses import dataclass
from datetime import datetime

from app.modules.priority.domain.weights import Weights
from app.modules.reports.domain.severity import Severity
from app.modules.reports.domain.status import ReportStatus
from app.shared.domain.geo import GeoPoint


@dataclass(frozen=True, slots=True)
class WeightVersion:
    """Versión guardada de los pesos. Las versiones no se editan: cada cambio crea una."""

    id: int
    weights: Weights
    # None = configuración inicial cargada por el sistema.
    created_by: uuid.UUID | None
    created_at: datetime
    is_current: bool


@dataclass(frozen=True, slots=True)
class ReportToEvaluate:
    """Datos de un reporte que el motor necesita para calcular su urgencia."""

    report_id: uuid.UUID
    severity: Severity
    location: GeoPoint
    status: ReportStatus
