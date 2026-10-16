from decimal import Decimal

import pytest

from app.modules.roads.domain.classification import (
    SUPPORTED_HIGHWAY_TAGS,
    classify_highway,
    flow_factor,
)
from app.modules.roads.domain.road_class import RoadClass


@pytest.mark.parametrize(
    ("tag", "expected"),
    [
        ("trunk", RoadClass.PRIMARY),
        ("trunk_link", RoadClass.PRIMARY),
        ("primary", RoadClass.PRIMARY),
        ("primary_link", RoadClass.PRIMARY),
        ("secondary", RoadClass.SECONDARY),
        ("tertiary", RoadClass.TERTIARY),
        ("residential", RoadClass.RESIDENTIAL),
        ("unclassified", RoadClass.RESIDENTIAL),
        ("service", RoadClass.RESIDENTIAL),
        ("living_street", RoadClass.RESIDENTIAL),
    ],
)
def test_supported_highway_tags_are_classified(tag: str, expected: RoadClass) -> None:
    assert classify_highway(tag) is expected


@pytest.mark.parametrize("tag", ["footway", "path", "track", "steps", "cycleway", "motorway", ""])
def test_unsupported_highway_tags_are_not_loaded(tag: str) -> None:
    assert classify_highway(tag) is None


def test_classification_ignores_case_and_spaces() -> None:
    assert classify_highway(" Primary ") is RoadClass.PRIMARY


@pytest.mark.parametrize(
    ("road_class", "expected"),
    [
        (RoadClass.PRIMARY, Decimal("10")),
        (RoadClass.SECONDARY, Decimal("7")),
        (RoadClass.TERTIARY, Decimal("5")),
        (RoadClass.RESIDENTIAL, Decimal("2")),
    ],
)
def test_flow_factor_follows_guide_normalization(road_class: RoadClass, expected: Decimal) -> None:
    assert flow_factor(road_class) == expected


def test_every_road_class_has_a_flow_factor() -> None:
    assert all(flow_factor(road_class) for road_class in RoadClass)


def test_trunk_roads_get_maximum_flow() -> None:
    # Motivo de la propuesta 7: las troncales (p. ej. la Panamericana) no deben quedar con F = 2.
    trunk_class = classify_highway("trunk")

    assert trunk_class is not None
    assert flow_factor(trunk_class) == Decimal("10")


def test_supported_tags_match_the_mapping() -> None:
    assert len(SUPPORTED_HIGHWAY_TAGS) == 10
