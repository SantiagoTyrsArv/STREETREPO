"""Sesión web del panel (decisión 42, ADR 0004): cookie HttpOnly, CSRF y origen."""

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from httpx import Response
from sqlalchemy import Connection, text
from sqlalchemy.orm import Session

from app.core.config import Environment, Settings
from app.core.database import get_session
from app.main import API_V1_PREFIX, create_app
from tests.conftest import TEST_JWT_SECRET
from tests.integration.conftest import (
    EMAIL,
    PASSWORD,
    TEST_REPORT_AREA,
    bearer,
    login_user,
    register_user,
    requires_db,
)

pytestmark = [pytest.mark.integration, requires_db]

WEB = f"{API_V1_PREFIX}/auth/web"
PANEL_ORIGIN = "http://localhost:8081"
PANEL_HEADERS = {"Origin": PANEL_ORIGIN, "X-CSRF-Protection": "1"}
COOKIE = "sr_refresh"
CREDENTIALS = {"email": EMAIL, "password": PASSWORD}


@pytest.fixture
def web(session: Session, photo_dir: Path) -> Iterator[TestClient]:
    """Cliente HTTPS (la cookie es Secure) con el origen del panel en CORS_ORIGINS."""
    app = create_app(
        Settings(
            app_env=Environment.TEST,
            jwt_secret_key=TEST_JWT_SECRET,
            photo_storage_dir=photo_dir,
            report_area_bbox=TEST_REPORT_AREA,
            cors_origins=PANEL_ORIGIN,
        )
    )

    def test_session() -> Iterator[Session]:
        yield session

    app.dependency_overrides[get_session] = test_session
    with TestClient(app, base_url="https://testserver") as client:
        yield client


def _admin(web: TestClient, conn: Connection) -> None:
    register_user(web, email=EMAIL)
    conn.execute(text("UPDATE usuario SET rol = 'administrador' WHERE correo = :c"), {"c": EMAIL})


def _login(web: TestClient, headers: dict[str, str] | None = None) -> Response:
    return web.post(f"{WEB}/login", json=CREDENTIALS, headers=PANEL_HEADERS | (headers or {}))


def _set_cookie(response: Response) -> str:
    header = response.headers.get("set-cookie", "")
    assert header.startswith(f"{COOKIE}="), header
    return header


def _active_sessions(conn: Connection) -> int:
    count: int = conn.execute(
        text("SELECT count(*) FROM token_refresco WHERE NOT revocado")
    ).scalar_one()
    return count


def test_web_login_sets_httponly_cookie_and_no_refresh_in_body(
    web: TestClient, conn: Connection
) -> None:
    _admin(web, conn)

    response = _login(web)

    assert response.status_code == 200, response.json()
    body = response.json()
    assert set(body) == {"access_token", "token_type", "expires_in"}
    assert body["token_type"] == "bearer"
    cookie = _set_cookie(response)
    attributes = {part.strip().lower() for part in cookie.split(";")}
    assert {"httponly", "secure", "samesite=strict", "path=/api/v1/auth/web"} <= attributes
    assert "max-age=604800" in attributes
    assert web.get(f"{API_V1_PREFIX}/me", headers=bearer(body["access_token"])).status_code == 200


def test_web_login_citizen_is_403(web: TestClient, conn: Connection) -> None:
    register_user(web, email=EMAIL)

    response = _login(web)

    assert response.status_code == 403
    assert response.json()["code"] == "ADMIN_ROLE_REQUIRED"
    assert response.json()["message"] == "Esta cuenta no tiene acceso al panel."
    assert "set-cookie" not in response.headers
    assert _active_sessions(conn) == 0


def test_web_login_wrong_password_is_401(web: TestClient, conn: Connection) -> None:
    _admin(web, conn)

    response = web.post(
        f"{WEB}/login", json={"email": EMAIL, "password": "otra cosa"}, headers=PANEL_HEADERS
    )

    assert response.status_code == 401
    assert response.json()["code"] == "INVALID_CREDENTIALS"


def test_web_login_locks_like_the_app_login(web: TestClient, conn: Connection) -> None:
    _admin(web, conn)
    wrong = {"email": EMAIL, "password": "otra cosa"}
    for _ in range(5):
        assert web.post(f"{WEB}/login", json=wrong, headers=PANEL_HEADERS).status_code == 401

    response = _login(web)

    assert response.status_code == 429
    assert response.json()["code"] == "TOO_MANY_LOGIN_ATTEMPTS"
    assert "retry-after" in response.headers


def test_web_login_without_csrf_header_is_403(web: TestClient, conn: Connection) -> None:
    _admin(web, conn)

    missing = web.post(f"{WEB}/login", json=CREDENTIALS, headers={"Origin": PANEL_ORIGIN})
    wrong = _login(web, {"X-CSRF-Protection": "0"})

    for response in (missing, wrong):
        assert response.status_code == 403
        assert response.json()["code"] == "CSRF_CHECK_FAILED"
    assert _active_sessions(conn) == 0


@pytest.mark.parametrize("origin", ["https://evil.example", "null", ""])
def test_web_login_foreign_origin_is_403(web: TestClient, conn: Connection, origin: str) -> None:
    _admin(web, conn)
    headers = {"X-CSRF-Protection": "1"} | ({"Origin": origin} if origin else {})

    response = web.post(f"{WEB}/login", json=CREDENTIALS, headers=headers)

    assert response.status_code == 403
    assert response.json()["code"] == "CSRF_CHECK_FAILED"


def test_web_refresh_rotates_cookie(web: TestClient, conn: Connection) -> None:
    _admin(web, conn)
    first = _set_cookie(_login(web))

    response = web.post(f"{WEB}/refresh", headers=PANEL_HEADERS)

    assert response.status_code == 200, response.json()
    assert set(response.json()) == {"access_token", "token_type", "expires_in"}
    second = _set_cookie(response)
    assert second.split(";")[0] != first.split(";")[0]
    assert _active_sessions(conn) == 1


def test_web_refresh_reused_cookie_revokes_chain(web: TestClient, conn: Connection) -> None:
    _admin(web, conn)
    _login(web)
    stolen = web.cookies.get(COOKIE)
    assert web.post(f"{WEB}/refresh", headers=PANEL_HEADERS).status_code == 200

    web.cookies.clear()
    reused = web.post(f"{WEB}/refresh", headers=PANEL_HEADERS | {"Cookie": f"{COOKIE}={stolen}"})

    assert reused.status_code == 401
    assert reused.json()["code"] == "INVALID_SESSION"
    assert _active_sessions(conn) == 0


def test_web_refresh_without_cookie_is_401_and_clears(web: TestClient) -> None:
    response = web.post(f"{WEB}/refresh", headers=PANEL_HEADERS)

    assert response.status_code == 401
    assert response.json()["code"] == "INVALID_SESSION"
    cleared = _set_cookie(response).lower()
    assert "max-age=0" in cleared
    assert "path=/api/v1/auth/web" in cleared


def test_web_refresh_of_demoted_admin_is_403_and_clears(web: TestClient, conn: Connection) -> None:
    _admin(web, conn)
    _login(web)
    conn.execute(text("UPDATE usuario SET rol = 'ciudadano' WHERE correo = :c"), {"c": EMAIL})

    response = web.post(f"{WEB}/refresh", headers=PANEL_HEADERS)

    assert response.status_code == 403
    assert response.json()["code"] == "ADMIN_ROLE_REQUIRED"
    assert "max-age=0" in _set_cookie(response).lower()
    assert _active_sessions(conn) == 0


def test_web_refresh_requires_csrf(web: TestClient, conn: Connection) -> None:
    _admin(web, conn)
    _login(web)

    response = web.post(f"{WEB}/refresh", headers={"Origin": PANEL_ORIGIN})

    assert response.status_code == 403
    assert _active_sessions(conn) == 1


def test_web_logout_revokes_and_clears(web: TestClient, conn: Connection) -> None:
    _admin(web, conn)
    _login(web)

    response = web.post(f"{WEB}/logout", headers=PANEL_HEADERS)

    assert response.status_code == 204
    assert "max-age=0" in _set_cookie(response).lower()
    assert _active_sessions(conn) == 0
    again = web.post(f"{WEB}/logout", headers=PANEL_HEADERS)
    assert again.status_code == 204


def test_web_logout_requires_csrf(web: TestClient, conn: Connection) -> None:
    _admin(web, conn)
    _login(web)

    assert web.post(f"{WEB}/logout", headers={"Origin": PANEL_ORIGIN}).status_code == 403
    assert _active_sessions(conn) == 1


def test_cors_preflight_allows_credentials_for_panel_origin(web: TestClient) -> None:
    response = web.options(
        f"{WEB}/login",
        headers={
            "Origin": PANEL_ORIGIN,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type,x-csrf-protection",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == PANEL_ORIGIN
    assert response.headers["access-control-allow-credentials"] == "true"
    assert "x-csrf-protection" in response.headers["access-control-allow-headers"].lower()


def test_cors_preflight_rejects_foreign_origin(web: TestClient) -> None:
    response = web.options(
        f"{WEB}/login",
        headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "POST"},
    )

    assert "access-control-allow-origin" not in response.headers


def test_app_login_unchanged(web: TestClient, conn: Connection) -> None:
    register_user(web, email=EMAIL)

    body = login_user(web)

    assert body["_status"] == 200
    assert {"access_token", "refresh_token", "expires_in", "token_type"} <= set(body)
