import uuid
from decimal import Decimal

from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modules.confirmations.domain.errors import AlreadyConfirmedError
from app.modules.confirmations.domain.ports import ConfirmationTarget
from app.modules.confirmations.infrastructure.models import ConfirmationModel
from app.modules.reports.domain.status import ReportStatus
from app.shared.domain.geo import GeoPoint

UNIQUE_CONFIRMATION_CONSTRAINT = "uq_confirmacion_reporte_usuario"

# Distancia a la ubicación exacta del reporte (no a la pública redondeada), en centímetros
# como el resto de distancias guardadas (guía 2.2).
_TARGET_SQL = text(
    """
    SELECT r.id_usuario,
           r.estado::text AS estado,
           ROUND(
               ST_Distance(
                   r.ubicacion::geography,
                   ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography
               )::numeric,
               2
           ) AS distancia_m
    FROM reporte r
    WHERE r.id_reporte = :report_id
    """
)


def _violated_constraint(exc: IntegrityError) -> str | None:
    diag = getattr(exc.orig, "diag", None)
    name = getattr(diag, "constraint_name", None)
    return name if isinstance(name, str) else None


class SqlConfirmationRepository:
    """Implementa ``ConfirmationRepository``. No confirma: lo hace el caso de uso."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def find_target(self, report_id: uuid.UUID, location: GeoPoint) -> ConfirmationTarget | None:
        row = self._session.execute(
            _TARGET_SQL,
            {"report_id": report_id, "lon": location.longitude, "lat": location.latitude},
        ).one_or_none()
        if row is None:
            return None
        return ConfirmationTarget(
            owner_id=row.id_usuario,
            status=ReportStatus(row.estado),
            distance_m=float(row.distancia_m),
        )

    def add(self, report_id: uuid.UUID, user_id: uuid.UUID, distance_m: float) -> None:
        self._session.add(
            ConfirmationModel(
                report_id=report_id, user_id=user_id, distance_m=Decimal(str(distance_m))
            )
        )
        try:
            self._session.flush()
        except IntegrityError as exc:
            if _violated_constraint(exc) == UNIQUE_CONFIRMATION_CONSTRAINT:
                raise AlreadyConfirmedError(str(report_id)) from exc
            raise

    def count(self, report_id: uuid.UUID) -> int:
        return self._session.execute(
            select(func.count()).where(ConfirmationModel.report_id == report_id)
        ).scalar_one()
