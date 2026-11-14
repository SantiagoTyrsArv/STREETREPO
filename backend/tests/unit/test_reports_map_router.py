"""GET /api/v1/reports por HTTP, con el caso de uso sustituido (sin base de datos)."""

import uuid
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import API_V1_PREFIX, create_app
from app.modules.auth.presentation.dependencies import get_current_user
from app.modules.reports.domain.my_reports import PublicReportView
from app.modules.reports.domain.public_map import MapReport, MapReportsPage
from app.modules.reports.domain.severity import Severity
from app.modules.reports.domain.status import ReportStatus
from app.modules.reports.presentation.dependencies import get_list_reports_in_area
from app.shared.application.rate_limit import RateLimitExceededError
from app.shared.domain.geo import BoundingBox, GeoPoint
from tests.unit.test_reports_router import CITIZEN

REPORTS = f"{API_V1_PREFIX}/reports"
BBOX = "-77.29,1.20,-77.27,1.22"
REPORT_ID = uuid.uuid4()


class FakeListReportsInArea:
    def __init__(self) -> None:
        self.calls: list[tuple[uuid.UUID, BoundingBox, ReportStatus | None, int]] = []
        self.rate_limited = False

    def execute(
        self, viewer_id: uuid.UUID, area: BoundingBox, status: ReportStatus | None, limit: int
    ) -> MapReportsPage:
        if self.rate_limited:
            raise RateLimitExceededError(timedelta(seconds=20))
        self.calls.append((viewer_id, area, status, limit))
        report = MapReport(
            public=PublicReportView(
                id=REPORT_ID,
                # Lo que entrega PostGIS tras ST_SnapToGrid puede traer ruido de coma flotante.
                location=GeoPoint(longitude=-77.28110000000001, latitude=1.2137),
                status=ReportStatus.PRIORITIZED,
                severity=Severity.HIGH,
                confirmations=4,
                road_id=7,
                road_name="Avenida Los Estudiantes",
                created_at=datetime(2026, 10, 19, 12, tzinfo=UTC),
            ),
            is_mine=False,
            confirmed_by_me=True,
        )
        return MapReportsPage(items=[report], limit=limit, truncated=True)


@pytest.fixture
def use_case() -> FakeListReportsInArea:
    return FakeListReportsInArea()


@pytest.fixture
def api(settings: Settings, use_case: FakeListReportsInArea) -> Iterator[TestClient]:
    app = create_app(settings)
    app.dependency_overrides[get_current_user] = lambda: CITIZEN
    app.dependency_overrides[get_list_reports_in_area] = lambda: use_case
    with TestClient(app, raise_server_exceptions=False) as client:
        yield client


def test_lists_the_public_view_of_the_reports_in_the_area(
    api: TestClient, use_case: FakeListReportsInArea
) -> None:
    response = api.get(REPORTS, params={"bbox": BBOX})

    assert response.status_code == 200
    assert response.json() == {
        "items": [
            {
                "id": str(REPORT_ID),
                "location": {"longitude": -77.2811, "latitude": 1.2137},
                "status": "priorizado",
                "severity": "alta",
                "address": "Avenida Los Estudiantes",
                "confirmations": 4,
                "created_at": "2026-10-19T12:00:00Z",
                "is_mine": False,
                "confirmed_by_me": True,
            }
        ],
        "limit": 200,
        "truncated": True,
    }
    assert use_case.calls == [
        (CITIZEN.id, BoundingBox(south=1.20, west=-77.29, north=1.22, east=-77.27), None, 200)
    ]


def test_passes_the_status_filter_and_the_limit(
    api: TestClient, use_case: FakeListReportsInArea
) -> None:
    response = api.get(REPORTS, params={"bbox": BBOX, "status": "reparado", "limit": 50})

    assert response.status_code == 200
    assert use_case.calls[0][2:] == (ReportStatus.REPAIRED, 50)


@pytest.mark.parametrize(
    "bbox",
    [
        "-77.29,1.20,-77.27",  # faltan valores
        "a,b,c,d",
        "-77.27,1.20,-77.29,1.22",  # oeste mayor que este
        "-77.29,1.22,-77.27,1.20",  # sur mayor que norte
        "-181,1.20,-77.27,1.22",
        "nan,1.20,-77.27,1.22",
    ],
)
def test_malformed_bbox_is_422(api: TestClient, use_case: FakeListReportsInArea, bbox: str) -> None:
    response = api.get(REPORTS, params={"bbox": bbox})

    assert response.status_code == 422
    assert response.json()["code"] == "INVALID_BBOX"
    assert use_case.calls == []


def test_bbox_is_required(api: TestClient) -> None:
    response = api.get(REPORTS)

    assert response.status_code == 422
    assert response.json()["code"] == "VALIDATION_ERROR"


@pytest.mark.parametrize("params", [{"limit": 0}, {"limit": 201}, {"status": "en_intervencion"}])
def test_invalid_limit_or_status_is_422(
    api: TestClient, use_case: FakeListReportsInArea, params: dict[str, object]
) -> None:
    response = api.get(REPORTS, params={"bbox": BBOX} | params)

    assert response.status_code == 422
    assert use_case.calls == []


def test_too_many_queries_answer_429_with_retry_after(
    api: TestClient, use_case: FakeListReportsInArea
) -> None:
    use_case.rate_limited = True

    response = api.get(REPORTS, params={"bbox": BBOX})

    assert response.status_code == 429
    assert response.json()["code"] == "REPORTS_LIST_RATE_LIMITED"
    assert response.headers["Retry-After"] == "20"


def test_requires_a_session(settings: Settings) -> None:
    with TestClient(create_app(settings)) as client:
        response = client.get(REPORTS, params={"bbox": BBOX})

    assert response.status_code == 401
