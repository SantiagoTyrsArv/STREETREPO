"""Pruebas contra PostgreSQL + PostGIS real (docker compose o servicio de CI)."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.core.database import get_engine
from app.main import create_app
from tests.integration.conftest import requires_db

pytestmark = [pytest.mark.integration, requires_db]


def test_postgis_extension_is_installed() -> None:
    with get_engine().connect() as connection:
        version = connection.execute(text("SELECT postgis_version()")).scalar_one()

    assert version


def test_ready_reports_ok_against_real_database() -> None:
    with TestClient(create_app()) as client:
        response = client.get("/ready")

    assert response.status_code == 200
