"""Versiones de pesos con el nombre de quien las guardó."""

from collections.abc import Sequence
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.modules.admin.domain.weights_view import WeightVersionView
from app.modules.priority.domain.weights import Weights

_CURRENT = text(
    """
    SELECT c.id_config, c.w_severidad, c.w_flujo, c.w_proximidad, c.vigente,
           c.fecha_creacion, u.nombre AS nombre_usuario
    FROM configuracion_pesos AS c
    LEFT JOIN usuario AS u ON u.id_usuario = c.id_usuario
    WHERE c.vigente
    """
)

# Mismo orden que SqlWeightVersionRepository.list_versions.
_PAGE = text(
    """
    SELECT c.id_config, c.w_severidad, c.w_flujo, c.w_proximidad, c.vigente,
           c.fecha_creacion, u.nombre AS nombre_usuario
    FROM configuracion_pesos AS c
    LEFT JOIN usuario AS u ON u.id_usuario = c.id_usuario
    ORDER BY c.fecha_creacion DESC, c.id_config DESC
    LIMIT :limite OFFSET :desplazamiento
    """
)


class SqlWeightVersionsReader:
    """Implementa ``WeightVersionsReader``."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def current(self) -> WeightVersionView | None:
        row = self._session.execute(_CURRENT).one_or_none()
        return None if row is None else _view(row)

    def list_versions(self, limit: int, offset: int) -> Sequence[WeightVersionView]:
        rows = self._session.execute(_PAGE, {"limite": limit, "desplazamiento": offset}).all()
        return [_view(row) for row in rows]


def _view(row: Any) -> WeightVersionView:
    return WeightVersionView(
        id=row.id_config,
        weights=Weights(row.w_severidad, row.w_flujo, row.w_proximidad),
        created_at=row.fecha_creacion,
        created_by_name=row.nombre_usuario,
        is_current=row.vigente,
    )
