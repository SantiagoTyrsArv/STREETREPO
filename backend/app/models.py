"""Registro de todos los modelos ORM para que Alembic vea el esquema completo."""

from app.modules.auth.infrastructure.models import RefreshTokenModel
from app.modules.confirmations.infrastructure.models import ConfirmationModel
from app.modules.critical_services.infrastructure.models import CriticalServiceModel
from app.modules.priority.infrastructure.models import PriorityEvaluationModel, WeightConfigModel
from app.modules.reports.infrastructure.models import (
    EvidenceModel,
    ReportModel,
    StatusHistoryModel,
)
from app.modules.roads.infrastructure.models import RoadModel, ZoneModel
from app.modules.users.infrastructure.models import DataDeletionRequestModel, UserModel

__all__ = [
    "ConfirmationModel",
    "CriticalServiceModel",
    "DataDeletionRequestModel",
    "EvidenceModel",
    "PriorityEvaluationModel",
    "RefreshTokenModel",
    "ReportModel",
    "RoadModel",
    "StatusHistoryModel",
    "UserModel",
    "WeightConfigModel",
    "ZoneModel",
]
