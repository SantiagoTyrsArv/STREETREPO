"""Motor de priorización: calcula, guarda la evaluación y marca el reporte como evaluado."""

import uuid

from app.modules.critical_services.domain.ports import CriticalServiceLocator
from app.modules.priority.domain.entities import ReportToEvaluate, WeightVersion
from app.modules.priority.domain.ports import (
    EvaluationRepository,
    ReportsToEvaluate,
    WeightVersionRepository,
)
from app.modules.priority.domain.urgency import EvaluationInput, PriorityModel, UrgencyEvaluation
from app.modules.reports.domain.ports import StatusHistoryRecorder
from app.modules.reports.domain.status import ReportStatus
from app.modules.reports.domain.status_machine import change_status
from app.modules.roads.domain.ports import RoadMatcher
from app.shared.domain.geo_parameters import PROXIMITY_MAX_RADIUS_M, ROAD_MATCHING_RADIUS_M


class WeightsNotConfiguredError(Exception):
    """No hay una versión de pesos vigente (la migración 0005 carga la inicial)."""


class ReportNotFoundError(Exception):
    """El reporte a evaluar no existe."""


class ReportEvaluator:
    """Evalúa reportes con PostGIS local (sin Overpass en tiempo de ejecución, guía 3.1).

    No confirma la transacción: la abre y la cierra el caso de uso que lo llama,
    para que crear un reporte o recalcular prioridades sea todo o nada.
    """

    def __init__(
        self,
        *,
        reports: ReportsToEvaluate,
        weights: WeightVersionRepository,
        evaluations: EvaluationRepository,
        statuses: StatusHistoryRecorder,
        road_matcher: RoadMatcher,
        service_locator: CriticalServiceLocator,
    ) -> None:
        self._reports = reports
        self._weights = weights
        self._evaluations = evaluations
        self._statuses = statuses
        self._road_matcher = road_matcher
        self._service_locator = service_locator

    def current_version(self) -> WeightVersion:
        version = self._weights.get_current()
        if version is None:
            raise WeightsNotConfiguredError("No hay pesos vigentes para el modelo de prioridad")
        return version

    def evaluate(self, report_id: uuid.UUID) -> UrgencyEvaluation:
        """Evalúa un reporte con los pesos vigentes."""
        report = self._reports.get(report_id)
        if report is None:
            raise ReportNotFoundError(f"No existe el reporte {report_id}")
        return self.evaluate_with(report, self.current_version())

    def evaluate_with(self, report: ReportToEvaluate, version: WeightVersion) -> UrgencyEvaluation:
        """Evalúa un reporte con una versión de pesos dada (recálculo masivo)."""
        data = EvaluationInput(
            severity=report.severity,
            road=self._road_matcher.find_nearest(report.location, ROAD_MATCHING_RADIUS_M),
            nearest_service=self._service_locator.find_nearest(
                report.location, PROXIMITY_MAX_RADIUS_M
            ),
        )
        evaluation = PriorityModel(version.weights).evaluate(data)
        self._evaluations.add(report.report_id, evaluation, version.id)
        # Registrado -> Evaluado ocurre por el cálculo automático (guía 2.4); en los
        # recálculos el reporte conserva su estado.
        if report.status is ReportStatus.REGISTERED:
            self._statuses.apply(
                report.report_id,
                change_status(report.status, ReportStatus.EVALUATED, changed_by=None),
            )
        return evaluation
