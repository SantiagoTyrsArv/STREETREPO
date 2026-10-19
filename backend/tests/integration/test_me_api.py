"""Derechos del titular por HTTP contra PostGIS real: actualizar y suprimir (Ley 1581)."""

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Connection, text
from sqlalchemy.orm import Session

from app.main import API_V1_PREFIX
from app.modules.reports.application.photo_cleanup import (
    ORPHAN_MIN_AGE,
    PhotoFileCleanup,
    PurgeOrphanPhotos,
)
from app.modules.reports.domain.photos import PhotoKeys
from app.modules.reports.infrastructure.evidence import SqlEvidenceKeys
from app.modules.reports.infrastructure.local_photo_storage import LocalPhotoStorage
from tests.images import image_bytes
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


def test_data_deletion_removes_the_photos_and_keeps_the_report(
    api: TestClient, conn: Connection, photo_dir: Path
) -> None:
    token = _session(api)["access_token"]
    created = api.post(
        f"{API_V1_PREFIX}/reports",
        data={"longitude": "-80.0", "latitude": "0.0", "severity": "media"},
        files={"photo": ("foto.jpg", image_bytes(), "image/jpeg")},
        headers=bearer(token),
    )
    assert created.status_code == 201
    report_id = created.json()["id"]
    assert len(list(photo_dir.rglob("*.jpg"))) == 2  # foto y miniatura

    response = api.post(DELETION, json={"current_password": PASSWORD}, headers=bearer(token))

    assert response.status_code == 201
    evidence = conn.execute(
        text("SELECT count(*) FROM evidencia WHERE id_reporte = :id"), {"id": report_id}
    ).scalar_one()
    assert evidence == 0
    assert list(photo_dir.rglob("*.jpg")) == []
    report = conn.execute(
        text("SELECT severidad, estado FROM reporte WHERE id_reporte = :id"), {"id": report_id}
    ).one()
    assert (report.severidad, report.estado) == (2, "evaluado")


def test_purge_keeps_photos_that_evidence_references(
    session: Session, conn: Connection, photo_dir: Path, api: TestClient
) -> None:
    token = _session(api)["access_token"]
    api.post(
        f"{API_V1_PREFIX}/reports",
        data={"longitude": "-80.0", "latitude": "0.0", "severity": "alta"},
        files={"photo": ("foto.jpg", image_bytes(), "image/jpeg")},
        headers=bearer(token),
    )
    storage = LocalPhotoStorage(photo_dir)
    orphan = PhotoKeys.for_name("ff99").photo
    storage.save(orphan, b"jpeg")
    later = datetime.now(UTC) + ORPHAN_MIN_AGE + timedelta(minutes=1)

    class Later:
        def now(self) -> datetime:
            return later

    deleted = PurgeOrphanPhotos(
        inventory=storage,
        evidence=SqlEvidenceKeys(session),
        cleanup=PhotoFileCleanup(storage),
        clock=Later(),
    ).execute()

    assert deleted == 1
    assert len(storage.list_keys(modified_before=later)) == 2  # las del reporte siguen
