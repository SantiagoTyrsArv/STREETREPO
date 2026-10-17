"""Derechos del titular por HTTP contra PostGIS real: actualizar y suprimir (Ley 1581)."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Connection, text

from app.main import API_V1_PREFIX
from tests.integration.conftest import (
    EMAIL,
    PASSWORD,
    bearer,
    insert_report,
    login_user,
    register_user,
    requires_db,
)

pytestmark = [pytest.mark.integration, requires_db]

ME = f"{API_V1_PREFIX}/me"
DELETION = f"{ME}/data-deletion-requests"


def _session(api: TestClient) -> dict[str, object]:
    register_user(api)
    return login_user(api)


def test_update_my_name(api: TestClient) -> None:
    token = _session(api)["access_token"]

    response = api.patch(ME, json={"name": "  Ana María  "}, headers=bearer(token))

    assert response.status_code == 200
    assert response.json()["name"] == "Ana María"
    assert api.get(ME, headers=bearer(token)).json()["name"] == "Ana María"


@pytest.mark.parametrize(
    ("password", "status", "code"),
    [
        (None, 422, "PASSWORD_CONFIRMATION_REQUIRED"),
        ("otra frase de paso", 403, "PASSWORD_CONFIRMATION_FAILED"),
    ],
)
def test_changing_the_email_needs_the_current_password(
    api: TestClient, password: str | None, status: int, code: str
) -> None:
    token = _session(api)["access_token"]
    body = {"email": "nueva@example.com"} | ({"current_password": password} if password else {})

    response = api.patch(ME, json=body, headers=bearer(token))

    assert response.status_code == status
    assert response.json()["code"] == code
    assert response.json()["details"]["field"] == "current_password"


def test_change_email_and_log_in_with_it(api: TestClient) -> None:
    token = _session(api)["access_token"]

    response = api.patch(
        ME,
        json={"email": "Nueva@Example.com", "current_password": PASSWORD},
        headers=bearer(token),
    )

    assert response.status_code == 200
    assert response.json()["email"] == "nueva@example.com"
    assert login_user(api, email="nueva@example.com")["_status"] == 200
    assert login_user(api, email=EMAIL)["_status"] == 401


def test_cannot_take_the_email_of_another_account(api: TestClient) -> None:
    register_user(api, email="otra@example.com")
    token = _session(api)["access_token"]

    response = api.patch(
        ME,
        json={"email": "otra@example.com", "current_password": PASSWORD},
        headers=bearer(token),
    )

    assert response.status_code == 409
    assert response.json()["code"] == "EMAIL_ALREADY_REGISTERED"


def test_update_rejects_unknown_fields(api: TestClient) -> None:
    token = _session(api)["access_token"]

    response = api.patch(ME, json={"role": "administrador"}, headers=bearer(token))

    assert response.status_code == 422


def test_data_deletion_anonymizes_the_titular_and_keeps_the_reports(
    api: TestClient, conn: Connection
) -> None:
    tokens = _session(api)
    user_id = conn.execute(
        text("SELECT id_usuario FROM usuario WHERE correo = :email"), {"email": EMAIL}
    ).scalar_one()
    report_id = insert_report(conn, user_id, lon=-77.28, lat=1.21)
    conn.execute(
        text("UPDATE reporte SET descripcion = :texto WHERE id_reporte = :id"),
        {"texto": "Frente a la casa de Ana Pérez", "id": report_id},
    )

    response = api.post(
        DELETION, json={"current_password": PASSWORD}, headers=bearer(tokens["access_token"])
    )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "atendida"
    assert body["attended_at"] == body["requested_at"]
    user = conn.execute(
        text("SELECT nombre, correo, password_hash, activo FROM usuario WHERE id_usuario = :id"),
        {"id": user_id},
    ).one()
    assert user.nombre == "Titular suprimido"
    assert user.correo == f"suprimido-{user_id.hex}@anonimo.invalid"
    assert not user.activo
    assert PASSWORD not in user.password_hash
    report = conn.execute(
        text("SELECT descripcion, severidad FROM reporte WHERE id_reporte = :id"),
        {"id": report_id},
    ).one()
    assert report.descripcion is None
    assert report.severidad == 2
    active_sessions = conn.execute(
        text("SELECT count(*) FROM token_refresco WHERE id_usuario = :id AND NOT revocado"),
        {"id": user_id},
    ).scalar_one()
    assert active_sessions == 0
    request = conn.execute(
        text("SELECT estado, fecha_atencion FROM solicitud_supresion WHERE id_usuario = :id"),
        {"id": user_id},
    ).one()
    assert request.estado == "atendida"
    assert request.fecha_atencion is not None


def test_after_deletion_the_account_is_unusable(api: TestClient) -> None:
    tokens = _session(api)
    api.post(DELETION, json={"current_password": PASSWORD}, headers=bearer(tokens["access_token"]))

    me = api.get(ME, headers=bearer(tokens["access_token"]))
    refreshed = api.post(
        f"{API_V1_PREFIX}/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )

    assert me.status_code == 401
    assert refreshed.status_code == 401
    assert login_user(api)["_status"] == 401
    # El correo queda libre: la persona puede volver a registrarse si quiere.
    assert register_user(api)["_status"] == 201


def test_data_deletion_with_a_wrong_password_changes_nothing(
    api: TestClient, conn: Connection
) -> None:
    token = _session(api)["access_token"]

    response = api.post(
        DELETION, json={"current_password": "otra frase de paso"}, headers=bearer(token)
    )

    assert response.status_code == 403
    assert api.get(ME, headers=bearer(token)).json()["email"] == EMAIL
    assert conn.execute(text("SELECT count(*) FROM solicitud_supresion")).scalar_one() == 0


def test_data_deletion_requires_a_session(api: TestClient) -> None:
    response = api.post(DELETION, json={"current_password": PASSWORD})

    assert response.status_code == 401


def test_guessing_the_password_with_a_stolen_token_locks_the_account(api: TestClient) -> None:
    token = _session(api)["access_token"]
    wrong = {"current_password": "otra frase de paso"}
    failures = [api.post(DELETION, json=wrong, headers=bearer(token)).status_code for _ in range(5)]

    locked = api.post(DELETION, json={"current_password": PASSWORD}, headers=bearer(token))

    assert failures == [403] * 5
    assert locked.status_code == 429
    assert locked.json()["code"] == "TOO_MANY_LOGIN_ATTEMPTS"
    # El bloqueo es el mismo del inicio de sesión.
    assert login_user(api)["_status"] == 429
