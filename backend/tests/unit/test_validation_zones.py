"""Lectura del GeoJSON de zonas y caso de uso ImportZones (objetivo 4)."""

from collections.abc import Sequence
from typing import Any

import pytest

from app.modules.validation.application.import_zones import ImportZones
from app.modules.validation.domain.ports import ZoneSummary
from app.modules.validation.domain.zones import (
    Concentration,
    InvalidZonesError,
    ZoneDefinition,
    parse_zones,
)

SQUARE = [[[0, 0], [0, 1], [1, 1], [1, 0], [0, 0]]]


def _feature(name: object = "Centro", concentration: object = "alta", **geometry: Any) -> dict:
    properties: dict[str, object] = {}
    if name is not None:
        properties["name"] = name
    if concentration is not None:
        properties["concentration"] = concentration
    return {
        "type": "Feature",
        "properties": properties,
        "geometry": geometry or {"type": "Polygon", "coordinates": SQUARE},
    }


def _collection(*features: dict) -> dict:
    return {"type": "FeatureCollection", "features": list(features)}


def test_parse_two_polygons() -> None:
    zones = parse_zones(_collection(_feature("Centro", "alta"), _feature("Obonuco", "baja")))

    assert [(z.name, z.concentration) for z in zones] == [
        ("Centro", Concentration.HIGH),
        ("Obonuco", Concentration.LOW),
    ]
    assert zones[0].polygon_geojson == {"type": "Polygon", "coordinates": SQUARE}


def test_parse_trims_the_name() -> None:
    (zone,) = parse_zones(_collection(_feature("  Centro  ")))

    assert zone.name == "Centro"


@pytest.mark.parametrize(
    ("geojson", "fragment"),
    [
        ({"type": "Feature"}, "FeatureCollection"),
        ("no es un objeto", "FeatureCollection"),
        (_collection(), "al menos"),
        (_collection(*[_feature(f"Z{i}") for i in range(4)]), "3"),
        (_collection(_feature("Centro"), _feature("Centro")), "Centro"),
        (_collection(_feature(None)), "nombre"),
        (_collection(_feature("  ")), "nombre"),
        (_collection(_feature("Centro", "media")), "Centro"),
        (_collection(_feature("Centro", None)), "Centro"),
        (
            _collection(_feature("Centro", type="MultiPolygon", coordinates=[SQUARE])),
            "Centro",
        ),
        (_collection(_feature("Centro", type="Polygon", coordinates="x")), "Centro"),
        (_collection({"type": "Feature", "properties": {"name": "Centro"}}), "Centro"),
        (_collection("no es una feature"), "zona"),  # type: ignore[arg-type]
    ],
)
def test_parse_rejects_invalid_collections(geojson: Any, fragment: str) -> None:
    with pytest.raises(InvalidZonesError) as error:
        parse_zones(geojson)

    assert fragment in str(error.value)


class _FakeRepository:
    def __init__(self, fail: Exception | None = None) -> None:
        self.fail = fail
        self.upserted: Sequence[ZoneDefinition] = ()
        self.events: list[str] = []

    def upsert(self, zones: Sequence[ZoneDefinition]) -> None:
        self.events.append("upsert")
        if self.fail:
            raise self.fail
        self.upserted = zones

    def assign_reports(self) -> int:
        self.events.append("assign")
        return 7

    def list_with_counts(self) -> list[ZoneSummary]:
        return []


class _FakeTransaction:
    def __init__(self, events: list[str]) -> None:
        self.events = events

    def commit(self) -> None:
        self.events.append("commit")

    def rollback(self) -> None:
        self.events.append("rollback")


def test_import_zones_upserts_assigns_and_commits_once() -> None:
    repository = _FakeRepository()
    result = ImportZones(repository, _FakeTransaction(repository.events)).execute(
        _collection(_feature("Centro"), _feature("Obonuco", "baja"))
    )

    assert (result.zones, result.reports_assigned) == (2, 7)
    assert repository.events == ["upsert", "assign", "commit"]


def test_import_zones_rolls_back_when_the_repository_rejects_the_zones() -> None:
    repository = _FakeRepository(fail=InvalidZonesError("La zona «Centro» se solapa"))
    use_case = ImportZones(repository, _FakeTransaction(repository.events))

    with pytest.raises(InvalidZonesError):
        use_case.execute(_collection(_feature("Centro")))

    assert repository.events == ["upsert", "rollback"]


def test_import_zones_does_not_touch_the_database_with_a_bad_file() -> None:
    repository = _FakeRepository()

    with pytest.raises(InvalidZonesError):
        ImportZones(repository, _FakeTransaction(repository.events)).execute(_collection())

    assert repository.events == []
