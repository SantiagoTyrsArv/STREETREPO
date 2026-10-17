import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.core.config import Environment, Settings
from app.main import create_app
from tests.conftest import TEST_JWT_SECRET

POLICY_URL = "https://streetrepo.example.test/politica-de-datos"


def test_policy_url_is_optional_and_empty_text_means_none() -> None:
    assert Settings().privacy_policy_url is None
    assert Settings(privacy_policy_url="").privacy_policy_url is None
    assert Settings(privacy_policy_url="  ").privacy_policy_url is None


def test_policy_url_must_be_a_valid_http_url() -> None:
    with pytest.raises(ValidationError):
        Settings(privacy_policy_url="no-es-una-url")


def test_privacy_policy_is_public_and_url_is_null_when_not_configured(
    client: TestClient,
) -> None:
    response = client.get("/api/v1/privacy-policy")

    assert response.status_code == 200
    assert response.json() == {"version": "1.0", "url": None}


def test_privacy_policy_returns_the_configured_version_and_url() -> None:
    settings = Settings(
        app_env=Environment.TEST,
        jwt_secret_key=TEST_JWT_SECRET,
        privacy_policy_version="2.1",
        privacy_policy_url=POLICY_URL,
    )
    with TestClient(create_app(settings)) as test_client:
        body = test_client.get("/api/v1/privacy-policy").json()

    assert body == {"version": "2.1", "url": POLICY_URL}


def test_production_refuses_to_start_without_a_policy_url() -> None:
    with pytest.raises(ValueError, match="PRIVACY_POLICY_URL"):
        create_app(Settings(app_env=Environment.PROD, jwt_secret_key=TEST_JWT_SECRET))


def test_production_refuses_to_start_with_a_policy_url_without_https() -> None:
    settings = Settings(
        app_env=Environment.PROD,
        jwt_secret_key=TEST_JWT_SECRET,
        privacy_policy_url="http://streetrepo.example.test/politica-de-datos",
    )

    with pytest.raises(ValueError, match="https"):
        create_app(settings)
