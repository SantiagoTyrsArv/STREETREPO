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


@dataclass(frozen=True, slots=True)
class WeightsUpdateResult:
    version: WeightVersion
    recalculated_reports: int


class UpdateWeights:
    """Crea una versión de pesos vigente y reevalúa con ella los reportes activos.

    Todo ocurre en una transacción: si un recálculo falla, la versión anterior
    sigue vigente y ninguna evaluación cambia.
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

    def execute(self, weights: Weights, admin_id: uuid.UUID) -> WeightsUpdateResult:
        try:
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
