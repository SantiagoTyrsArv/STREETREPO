from collections.abc import Sequence
from itertools import batched
from typing import cast

from sqlalchemy import Table, func
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.core.db_types import SRID_WGS84
from app.modules.critical_services.domain.entities import OsmCriticalService
from app.modules.critical_services.infrastructure.models import CriticalServiceModel
from app.shared.infrastructure.wkt import point_wkt

_BATCH_SIZE = 500


class SqlCriticalServiceRepository:
    """Implementa ``CriticalServiceRepository`` con upsert de PostgreSQL por ``osm_id``."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def upsert_many(self, services: Sequence[OsmCriticalService]) -> int:
        # ON CONFLICT no admite el mismo osm_id dos veces en una sentencia; gana el último.
        unique = list({item.osm_id: item for item in services}.values())
        table = cast(Table, CriticalServiceModel.__table__)
        for batch in batched(unique, _BATCH_SIZE, strict=False):
            statement = insert(table).values(
                [
                    {
                        "osm_id": service.osm_id,
                        "nombre": service.name,
                        "tipo": service.service_type,
                        "ubicacion": func.ST_GeomFromText(point_wkt(service.location), SRID_WGS84),
                    }
                    for service in batch
                ]
            )
            excluded = statement.excluded
            self._session.execute(
                statement.on_conflict_do_update(
                    index_elements=[table.c.osm_id],
                    set_={
                        "nombre": excluded.nombre,
                        "tipo": excluded.tipo,
                        "ubicacion": excluded.ubicacion,
                    },
                )
            )
        return len(unique)
