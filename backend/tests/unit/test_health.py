from collections.abc import Iterator
from unittest.mock import MagicMock

from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from app.core.database import get_session


def test_health_returns_ok(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def _override_session(client: TestClient, session: MagicMock) -> None:
    def fake_session() -> Iterator[MagicMock]:
        yield session

    client.app.dependency_overrides[get_session] = fake_session  # type: ignore[attr-defined]


def test_ready_returns_ok_when_database_answers(client: TestClient) -> None:
    session = MagicMock()
    _override_session(client, session)

    response = client.get("/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    session.execute.assert_called_once()


def test_ready_returns_503_with_uniform_error_when_database_fails(client: TestClient) -> None:
    session = MagicMock()
    session.execute.side_effect = OperationalError("SELECT 1", {}, Exception("caída"))
    _override_session(client, session)

    response = client.get("/ready")

    assert response.status_code == 503
    body = response.json()
    assert body["code"] == "DB_UNAVAILABLE"
    assert "caída" not in response.text
