"""Armado de los casos de uso del módulo de validación para cada petición."""

from typing import Annotated

from fastapi import Depends

from app.core.dependencies import SessionDep
from app.modules.priority.infrastructure.weights_repository import SqlWeightVersionRepository
from app.modules.validation.application.import_zones import ListZones
from app.modules.validation.application.manage_rounds import CloseRound, OpenRound, ReadRounds
from app.modules.validation.infrastructure.round_repository import SqlRoundRepository
from app.modules.validation.infrastructure.zone_repository import SqlZoneRepository


def get_list_zones(session: SessionDep) -> ListZones:
    return ListZones(SqlZoneRepository(session))


ListZonesDep = Annotated[ListZones, Depends(get_list_zones)]


def get_open_round(session: SessionDep) -> OpenRound:
    return OpenRound(
        SqlZoneRepository(session),
        SqlRoundRepository(session),
        SqlWeightVersionRepository(session),
        session,
    )


def get_close_round(session: SessionDep) -> CloseRound:
    return CloseRound(SqlRoundRepository(session), session)


def get_read_rounds(session: SessionDep) -> ReadRounds:
    return ReadRounds(SqlRoundRepository(session))


OpenRoundDep = Annotated[OpenRound, Depends(get_open_round)]
CloseRoundDep = Annotated[CloseRound, Depends(get_close_round)]
ReadRoundsDep = Annotated[ReadRounds, Depends(get_read_rounds)]
