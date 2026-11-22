"""Armado de los casos de uso del módulo de validación para cada petición."""

from typing import Annotated

from fastapi import Depends

from app.core.dependencies import SessionDep
from app.modules.validation.application.import_zones import ListZones
from app.modules.validation.infrastructure.zone_repository import SqlZoneRepository


def get_list_zones(session: SessionDep) -> ListZones:
    return ListZones(SqlZoneRepository(session))


ListZonesDep = Annotated[ListZones, Depends(get_list_zones)]
