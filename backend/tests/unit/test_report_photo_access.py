"""Acceso a la foto del reporte: solo su autor y los administradores (propuesta 34)."""

import uuid
from collections.abc import Iterator
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import API_V1_PREFIX, create_app
from app.modules.auth.presentation.dependencies import get_current_user
from app.modules.reports.application.get_photo import (
    GetReportPhoto,
    PhotoNotAvailableError,
    PhotoViewer,
)
from app.modules.reports.domain.photos import PhotoKeys, ReportPhoto, can_view_photo
from app.modules.reports.domain.ports import PhotoNotStoredError
from app.modules.reports.presentation.dependencies import get_report_photo
from app.modules.users.domain.entities import User
from app.modules.users.domain.role import UserRole

OWNER = uuid.UUID("00000000-0000-0000-0000-000000000001")
OTHER = uuid.UUID("00000000-0000-0000-0000-000000000002")
REPORT = uuid.UUID("00000000-0000-0000-0000-0000000000aa")
KEYS = PhotoKeys.for_name("ab12")


class FakeLookup:
    def __init__(self, photo: ReportPhoto | None) -> None:
        self._photo = photo

    def find_photo(self, report_id: uuid.UUID) -> ReportPhoto | None:
        return self._photo if report_id == REPORT else None


class FakeReader:
    def __init__(self, files: dict[str, bytes]) -> None:
        self._files = files

    def read(self, key: str) -> bytes:
        if key not in self._files:
            raise PhotoNotStoredError(key)
        return self._files[key]


FILES = {KEYS.photo: b"foto-grande", KEYS.thumbnail: b"miniatura"}


def _use_case(
    photo_key: str | None = KEYS.photo, files: dict[str, bytes] = FILES
) -> GetReportPhoto:
    return GetReportPhoto(FakeLookup(ReportPhoto(OWNER, photo_key)), FakeReader(files))


@pytest.mark.parametrize(
    ("viewer_id", "is_admin", "expected"),
    [(OWNER, False, True), (OTHER, True, True), (OTHER, False, False)],
)
def test_who_can_view_the_photo(viewer_id: uuid.UUID, is_admin: bool, expected: bool) -> None:
    assert can_view_photo(viewer_id=viewer_id, viewer_is_admin=is_admin, owner_id=OWNER) is expected


@pytest.mark.parametrize(("thumbnail", "content"), [(False, b"foto-grande"), (True, b"miniatura")])
def test_the_owner_gets_the_photo_and_its_thumbnail(thumbnail: bool, content: bytes) -> None:
    viewer = PhotoViewer(OWNER, is_admin=False)

    assert _use_case().execute(REPORT, viewer, thumbnail=thumbnail) == content


def test_an_admin_gets_any_photo() -> None:
    viewer = PhotoViewer(OTHER, is_admin=True)

    assert _use_case().execute(REPORT, viewer, thumbnail=False) == b"foto-grande"


@pytest.mark.parametrize(
    ("report_id", "use_case"),
    [
        (REPORT, _use_case()),  # reporte de otro ciudadano
        (uuid.uuid4(), _use_case()),  # reporte que no existe
    ],
    ids=["ajeno", "inexistente"],
)
def test_another_citizen_cannot_tell_whether_the_report_exists(
    report_id: uuid.UUID, use_case: GetReportPhoto
) -> None:
    with pytest.raises(PhotoNotAvailableError):
        use_case.execute(report_id, PhotoViewer(OTHER, is_admin=False), thumbnail=False)


def test_report_without_a_photo() -> None:
    with pytest.raises(PhotoNotAvailableError):
        _use_case(photo_key=None).execute(
            REPORT, PhotoViewer(OWNER, is_admin=False), thumbnail=False
        )


def test_missing_file_is_logged_and_treated_as_not_available(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with pytest.raises(PhotoNotAvailableError):
        _use_case(files={}).execute(REPORT, PhotoViewer(OWNER, is_admin=False), thumbnail=False)

    assert KEYS.photo in caplog.text


# --- Rutas HTTP -------------------------------------------------------------------


def _user(user_id: uuid.UUID, role: UserRole = UserRole.CITIZEN) -> User:
    return User(
        id=user_id,
        name="Prueba",
        email=f"{user_id.hex[-4:]}@example.com",
        password_hash="hash",
        role=role,
        is_active=True,
        consent=None,
        registered_at=datetime(2026, 10, 19, tzinfo=UTC),
    )


@pytest.fixture
def client_as(settings: Settings) -> Iterator[object]:
    clients: list[TestClient] = []

    def make(user: User) -> TestClient:
        app = create_app(settings)
        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_report_photo] = _use_case
        client = TestClient(app)
        clients.append(client)
        return client

    yield make
    for client in clients:
        client.close()


PHOTO = f"{API_V1_PREFIX}/reports/{REPORT}/photo"


@pytest.mark.parametrize(
    ("path", "content"), [(PHOTO, b"foto-grande"), (f"{PHOTO}/thumbnail", b"miniatura")]
)
def test_photo_routes_serve_jpeg_without_caching(
    client_as: object, path: str, content: bytes
) -> None:
    response = client_as(_user(OWNER)).get(path)  # type: ignore[operator]

    assert response.status_code == 200
    assert response.content == content
    assert response.headers["content-type"] == "image/jpeg"
    assert response.headers["cache-control"] == "private, no-store"
    assert response.headers["x-content-type-options"] == "nosniff"


def test_admin_gets_the_photo_over_http(client_as: object) -> None:
    response = client_as(_user(OTHER, UserRole.ADMIN)).get(PHOTO)  # type: ignore[operator]

    assert response.status_code == 200


def test_other_citizen_gets_404(client_as: object) -> None:
    response = client_as(_user(OTHER)).get(PHOTO)  # type: ignore[operator]

    assert response.status_code == 404
    assert response.json()["code"] == "PHOTO_NOT_FOUND"


def test_report_id_must_be_a_uuid(client_as: object) -> None:
    response = client_as(_user(OWNER)).get(f"{API_V1_PREFIX}/reports/123/photo")  # type: ignore[operator]

    assert response.status_code == 422


def test_photo_requires_a_session(settings: Settings) -> None:
    with TestClient(create_app(settings)) as client:
        assert client.get(PHOTO).status_code == 401
