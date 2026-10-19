import uuid

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.db_types import SRID_WGS84
from app.modules.reports.domain.entities import ReportDetails
from app.modules.reports.domain.new_report import NewReport
from app.modules.reports.domain.photos import StoredEvidence
from app.modules.reports.domain.ports import DuplicateIdempotencyKeyError
from app.modules.reports.domain.severity import Severity
from app.modules.reports.domain.status import ReportStatus
from app.modules.reports.infrastructure.models import EvidenceModel, ReportModel
from app.modules.roads.infrastructure.models import RoadModel
from app.shared.domain.geo import GeoPoint
from app.shared.infrastructure.wkt import point_wkt

IDEMPOTENCY_CONSTRAINT = "uq_reporte_usuario_clave_idempotencia"


def _violated_constraint(exc: IntegrityError) -> str | None:
    diag = getattr(exc.orig, "diag", None)
    name = getattr(diag, "constraint_name", None)
    return name if isinstance(name, str) else None


class SqlReportRepository:
    """Implementa ``ReportRepository``. No confirma: lo hace el caso de uso."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def find_by_idempotency_key(self, user_id: uuid.UUID, key: uuid.UUID) -> uuid.UUID | None:
        return self._session.execute(
            select(ReportModel.id).where(
                ReportModel.user_id == user_id, ReportModel.idempotency_key == key
            )
        ).scalar_one_or_none()

    def add(self, report: NewReport) -> uuid.UUID:
        model = ReportModel(
            user_id=report.user_id,
            location=func.ST_GeomFromText(point_wkt(report.location), SRID_WGS84),
            severity=int(report.severity),
            description=report.description,
            status=ReportStatus.REGISTERED,
            idempotency_key=report.idempotency_key,
        )
        self._session.add(model)
        try:
            self._session.flush()
        except IntegrityError as exc:
            if _violated_constraint(exc) == IDEMPOTENCY_CONSTRAINT:
                raise DuplicateIdempotencyKeyError(str(report.idempotency_key)) from exc
            raise
        return model.id

    def add_evidence(self, report_id: uuid.UUID, evidence: StoredEvidence) -> None:
        self._session.add(
            EvidenceModel(
                report_id=report_id,
                photo_url=evidence.photo_key,
                file_format=evidence.file_format,
                size_bytes=evidence.size_bytes,
            )
        )
        self._session.flush()

    def get_details(self, report_id: uuid.UUID) -> ReportDetails | None:
        row = self._session.execute(
            select(
                ReportModel.id,
                ReportModel.user_id,
                func.ST_X(ReportModel.location).label("lon"),
                func.ST_Y(ReportModel.location).label("lat"),
                ReportModel.severity,
                ReportModel.description,
                ReportModel.status,
                ReportModel.priority_score,
                ReportModel.road_id,
                RoadModel.name.label("road_name"),
                ReportModel.created_at,
            )
            .outerjoin(RoadModel, RoadModel.id == ReportModel.road_id)
            .where(ReportModel.id == report_id)
        ).one_or_none()
        if row is None:
            return None
        return ReportDetails(
            id=row.id,
            user_id=row.user_id,
            location=GeoPoint(longitude=row.lon, latitude=row.lat),
            severity=Severity(row.severity),
            description=row.description,
            status=ReportStatus(row.status),
            priority_score=row.priority_score,
            road_id=row.road_id,
            road_name=row.road_name,
            created_at=row.created_at,
        )
