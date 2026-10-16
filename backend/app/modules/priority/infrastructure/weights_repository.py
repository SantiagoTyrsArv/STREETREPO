import uuid
from collections.abc import Sequence

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.modules.priority.domain.entities import WeightVersion
from app.modules.priority.domain.weights import Weights
from app.modules.priority.infrastructure.models import WeightConfigModel


def _to_entity(row: WeightConfigModel) -> WeightVersion:
    return WeightVersion(
        id=row.id,
        weights=Weights(row.severity_weight, row.flow_weight, row.proximity_weight),
        created_by=row.user_id,
        created_at=row.created_at,
        is_current=row.is_current,
    )


class SqlWeightVersionRepository:
    """Implementa ``WeightVersionRepository`` sobre ``configuracion_pesos``."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_current(self) -> WeightVersion | None:
        row = self._session.scalars(
            select(WeightConfigModel).where(WeightConfigModel.is_current)
        ).one_or_none()
        return None if row is None else _to_entity(row)

    def list_versions(self, limit: int, offset: int) -> Sequence[WeightVersion]:
        rows = self._session.scalars(
            select(WeightConfigModel)
            .order_by(WeightConfigModel.created_at.desc(), WeightConfigModel.id.desc())
            .limit(limit)
            .offset(offset)
        )
        return [_to_entity(row) for row in rows]

    def add_current(self, weights: Weights, created_by: uuid.UUID | None) -> WeightVersion:
        # Primero se retira la vigencia: el índice único parcial admite una sola fila vigente.
        self._session.execute(
            update(WeightConfigModel).where(WeightConfigModel.is_current).values(is_current=False)
        )
        row = WeightConfigModel(
            user_id=created_by,
            severity_weight=weights.severity,
            flow_weight=weights.flow,
            proximity_weight=weights.proximity,
            is_current=True,
        )
        self._session.add(row)
        self._session.flush()
        # fecha_creacion la asigna la base (server_default).
        self._session.refresh(row)
        return _to_entity(row)
