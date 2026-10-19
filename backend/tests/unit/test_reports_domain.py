"""Reglas del reporte nuevo: área de servicio, descripción, dirección y claves de foto."""

import uuid
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from app.modules.reports.domain.address import NO_ROAD, UNNAMED_ROAD, display_address
from app.modules.reports.domain.entities import ReportDetails
from app.modules.reports.domain.new_report import (
    DESCRIPTION_MAX_LENGTH,
    InvalidReportError,
    LocationOutsideServiceAreaError,
    NewReport,
)
from app.modules.reports.domain.photos import PhotoKeys
from app.modules.reports.domain.severity import Severity
from app.modules.reports.domain.status import ReportStatus
from app.modules.reports.presentation.schemas import SeverityLevel
from app.shared.domain.geo import BoundingBox, GeoPoint

PASTO_AREA = BoundingBox.parse("1.16,-77.33,1.25,-77.23")
PASTO = GeoPoint(longitude=-77.2811, latitude=1.2136)
USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


def _create(location: GeoPoint = PASTO, description: str | None = None) -> NewReport:
    return NewReport.create(
        user_id=USER_ID,
        location=location,
        severity=Severity.HIGH,
        description=description,
        idempotency_key=None,
        service_area=PASTO_AREA,
    )


def test_new_report_inside_the_service_area() -> None:
    report = _create(description="  Hueco grande frente al colegio  ")

    assert report.location == PASTO
    assert report.description == "Hueco grande frente al colegio"


@pytest.mark.parametrize("description", [None, "", "   \n "])
def test_blank_description_is_stored_as_null(description: str | None) -> None:
    assert _create(description=description).description is None


def test_description_longer_than_the_limit_is_rejected() -> None:
    with pytest.raises(InvalidReportError, match=str(DESCRIPTION_MAX_LENGTH)):
        _create(description="a" * (DESCRIPTION_MAX_LENGTH + 1))


def test_description_at_the_limit_is_accepted() -> None:
    assert _create(description="a" * DESCRIPTION_MAX_LENGTH).description is not None


@pytest.mark.parametrize(
    "location",
    [
        GeoPoint(longitude=-74.0721, latitude=4.7110),  # Bogotá
        GeoPoint(longitude=-77.2811, latitude=1.2501),  # justo al norte del borde
        GeoPoint(longitude=-77.2299, latitude=1.2136),  # justo al este del borde
    ],
)
def test_location_outside_the_service_area_is_rejected(location: GeoPoint) -> None:
    with pytest.raises(LocationOutsideServiceAreaError):
        _create(location=location)


@pytest.mark.parametrize(
    "location",
    [
        GeoPoint(longitude=-77.33, latitude=1.16),  # esquina suroeste
        GeoPoint(longitude=-77.23, latitude=1.25),  # esquina noreste
    ],
)
def test_the_edge_of_the_area_counts_as_inside(location: GeoPoint) -> None:
    assert PASTO_AREA.contains(location)


@pytest.mark.parametrize(
    ("has_road", "road_name", "expected"),
    [
        (True, "Avenida Panamericana", "Avenida Panamericana"),
        (True, "  Calle 18  ", "Calle 18"),
        (True, None, UNNAMED_ROAD),
        (True, "   ", UNNAMED_ROAD),
        (False, None, NO_ROAD),
    ],
)
def test_display_address(has_road: bool, road_name: str | None, expected: str) -> None:
    assert display_address(has_road=has_road, road_name=road_name) == expected


def _details(priority_score: Decimal | None, road_id: int | None) -> ReportDetails:
    return ReportDetails(
        id=uuid.uuid4(),
        user_id=USER_ID,
        location=PASTO,
        severity=Severity.MEDIUM,
        description=None,
        status=ReportStatus.EVALUATED,
        priority_score=priority_score,
        road_id=road_id,
        road_name=None,
        created_at=datetime(2026, 10, 19, tzinfo=UTC),
    )


@pytest.mark.parametrize(
    ("priority_score", "road_id", "expected"),
    [
        (Decimal("3.60"), None, True),  # Sector Obonuco (guía 8.3)
        (Decimal("8.70"), 7, False),
        (None, None, False),  # sin evaluar todavía: no se sabe
    ],
)
def test_needs_road_review(
    priority_score: Decimal | None, road_id: int | None, expected: bool
) -> None:
    assert _details(priority_score, road_id).needs_road_review is expected


def test_photo_keys_are_random_and_share_a_folder() -> None:
    first, second = PhotoKeys.new(), PhotoKeys.new()

    assert first.photo != second.photo
    folder, name = first.photo.split("/")
    assert first.thumbnail == f"{folder}/{name.removesuffix('.jpg')}_min.jpg"
    assert PhotoKeys.from_photo_key(first.photo) == first


@pytest.mark.parametrize("level", list(SeverityLevel))
def test_severity_level_round_trip(level: SeverityLevel) -> None:
    assert SeverityLevel.from_domain(level.to_domain()) is level


def test_severity_levels_follow_the_thesis_order() -> None:
    assert [level.to_domain() for level in SeverityLevel] == [
        Severity.LOW,
        Severity.MEDIUM,
        Severity.HIGH,
    ]
