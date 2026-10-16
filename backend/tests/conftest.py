from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.core.config import Environment, Settings
from app.main import create_app

PANEL_ORIGIN = "http://panel.test"
# Solo para pruebas: cumple el largo mínimo y es obviamente falsa.
TEST_JWT_SECRET = "x" * 64


@pytest.fixture
def settings() -> Settings:
    return Settings(
        app_env=Environment.TEST, cors_origins=PANEL_ORIGIN, jwt_secret_key=TEST_JWT_SECRET
    )


@pytest.fixture
def client(settings: Settings) -> Iterator[TestClient]:
    with TestClient(create_app(settings), raise_server_exceptions=False) as test_client:
        yield test_client
