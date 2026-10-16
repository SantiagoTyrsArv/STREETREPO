from collections.abc import Sequence
from itertools import batched
from typing import cast

from sqlalchemy import Table, func
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.core.db_types import SRID_WGS84
from app.modules.roads.domain.entities import OsmRoad
from app.modules.roads.infrastructure.models import RoadModel
from app.shared.infrastructure.wkt import linestring_wkt

_BATCH_SIZE = 500


class SqlRoadRepository:
    """Implementa ``RoadRepository`` con upsert de PostgreSQL por ``osm_id``."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def upsert_many(self, roads: Sequence[OsmRoad]) -> int:
        # ON CONFLICT no admite el mismo osm_id dos veces en una sentencia; gana el último.
        unique = list({item.osm_id: item for item in roads}.values())
        table = cast(Table, RoadModel.__table__)
        for batch in batched(unique, _BATCH_SIZE, strict=False):
            statement = insert(table).values(
                [
                    {
                        "osm_id": road.osm_id,
                        "nombre": road.name,
                        "highway_osm": road.highway_tag,
                        "jerarquia_vial": road.road_class,
                        "factor_flujo": road.flow_factor,
                        "geom": func.ST_GeomFromText(linestring_wkt(road.points), SRID_WGS84),
                    }
                    for road in batch
                ]
            )
            excluded = statement.excluded
            self._session.execute(
                statement.on_conflict_do_update(
                    index_elements=[table.c.osm_id],
                    set_={
                        "nombre": excluded.nombre,
                        "highway_osm": excluded.highway_osm,
                        "jerarquia_vial": excluded.jerarquia_vial,
                        "factor_flujo": excluded.factor_flujo,
                        "geom": excluded.geom,
                    },
                )
            )
        return len(unique)
