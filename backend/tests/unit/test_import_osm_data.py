from collections.abc import Sequence
from decimal import Decimal

import pytest

from app.modules.admin.application.import_osm_data import (
    ImportOsmData,
    OsmImportResult,
    OsmSourceError,
)
from app.modules.critical_services.domain.entities import OsmCriticalService
from app.modules.critical_services.domain.service_type import CriticalServiceType
from app.modules.roads.domain.entities import OsmRoad
from app.modules.roads.domain.road_class import RoadClass
from app.shared.domain.geo import BoundingBox, GeoPoint

AREA = BoundingBox(south=1.16, west=-77.33, north=1.25, east=-77.23)
ROAD = OsmRoad(
    osm_id=1,
    name="Calle de prueba",
    highway_tag="residential",
    road_class=RoadClass.RESIDENTIAL,
    flow_factor=Decimal("2"),
    points=(GeoPoint(-77.28, 1.21), GeoPoint(-77.27, 1.22)),
)
SERVICE = OsmCriticalService(
    osm_id=2, name=None, service_type=CriticalServiceType.SCHOOL, location=GeoPoint(-77.28, 1.21)
)


class FakeSource:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.areas: list[BoundingBox] = []

    def fetch_roads(self, area: BoundingBox) -> Sequence[OsmRoad]:
        self.areas.append(area)
        if self.fail:
            raise OsmSourceError("caída")
        return [ROAD]

    def fetch_critical_services(self, area: BoundingBox) -> Sequence[OsmCriticalService]:
        self.areas.append(area)
        return [SERVICE]


class FakeRepository[T]:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.saved: list[T] = []

    def upsert_many(self, items: Sequence[T]) -> int:
        if self.fail:
            raise RuntimeError("fallo al escribir")
        self.saved.extend(items)
        return len(items)


class FakeTransaction:
    def __init__(self) -> None:
        self.committed = False
        self.rolled_back = False

    def commit(self) -> None:
        self.committed = True

    def rollback(self) -> None:
        self.rolled_back = True


def _use_case(
    source: FakeSource,
    roads: FakeRepository[OsmRoad],
    services: FakeRepository[OsmCriticalService],
    transaction: FakeTransaction,
) -> ImportOsmData:
    return ImportOsmData(source, roads, services, transaction)


def test_import_saves_everything_and_commits() -> None:
    source, roads, services, tx = (
        FakeSource(),
        FakeRepository[OsmRoad](),
        FakeRepository[OsmCriticalService](),
        FakeTransaction(),
    )

    result = _use_case(source, roads, services, tx).execute(AREA)

    assert result == OsmImportResult(roads=1, critical_services=1)
    assert roads.saved == [ROAD]
    assert services.saved == [SERVICE]
    assert source.areas == [AREA, AREA]
    assert tx.committed
    assert not tx.rolled_back


def test_source_failure_writes_nothing() -> None:
    roads, services, tx = (
        FakeRepository[OsmRoad](),
        FakeRepository[OsmCriticalService](),
        FakeTransaction(),
    )

    with pytest.raises(OsmSourceError):
        _use_case(FakeSource(fail=True), roads, services, tx).execute(AREA)

    assert roads.saved == []
    assert services.saved == []
    assert not tx.committed


def test_write_failure_rolls_back() -> None:
    tx = FakeTransaction()

    with pytest.raises(RuntimeError):
        _use_case(
            FakeSource(),
            FakeRepository[OsmRoad](),
            FakeRepository[OsmCriticalService](fail=True),
            tx,
        ).execute(AREA)

    assert tx.rolled_back
    assert not tx.committed
