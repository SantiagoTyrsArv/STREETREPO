import json
import logging

import pytest
from fastapi.testclient import TestClient

from app.core.config import Environment, Settings
from app.core.logging import CORRELATION_HEADER, JsonFormatter
from app.main import create_app
from tests.conftest import PANEL_ORIGIN, TEST_JWT_SECRET


def test_security_headers_are_present(client: TestClient) -> None:
    headers = client.get("/health").headers

    assert headers["X-Content-Type-Options"] == "nosniff"
    assert headers["X-Frame-Options"] == "DENY"
    assert "default-src 'none'" in headers["Content-Security-Policy"]
    assert "Strict-Transport-Security" not in headers


def _production() -> Settings:
    return Settings(
        app_env=Environment.PROD,
        jwt_secret_key=TEST_JWT_SECRET,
        privacy_policy_url="https://streetrepo.example.test/politica-de-datos",
    )


def test_hsts_only_in_production() -> None:
    with TestClient(create_app(_production())) as prod_client:
        assert "Strict-Transport-Security" in prod_client.get("/health").headers


def test_docs_disabled_in_production() -> None:
    with TestClient(create_app(_production())) as prod_client:
        assert prod_client.get("/docs").status_code == 404


def test_production_refuses_to_start_without_a_strong_jwt_secret() -> None:
    settings = Settings(app_env=Environment.PROD, jwt_secret_key="corta")

    with pytest.raises(ValueError, match="JWT_SECRET_KEY"):
        create_app(settings)


def test_cors_allows_only_panel_origin(client: TestClient) -> None:
    allowed = client.get("/health", headers={"Origin": PANEL_ORIGIN})
    denied = client.get("/health", headers={"Origin": "http://malicioso.test"})

    assert allowed.headers["access-control-allow-origin"] == PANEL_ORIGIN
    assert "access-control-allow-origin" not in denied.headers


def test_cors_wraps_errors_and_exposes_the_request_id(client: TestClient) -> None:
    # CORS es la capa más externa: el panel puede leer los errores y su X-Request-ID.
    response = client.get("/no-existe", headers={"Origin": PANEL_ORIGIN})

    assert response.status_code == 404
    assert response.headers["access-control-allow-origin"] == PANEL_ORIGIN
    assert CORRELATION_HEADER in response.headers
    assert CORRELATION_HEADER.lower() in response.headers["access-control-expose-headers"].lower()
    assert response.headers["x-content-type-options"] == "nosniff"


def test_preflight_is_answered_for_the_panel(client: TestClient) -> None:
    response = client.options(
        "/api/v1/me",
        headers={"Origin": PANEL_ORIGIN, "Access-Control-Request-Method": "PATCH"},
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == PANEL_ORIGIN


def test_request_id_is_generated(client: TestClient) -> None:
    assert len(client.get("/health").headers[CORRELATION_HEADER]) == 32


def test_valid_request_id_is_propagated(client: TestClient) -> None:
    response = client.get("/health", headers={CORRELATION_HEADER: "abc-123"})

    assert response.headers[CORRELATION_HEADER] == "abc-123"


@pytest.mark.parametrize("bad_id", ["<script>", "a" * 65, "id con espacios"])
def test_unsafe_request_id_is_replaced(client: TestClient, bad_id: str) -> None:
    response = client.get("/health", headers={CORRELATION_HEADER: bad_id})

    assert response.headers[CORRELATION_HEADER] != bad_id


def test_json_formatter_outputs_structured_record() -> None:
    record = logging.LogRecord("app", logging.INFO, __file__, 1, "hola %s", ("mundo",), None)

    payload = json.loads(JsonFormatter().format(record))

    assert payload["message"] == "hola mundo"
    assert payload["level"] == "INFO"
    assert payload["request_id"] == "-"
