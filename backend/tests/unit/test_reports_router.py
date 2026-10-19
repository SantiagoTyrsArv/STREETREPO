"""POST /api/v1/reports sin base de datos: formulario, códigos HTTP y errores."""

import uuid
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import API_V1_PREFIX, create_app
from app.modules.auth.presentation.dependencies import get_current_user
from app.modules.reports.application.find_nearby import FindPossibleDuplicates, NearbyPolicy
from app.modules.reports.domain.photos import (
    MAX_PHOTO_BYTES,
    InvalidPhotoError,
    UnsupportedPhotoTypeError,
)
from app.modules.reports.infrastructure.pillow_photos import PillowPhotoProcessor
from app.modules.reports.presentation.dependencies import (
    get_create_report,
    get_find_possible_duplicates,
)
from app.modules.users.domain.entities import User
from app.modules.users.domain.role import UserRole
from app.shared.application.clock import SystemClock
from app.shared.application.rate_limit import RateLimit
from app.shared.domain.geo import BoundingBox
from app.shared.infrastructure.memory_rate_limiter import InMemoryRateLimiter
from tests.images import image_bytes
from tests.unit.test_create_report import USER_ID, FakeNearby, FakeProcessor, Harness, candidate

REPORTS = f"{API_V1_PREFIX}/reports"
CITIZEN = User(
    id=USER_ID,
    name="Ana",
    email="ana@example.com",
    password_hash="hash",
    role=UserRole.CITIZEN,
    is_active=True,
    consent=None,
    registered_at=datetime(2026, 10, 19, tzinfo=UTC),
)
FORM = {"longitude": "-77.2811", "latitude": "1.2136", "severity": "alta"}
PASTO_AREA = "1.16,-77.33,1.25,-77.23"


def _client(settings: Settings, harness: Harness) -> TestClient:
    app = create_app(settings)
    app.dependency_overrides[get_current_user] = lambda: CITIZEN
    app.dependency_overrides[get_create_report] = lambda: harness.use_case
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def harness() -> Harness:
    return Harness()


@pytest.fixture
def api(settings: Settings, harness: Harness) -> Iterator[TestClient]:
    with _client(settings, harness) as client:
        yield client


def _photo(content: bytes | None = None) -> dict[str, tuple[str, bytes, str]]:
    return {"photo": ("foto.jpg", content or image_bytes(), "image/jpeg")}


def test_creates_a_report_from_the_form(api: TestClient, harness: Harness) -> None:
    response = api.post(REPORTS, data=FORM | {"description": "Hueco profundo"}, files=_photo())

    assert response.status_code == 201
    body = response.json()
    assert body["severity"] == "alta"
    assert body["status"] == "evaluado"
    assert body["description"] == "Hueco profundo"
    assert body["location"] == {"longitude": -77.2811, "latitude": 1.2136}
    assert body["priority_score"] == "8.70"
    assert body["address"] == "Avenida Los Estudiantes"
    assert body["needs_road_review"] is False
    assert set(body) == {
        "id",
        "status",
        "severity",
        "description",
        "location",
        "address",
        "priority_score",
        "needs_road_review",
        "created_at",
    }
    assert harness.reports.saved[uuid.UUID(body["id"])].user_id == USER_ID


def test_retry_with_the_same_idempotency_key_answers_200(api: TestClient) -> None:
    headers = {"Idempotency-Key": str(uuid.uuid4())}
    first = api.post(REPORTS, data=FORM, files=_photo(), headers=headers)

    second = api.post(REPORTS, data=FORM, files=_photo(), headers=headers)

    assert (first.status_code, second.status_code) == (201, 200)
    assert second.json()["id"] == first.json()["id"]


def test_idempotency_key_must_be_a_uuid(api: TestClient) -> None:
    response = api.post(
        REPORTS, data=FORM, files=_photo(), headers={"Idempotency-Key": "reintento-1"}
    )

    assert response.status_code == 422
    assert response.json()["code"] == "VALIDATION_ERROR"


@pytest.mark.parametrize(
    ("form", "field"),
    [
        ({"latitude": "1.2136", "severity": "alta"}, "longitude"),
        (FORM | {"severity": "urgente"}, "severity"),
        (FORM | {"latitude": "95"}, "latitude"),
        (FORM | {"description": "a" * 501}, "description"),
    ],
)
def test_invalid_form_fields(api: TestClient, form: dict[str, str], field: str) -> None:
    response = api.post(REPORTS, data=form, files=_photo())

    assert response.status_code == 422
    assert field in {issue["field"] for issue in response.json()["details"]["fields"]}


def test_photo_is_required(api: TestClient) -> None:
    response = api.post(REPORTS, data=FORM)

    assert response.status_code == 422
    assert "photo" in {issue["field"] for issue in response.json()["details"]["fields"]}


def test_location_outside_the_service_area(api: TestClient) -> None:
    form = FORM | {"longitude": "-74.0721", "latitude": "4.7110"}

    response = api.post(REPORTS, data=form, files=_photo())

    assert response.status_code == 422
    assert response.json()["code"] == "LOCATION_OUTSIDE_SERVICE_AREA"


def test_photo_over_10_mb(api: TestClient) -> None:
    response = api.post(REPORTS, data=FORM, files=_photo(b"x" * (MAX_PHOTO_BYTES + 1)))

    assert response.status_code == 413
    assert response.json()["code"] == "PHOTO_TOO_LARGE"
    assert response.json()["details"]["max_bytes"] == MAX_PHOTO_BYTES


@pytest.mark.parametrize(
    ("error", "status", "code"),
    [
        (UnsupportedPhotoTypeError("gif"), 415, "PHOTO_UNSUPPORTED_TYPE"),
        (InvalidPhotoError("dañada"), 422, "PHOTO_INVALID"),
    ],
)
def test_photo_errors(settings: Settings, error: Exception, status: int, code: str) -> None:
    with _client(settings, Harness(processor=FakeProcessor(error))) as client:
        response = client.post(REPORTS, data=FORM, files=_photo())

    assert response.status_code == status
    assert response.json()["code"] == code


def test_a_gif_named_jpg_is_rejected_by_its_content(settings: Settings) -> None:
    with _client(settings, Harness(processor=PillowPhotoProcessor())) as client:
        response = client.post(REPORTS, data=FORM, files=_photo(image_bytes("GIF")))

    assert response.status_code == 415


def test_hourly_limit_per_user(api: TestClient) -> None:
    for _ in range(2):  # Harness: dos por hora
        assert api.post(REPORTS, data=FORM, files=_photo()).status_code == 201

    response = api.post(REPORTS, data=FORM, files=_photo())

    assert response.status_code == 429
    assert response.json()["code"] == "REPORT_RATE_LIMITED"
    assert int(response.headers["Retry-After"]) == 3600


def test_hourly_limit_per_ip(settings: Settings) -> None:
    limited = settings.model_copy(update={"reports_per_ip_per_hour": 1})
    with _client(limited, Harness()) as client:
        assert client.post(REPORTS, data=FORM, files=_photo()).status_code == 201

        response = client.post(REPORTS, data=FORM, files=_photo())

    assert response.status_code == 429
    assert response.json()["code"] == "RATE_LIMITED"


def test_requires_a_session(settings: Settings) -> None:
    with TestClient(create_app(settings)) as client:
        response = client.post(REPORTS, data=FORM, files=_photo())

    assert response.status_code == 401


# --- Posible duplicado (propuesta 36) ---------------------------------------------


def test_nearby_active_report_answers_409_with_the_candidates(
    api: TestClient, harness: Harness
) -> None:
    existing = candidate(distance_m=12.345)
    harness.nearby.default = [existing]

    response = api.post(REPORTS, data=FORM, files=_photo())

    assert response.status_code == 409
    body = response.json()
    assert body["code"] == "REPORT_DUPLICATE_NEARBY"
    assert body["details"]["radius_m"] == 25.0
    assert body["details"]["items"] == [
        {
            "id": str(existing.id),
            "location": {"longitude": -77.2811, "latitude": 1.2137},
            "distance_m": 12.3,
            "status": "evaluado",
            "severity": "media",
            "confirmations": 3,
            "address": "Carrera 27",
            "created_at": "2026-10-19T12:00:00Z",
            "is_mine": False,
        }
    ]
    assert harness.reports.saved == {}


def test_create_anyway_in_the_form(api: TestClient, harness: Harness) -> None:
    harness.nearby.default = [candidate()]

    response = api.post(REPORTS, data=FORM | {"create_anyway": "true"}, files=_photo())

    assert response.status_code == 201


def _nearby_client(
    settings: Settings, nearby: FakeNearby, limit: int = 10, area: str = PASTO_AREA
) -> TestClient:
    use_case = FindPossibleDuplicates(
        nearby,
        InMemoryRateLimiter(),
        NearbyPolicy(
            service_area=BoundingBox.parse(area),
            limit_per_user=RateLimit(max_requests=limit, window=timedelta(hours=1)),
        ),
        SystemClock(),
    )
    app = create_app(settings)
    app.dependency_overrides[get_current_user] = lambda: CITIZEN
    app.dependency_overrides[get_find_possible_duplicates] = lambda: use_case
    return TestClient(app)


def test_nearby_lists_active_reports_within_25_m(settings: Settings) -> None:
    nearby = FakeNearby()
    nearby.default = [candidate(distance_m=3.0), candidate(distance_m=20.0)]

    with _nearby_client(settings, nearby) as client:
        response = client.get(
            f"{REPORTS}/nearby", params={"longitude": -77.2811, "latitude": 1.2136}
        )

    assert response.status_code == 200
    assert [item["distance_m"] for item in response.json()["items"]] == [3.0, 20.0]
    point, radius_m = nearby.calls[0]
    assert (point.longitude, point.latitude, radius_m) == (-77.2811, 1.2136, 25.0)
    # Nada del autor ni su descripción; la ubicación es la pública (otra prueba la revisa).
    assert not {"user_id", "author", "description"} & set(response.json()["items"][0])


def test_nearby_without_results(settings: Settings) -> None:
    with _nearby_client(settings, FakeNearby()) as client:
        response = client.get(f"{REPORTS}/nearby", params={"longitude": -77.28, "latitude": 1.21})

    assert response.json() == {"radius_m": 25.0, "items": []}


@pytest.mark.parametrize("params", [{"longitude": -77.28}, {"longitude": -77.28, "latitude": 91}])
def test_nearby_validates_the_point(settings: Settings, params: dict[str, float]) -> None:
    with _nearby_client(settings, FakeNearby()) as client:
        response = client.get(f"{REPORTS}/nearby", params=params)

    assert response.status_code == 422


def test_nearby_requires_a_session(settings: Settings) -> None:
    with TestClient(create_app(settings)) as client:
        response = client.get(f"{REPORTS}/nearby", params={"longitude": -77.28, "latitude": 1.21})

    assert response.status_code == 401


def test_candidates_show_only_the_public_location(settings: Settings) -> None:
    nearby = FakeNearby()
    nearby.default = [candidate()]

    with _nearby_client(settings, nearby) as client:
        item = client.get(
            f"{REPORTS}/nearby", params={"longitude": -77.2811, "latitude": 1.2136}
        ).json()["items"][0]

    # Cuatro decimales como máximo, aunque el doble traiga más.
    assert item["location"] == {"longitude": -77.2811, "latitude": 1.2137}


def test_nearby_outside_the_service_area(settings: Settings) -> None:
    with _nearby_client(settings, FakeNearby()) as client:
        response = client.get(
            f"{REPORTS}/nearby", params={"longitude": -74.0721, "latitude": 4.7110}
        )

    assert response.status_code == 422
    assert response.json()["code"] == "LOCATION_OUTSIDE_SERVICE_AREA"


def test_nearby_has_its_own_hourly_limit_per_user(settings: Settings) -> None:
    nearby = FakeNearby()
    params = {"longitude": -77.2811, "latitude": 1.2136}
    with _nearby_client(settings, nearby, limit=2) as client:
        statuses = [client.get(f"{REPORTS}/nearby", params=params).status_code for _ in range(3)]
        response = client.get(f"{REPORTS}/nearby", params=params)

    assert statuses == [200, 200, 429]
    assert response.json()["code"] == "NEARBY_RATE_LIMITED"
    assert "Retry-After" in response.headers
    # Ni el área inválida ni el rechazo por cupo llegan a consultar la base.
    assert len(nearby.calls) == 2
