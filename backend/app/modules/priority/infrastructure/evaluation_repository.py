import uuid

from sqlalchemy import update
from sqlalchemy.orm import Session

from app.modules.priority.domain.urgency import UrgencyEvaluation
from app.modules.priority.infrastructure.models import PriorityEvaluationModel
from app.modules.reports.infrastructure.models import ReportModel


class SqlEvaluationRepository:
    """Implementa ``EvaluationRepository``.

    Cada cálculo es una fila nueva de ``evaluacion_prioridad`` (historial
    reproducible, guía 4.5). El reporte guarda una copia de la U vigente para
    ordenar el ranking sin JOIN y la vía asociada (NULL = "Revisar vía").
    """

    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, report_id: uuid.UUID, evaluation: UrgencyEvaluation, config_id: int) -> None:
        self._session.add(
            PriorityEvaluationModel(
                report_id=report_id,
                config_id=config_id,
                service_id=evaluation.service_id,
                service_distance_m=evaluation.service_distance_m,
                severity_score=evaluation.severity_score,
                flow_score=evaluation.flow_score,
                proximity_score=evaluation.proximity_score,
                urgency_score=evaluation.urgency_score,
            )
        )
        self._session.execute(
            update(ReportModel)
            .where(ReportModel.id == report_id)
            .values(priority_score=evaluation.urgency_score, road_id=evaluation.road_id)
        )
        self._session.flush()
