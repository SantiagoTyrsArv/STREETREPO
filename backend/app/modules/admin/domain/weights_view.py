"""Versiones de pesos vistas desde el panel «Pesos del modelo» (HU-14)."""

from dataclasses import dataclass
from datetime import datetime

from app.modules.priority.domain.weights import Weights


@dataclass(frozen=True, slots=True)
class WeightVersionView:
    id: int
    weights: Weights
    created_at: datetime
    # None = configuración inicial cargada por el sistema (o cuenta suprimida).
    created_by_name: str | None
    is_current: bool
