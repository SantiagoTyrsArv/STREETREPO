"""Flujo de autenticación por HTTP contra PostGIS real (HU-10, HU-11).

La sesión de la API se sustituye por la sesión de prueba (transacción que se
revierte al terminar), así que ningún usuario queda en la base.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Connection, text
from sqlalchemy.orm import Session

from app.main import API_V1_PREFIX
from app.modules.auth.application.create_admin import CreateAdmin
from app.modules.auth.infrastructure.passwords import Argon2PasswordHasher
from app.modules.users.infrastructure.repository import SqlUserRepository
from tests.integration.conftest import (
    EMAIL,
    PASSWORD,
    bearer,
    login_user,
    register_user,
    requires_db,
)

pytestmark = [pytest.mark.integration, requires_db]


def test_register_stores_consent_and_a_hashed_password(api: TestClient, conn: Connection) -> None:
    created = register_user(api, email=" Ana@Example.COM ")

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
    result = register_user(api, **overrides)

    assert result["_status"] == status
    assert result["code"] == code


def test_register_rejects_a_repeated_email(api: TestClient) -> None:
    register_user(api)

    result = register_user(api, email="ANA@example.com")

    assert result["_status"] == 409
    assert result["code"] == "EMAIL_ALREADY_REGISTERED"


def test_login_and_read_my_data(api: TestClient) -> None:
    register_user(api)
    tokens = login_user(api, email="ANA@EXAMPLE.COM")

    assert tokens["_status"] == 200
    assert tokens["token_type"] == "bearer"
    assert tokens["expires_in"] == 15 * 60
    me = api.get(f"{API_V1_PREFIX}/me", headers=bearer(tokens["access_token"]))
    assert me.status_code == 200
    assert me.json()["email"] == EMAIL


@pytest.mark.parametrize(
    ("email", "password"), [(EMAIL, "otra frase de paso"), ("nadie@example.com", PASSWORD)]
)
def test_login_failures_look_the_same(api: TestClient, email: str, password: str) -> None:
    register_user(api)

    result = login_user(api, email=email, password=password)

    assert result["_status"] == 401
    assert result["code"] == "INVALID_CREDENTIALS"


def test_login_locks_the_email_after_repeated_failures(api: TestClient) -> None:
    register_user(api)
    failures = [login_user(api, password="otra frase de paso")["_status"] for _ in range(5)]

    locked = api.post(f"{API_V1_PREFIX}/auth/login", json={"email": EMAIL, "password": PASSWORD})

    assert failures == [401] * 5
    assert locked.status_code == 429
    assert locked.json()["code"] == "TOO_MANY_LOGIN_ATTEMPTS"
    assert 0 < int(locked.headers["Retry-After"]) <= 60


@pytest.mark.parametrize(
    "headers", [{}, {"Authorization": "Bearer basura"}, {"Authorization": "Basic abc"}]
)
def test_my_data_requires_a_valid_token(api: TestClient, headers: dict[str, str]) -> None:
    response = api.get(f"{API_V1_PREFIX}/me", headers=headers)

    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"


def test_refresh_rotates_and_detects_reuse(api: TestClient, conn: Connection) -> None:
    register_user(api)
    first = login_user(api)["refresh_token"]

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
    register_user(api)
    token = login_user(api)["refresh_token"]

    first = api.post(f"{API_V1_PREFIX}/auth/logout", json={"refresh_token": token})
    again = api.post(f"{API_V1_PREFIX}/auth/logout", json={"refresh_token": token})
    refreshed = api.post(f"{API_V1_PREFIX}/auth/refresh", json={"refresh_token": token})

    assert (first.status_code, again.status_code) == (204, 204)
    assert refreshed.status_code == 401


def test_admin_routes_check_the_role_on_the_server(api: TestClient, conn: Connection) -> None:
    register_user(api)
    register_user(api, email="admin@example.com")
    conn.execute(
        text("UPDATE usuario SET rol = 'administrador' WHERE correo = 'admin@example.com'")
    )
    citizen = login_user(api)["access_token"]
    admin = login_user(api, email="admin@example.com")["access_token"]

    assert api.get(f"{API_V1_PREFIX}/admin/probe", headers=bearer(citizen)).status_code == 403
    response = api.get(f"{API_V1_PREFIX}/admin/probe", headers=bearer(admin))
    assert response.status_code == 200
    assert response.json() == {"rol": "administrador"}


def test_deactivated_user_loses_access_immediately(api: TestClient, conn: Connection) -> None:
    register_user(api)
    access = login_user(api)["access_token"]
    conn.execute(text("UPDATE usuario SET activo = false WHERE correo = :e"), {"e": EMAIL})

    response = api.get(f"{API_V1_PREFIX}/me", headers=bearer(access))

    assert response.status_code == 401


def test_create_admin_command_creates_an_administrator(session: Session, conn: Connection) -> None:
    user = CreateAdmin(SqlUserRepository(session), Argon2PasswordHasher(), session).execute(
        " Secretaría ", "Admin@Example.com", PASSWORD
    )

    row = conn.execute(
        text("SELECT rol::text, correo FROM usuario WHERE id_usuario = :id"), {"id": user.id}
    ).one()
    assert tuple(row) == ("administrador", "admin@example.com")
