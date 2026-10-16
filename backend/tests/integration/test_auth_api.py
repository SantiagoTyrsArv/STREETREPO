"""Flujo de autenticación por HTTP contra PostGIS real (HU-10, HU-11).

La sesión de la API se sustituye por la sesión de prueba (transacción que se
revierte al terminar), así que ningún usuario queda en la base.
"""

from collections.abc import Iterator

import pytest
from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import Connection, text
from sqlalchemy.orm import Session

from app.core.config import Environment, Settings
from app.core.database import get_session
from app.main import API_V1_PREFIX, create_app
from app.modules.auth.application.create_admin import CreateAdmin
from app.modules.auth.infrastructure.passwords import Argon2PasswordHasher
from app.modules.auth.presentation.dependencies import AdminUserDep
from app.modules.users.infrastructure.repository import SqlUserRepository
from tests.conftest import TEST_JWT_SECRET
from tests.integration.conftest import requires_db

pytestmark = [pytest.mark.integration, requires_db]

PASSWORD = "una frase de paso larga"
EMAIL = "ana@example.com"


def _app_with_admin_route() -> FastAPI:
    app = create_app(Settings(app_env=Environment.TEST, jwt_secret_key=TEST_JWT_SECRET))
    probe = APIRouter()

    @probe.get("/admin/probe")
    def admin_probe(admin: AdminUserDep) -> dict[str, str]:
        return {"rol": admin.role.value}

    app.include_router(probe, prefix=API_V1_PREFIX)
    return app


@pytest.fixture
def api(session: Session) -> Iterator[TestClient]:
    app = _app_with_admin_route()

    def test_session() -> Iterator[Session]:
        yield session

    app.dependency_overrides[get_session] = test_session
    with TestClient(app) as client:
        yield client


def _register(api: TestClient, email: str = EMAIL, **overrides: object) -> dict[str, object]:
    body = {
        "name": "Ana Pérez",
        "email": email,
        "password": PASSWORD,
        "accepted_policy": True,
        "policy_version": "1.0",
    } | overrides
    response = api.post(f"{API_V1_PREFIX}/auth/register", json=body)
    result: dict[str, object] = response.json() | {"_status": response.status_code}
    return result


def _login(api: TestClient, email: str = EMAIL, password: str = PASSWORD) -> dict[str, object]:
    response = api.post(f"{API_V1_PREFIX}/auth/login", json={"email": email, "password": password})
    result: dict[str, object] = response.json() | {"_status": response.status_code}
    return result


def _bearer(token: object) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_register_stores_consent_and_a_hashed_password(api: TestClient, conn: Connection) -> None:
    created = _register(api, email=" Ana@Example.COM ")

    assert created["_status"] == 201
    assert created["email"] == EMAIL
    assert created["role"] == "ciudadano"
    assert created["policy_version"] == "1.0"
    assert "password" not in created
    assert "password_hash" not in created
    row = conn.execute(
        text(
            "SELECT password_hash, acepta_politica, version_politica, fecha_aceptacion "
            "FROM usuario WHERE correo = :email"
        ),
        {"email": EMAIL},
    ).one()
    assert row.password_hash.startswith("$argon2id$")
    assert row.acepta_politica is True
    assert row.version_politica == "1.0"
    assert row.fecha_aceptacion is not None


@pytest.mark.parametrize(
    ("overrides", "status", "code"),
    [
        ({"accepted_policy": False}, 422, "POLICY_NOT_ACCEPTED"),
        ({"policy_version": "0.9"}, 409, "POLICY_VERSION_OUTDATED"),
        ({"password": "corta"}, 422, "WEAK_PASSWORD"),
        ({"email": "no-es-correo"}, 422, "VALIDATION_ERROR"),
        ({"role": "administrador"}, 422, "VALIDATION_ERROR"),  # no se puede elegir el rol
    ],
)
def test_register_rejects_invalid_requests(
    api: TestClient, overrides: dict[str, object], status: int, code: str
) -> None:
    result = _register(api, **overrides)

    assert result["_status"] == status
    assert result["code"] == code


def test_register_rejects_a_repeated_email(api: TestClient) -> None:
    _register(api)

    result = _register(api, email="ANA@example.com")

    assert result["_status"] == 409
    assert result["code"] == "EMAIL_ALREADY_REGISTERED"


def test_login_and_read_my_data(api: TestClient) -> None:
    _register(api)
    tokens = _login(api, email="ANA@EXAMPLE.COM")

    assert tokens["_status"] == 200
    assert tokens["token_type"] == "bearer"
    assert tokens["expires_in"] == 15 * 60
    me = api.get(f"{API_V1_PREFIX}/me", headers=_bearer(tokens["access_token"]))
    assert me.status_code == 200
    assert me.json()["email"] == EMAIL


@pytest.mark.parametrize(
    ("email", "password"), [(EMAIL, "otra frase de paso"), ("nadie@example.com", PASSWORD)]
)
def test_login_failures_look_the_same(api: TestClient, email: str, password: str) -> None:
    _register(api)

    result = _login(api, email=email, password=password)

    assert result["_status"] == 401
    assert result["code"] == "INVALID_CREDENTIALS"


@pytest.mark.parametrize(
    "headers", [{}, {"Authorization": "Bearer basura"}, {"Authorization": "Basic abc"}]
)
def test_my_data_requires_a_valid_token(api: TestClient, headers: dict[str, str]) -> None:
    response = api.get(f"{API_V1_PREFIX}/me", headers=headers)

    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"


def test_refresh_rotates_and_detects_reuse(api: TestClient, conn: Connection) -> None:
    _register(api)
    first = _login(api)["refresh_token"]

    rotated = api.post(f"{API_V1_PREFIX}/auth/refresh", json={"refresh_token": first})
    reused = api.post(f"{API_V1_PREFIX}/auth/refresh", json={"refresh_token": first})

    assert rotated.status_code == 200
    assert reused.status_code == 401
    assert reused.json()["code"] == "INVALID_REFRESH_TOKEN"
    # La reutilización revoca también el token nuevo de esa sesión.
    second = rotated.json()["refresh_token"]
    after = api.post(f"{API_V1_PREFIX}/auth/refresh", json={"refresh_token": second})
    assert after.status_code == 401
    active = conn.execute(text("SELECT count(*) FROM token_refresco WHERE NOT revocado"))
    assert active.scalar_one() == 0


def test_logout_closes_the_session(api: TestClient) -> None:
    _register(api)
    token = _login(api)["refresh_token"]

    first = api.post(f"{API_V1_PREFIX}/auth/logout", json={"refresh_token": token})
    again = api.post(f"{API_V1_PREFIX}/auth/logout", json={"refresh_token": token})
    refreshed = api.post(f"{API_V1_PREFIX}/auth/refresh", json={"refresh_token": token})

    assert (first.status_code, again.status_code) == (204, 204)
    assert refreshed.status_code == 401


def test_admin_routes_check_the_role_on_the_server(api: TestClient, conn: Connection) -> None:
    _register(api)
    _register(api, email="admin@example.com")
    conn.execute(
        text("UPDATE usuario SET rol = 'administrador' WHERE correo = 'admin@example.com'")
    )
    citizen = _login(api)["access_token"]
    admin = _login(api, email="admin@example.com")["access_token"]

    assert api.get(f"{API_V1_PREFIX}/admin/probe", headers=_bearer(citizen)).status_code == 403
    response = api.get(f"{API_V1_PREFIX}/admin/probe", headers=_bearer(admin))
    assert response.status_code == 200
    assert response.json() == {"rol": "administrador"}


def test_deactivated_user_loses_access_immediately(api: TestClient, conn: Connection) -> None:
    _register(api)
    access = _login(api)["access_token"]
    conn.execute(text("UPDATE usuario SET activo = false WHERE correo = :e"), {"e": EMAIL})

    response = api.get(f"{API_V1_PREFIX}/me", headers=_bearer(access))

    assert response.status_code == 401


def test_create_admin_command_creates_an_administrator(session: Session, conn: Connection) -> None:
    user = CreateAdmin(SqlUserRepository(session), Argon2PasswordHasher(), session).execute(
        " Secretaría ", "Admin@Example.com", PASSWORD
    )

    row = conn.execute(
        text("SELECT rol::text, correo FROM usuario WHERE id_usuario = :id"), {"id": user.id}
    ).one()
    assert tuple(row) == ("administrador", "admin@example.com")
