"""Caso de uso: guardar nuevos pesos y recalcular los reportes activos (guía 4.5)."""

import logging
import uuid
from dataclasses import dataclass

from app.modules.priority.application.evaluate_report import ReportEvaluator
from app.modules.priority.domain.entities import WeightVersion
from app.modules.priority.domain.ports import ReportsToEvaluate, WeightVersionRepository
from app.modules.priority.domain.weights import Weights
from app.shared.application.transaction import TransactionManager

logger = logging.getLogger(__name__)


class StaleWeightsVersionError(Exception):
    """La versión sobre la que se editó ya no es la vigente: otro administrador guardó antes."""

    def __init__(self, current_id: int | None) -> None:
        super().__init__(f"La versión vigente de los pesos es {current_id}")
        self.current_id = current_id


@dataclass(frozen=True, slots=True)
class WeightsUpdateResult:
    version: WeightVersion
    recalculated_reports: int


class UpdateWeights:
    """Crea una versión de pesos vigente y reevalúa con ella los reportes activos.

    Todo ocurre en una transacción: si un recálculo falla, la versión anterior
    sigue vigente y ninguna evaluación cambia. La versión vigente se bloquea al empezar:
    si no es ``base_version_id`` (la que el administrador estaba editando), se rechaza el
    cambio en vez de pisar el de otro administrador.
    """

    def __init__(
        self,
        weights: WeightVersionRepository,
        reports: ReportsToEvaluate,
        evaluator: ReportEvaluator,
        transaction: TransactionManager,
    ) -> None:
        self._weights = weights
        self._reports = reports
        self._evaluator = evaluator
        self._transaction = transaction

    def execute(
        self, weights: Weights, admin_id: uuid.UUID, base_version_id: int
    ) -> WeightsUpdateResult:
        try:
            current = self._weights.lock_current()
            if current is None or current.id != base_version_id:
                raise StaleWeightsVersionError(None if current is None else current.id)
            version = self._weights.add_current(weights, created_by=admin_id)
            active = self._reports.list_active()
            for report in active:
                self._evaluator.evaluate_with(report, version)
            self._transaction.commit()
        except Exception:
            self._transaction.rollback()
            raise
        logger.info(
            "Pesos actualizados a la versión %d; %d reportes recalculados", version.id, len(active)
        )
        return WeightsUpdateResult(version=version, recalculated_reports=len(active))
