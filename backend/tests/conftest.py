from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.core.config import Environment, Settings
from app.main import create_app

PANEL_ORIGIN = "http://panel.test"


@pytest.fixture
def settings() -> Settings:
    return Settings(app_env=Environment.TEST, cors_origins=PANEL_ORIGIN)


@pytest.fixture
def client(settings: Settings) -> Iterator[TestClient]:
    with TestClient(create_app(settings), raise_server_exceptions=False) as test_client:
        yield test_client
