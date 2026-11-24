"""Cuentas de la prueba de carga (fase 8, tarea 7) contra PostGIS real.

Se crean con ``loadtest-accounts --count N`` y se borran enteras, con sus reportes, avisos y
fotos, con ``loadtest-accounts --remove``. Solo viven en ``@carga.example.com``.
"""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Connection, text
from sqlalchemy.orm import Session

from app.cli import _build_loadtest_accounts
from app.core.config import Environment, Settings
from app.main import API_V1_PREFIX
from app.modules.admin.application.loadtest_accounts import LoadTestAccounts
from app.modules.admin.domain.loadtest import LOADTEST_EMAIL_DOMAIN
from tests.conftest import TEST_JWT_SECRET
from tests.images import jpeg_with_metadata
from tests.integration.conftest import (
    TEST_REPORT_AREA,
    bearer,
    insert_report,
    insert_user,
    login_user,
    requires_db,
)

pytestmark = [pytest.mark.integration, requires_db]

LOAD_PASSWORD = "clave-de-carga-1234"
LON, LAT = -80.0, 0.0
LOAD_USERS = "SELECT count(*) FROM usuario WHERE correo LIKE '%@carga.example.com'"


def _accounts(session: Session, photo_dir: Path) -> LoadTestAccounts:
    settings = Settings(
        app_env=Environment.TEST,
        jwt_secret_key=TEST_JWT_SECRET,
        photo_storage_dir=photo_dir,
        report_area_bbox=TEST_REPORT_AREA,
    )
    return _build_loadtest_accounts(session, settings)


def _count(conn: Connection, sql: str) -> int:
    count: int = conn.execute(text(sql)).scalar_one()
    return count


def test_create_makes_citizen_accounts_that_can_log_in(
    session: Session, conn: Connection, photo_dir: Path, api: TestClient
) -> None:
    emails = _accounts(session, photo_dir).create(3, LOAD_PASSWORD)

    assert emails == [f"carga-{n:03d}@{LOADTEST_EMAIL_DOMAIN}" for n in (1, 2, 3)]
    assert _count(conn, LOAD_USERS) == 3
    roles = conn.execute(
        text(
            "SELECT DISTINCT rol::text, version_politica IS NOT NULL "
            "FROM usuario WHERE correo LIKE :d"
        ),
        {"d": f"%@{LOADTEST_EMAIL_DOMAIN}"},
    ).all()
    assert roles == [("ciudadano", True)]
    login = login_user(api, emails[0], LOAD_PASSWORD)
    assert login["_status"] == 200


def test_create_is_idempotent(session: Session, conn: Connection, photo_dir: Path) -> None:
    accounts = _accounts(session, photo_dir)
    accounts.create(3, LOAD_PASSWORD)

    again = accounts.create(3, LOAD_PASSWORD)

    assert len(again) == 3
    assert _count(conn, LOAD_USERS) == 3


def test_remove_deletes_accounts_reports_warnings_and_photo_files(
    session: Session, conn: Connection, photo_dir: Path, api: TestClient
) -> None:
    accounts = _accounts(session, photo_dir)
    email = accounts.create(1, LOAD_PASSWORD)[0]
    token = login_user(api, email, LOAD_PASSWORD)["access_token"]
    # Un reporte ajeno al lado, para que el de carga registre un aviso de posible duplicado.
    insert_report(conn, insert_user(conn), LON, LAT)
    form = {"longitude": str(LON), "latitude": str(LAT), "severity": "media"}
    photo = {"photo": ("foto.jpg", jpeg_with_metadata(), "image/jpeg")}
    warned = api.post(f"{API_V1_PREFIX}/reports", data=form, files=photo, headers=bearer(token))
    assert warned.status_code == 409
    response = api.post(
        f"{API_V1_PREFIX}/reports",
        data=form | {"create_anyway": "true"},
        files={"photo": ("foto.jpg", jpeg_with_metadata(), "image/jpeg")},
        headers=bearer(token),
    )
    assert response.status_code == 201
    assert _count(conn, "SELECT count(*) FROM aviso_duplicado") == 1
    assert list(photo_dir.rglob("*.jpg"))
    assert _count(conn, "SELECT count(*) FROM token_refresco") >= 1

    removed = accounts.remove()

    assert removed == 1
    assert _count(conn, LOAD_USERS) == 0
    assert _count(conn, "SELECT count(*) FROM reporte") == 1
    assert _count(conn, "SELECT count(*) FROM aviso_duplicado") == 0
    assert list(photo_dir.rglob("*.jpg")) == []


def test_remove_twice_does_not_fail(session: Session, photo_dir: Path) -> None:
    accounts = _accounts(session, photo_dir)
    accounts.create(2, LOAD_PASSWORD)
    accounts.remove()

    assert accounts.remove() == 0


def test_remove_does_not_touch_other_users(
    session: Session, conn: Connection, photo_dir: Path
) -> None:
    other = insert_user(conn, "persona@example.test")
    insert_report(conn, other, LON, LAT)
    accounts = _accounts(session, photo_dir)
    accounts.create(2, LOAD_PASSWORD)

    accounts.remove()

    assert _count(conn, "SELECT count(*) FROM usuario WHERE correo = 'persona@example.test'") == 1
    assert _count(conn, "SELECT count(*) FROM reporte") == 1


def test_count_must_be_positive(session: Session, photo_dir: Path) -> None:
    accounts = _accounts(session, photo_dir)

    with pytest.raises(ValueError, match="count"):
        accounts.create(0, LOAD_PASSWORD)
