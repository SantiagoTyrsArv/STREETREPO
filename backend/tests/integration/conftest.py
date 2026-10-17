import uuid
from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import Connection, text
from sqlalchemy.orm import Session

from app.core.config import Environment, Settings, get_settings
from app.core.database import get_engine, get_session
from app.main import API_V1_PREFIX, create_app
from app.modules.auth.presentation.dependencies import AdminUserDep
from tests.conftest import TEST_JWT_SECRET

# osm_id de prueba en un rango que OSM no usa (los ids reales no llegan a 2.000 millones):
# no chocan con los datos reales de Pasto cargados en la base de desarrollo.
TEST_OSM_ID = 9_000_000_000

BACKEND_DIR = Path(__file__).resolve().parents[2]
TEST_DATABASE_SUFFIX = "_test"


def is_test_database() -> bool:
    # Protección: algunas pruebas borran tablas (downgrade de migraciones). Nunca deben
    # correr contra la base de desarrollo ni de producción.
    return get_settings().postgres_db.endswith(TEST_DATABASE_SUFFIX)


requires_db = pytest.mark.skipif(
    not is_test_database(),
    reason="Requiere POSTGRES_DB terminada en _test (p. ej. streetrepo_test) con PostGIS",
)


def alembic_config() -> Config:
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_DIR / "migrations"))
    return config


@pytest.fixture(scope="session", autouse=True)
def migrated_test_database() -> None:
    """Deja la base de pruebas en la última migración antes de la primera prueba."""
    if is_test_database():
        command.upgrade(alembic_config(), "head")


@pytest.fixture
def conn() -> Iterator[Connection]:
    """Conexión en una transacción que se revierte al terminar: cada prueba deja la base intacta."""
    with get_engine().connect() as connection:
        transaction = connection.begin()
        try:
            yield connection
        finally:
            transaction.rollback()


@pytest.fixture
def session(conn: Connection) -> Iterator[Session]:
    """Sesión ORM dentro de la transacción de prueba; sus commit se vuelven savepoints."""
    with Session(bind=conn, join_transaction_mode="create_savepoint") as orm_session:
        yield orm_session


def insert_user(conn: Connection, email: str = "ciudadano@example.test") -> uuid.UUID:
    return conn.execute(
        text(
            "INSERT INTO usuario (nombre, correo, password_hash) "
            "VALUES ('Prueba', :email, 'hash') RETURNING id_usuario"
        ),
        {"email": email},
    ).scalar_one()


def insert_report(conn: Connection, user_id: uuid.UUID, lon: float, lat: float) -> uuid.UUID:
    return conn.execute(
        text(
            "INSERT INTO reporte (id_usuario, ubicacion, severidad) "
            "VALUES (:user_id, ST_SetSRID(ST_MakePoint(:lon, :lat), 4326), 2) "
            "RETURNING id_reporte"
        ),
        {"user_id": user_id, "lon": lon, "lat": lat},
    ).scalar_one()


# --- API por HTTP con la sesión de prueba -------------------------------------

PASSWORD = "una frase de paso larga"
EMAIL = "ana@example.com"


def app_with_admin_probe() -> FastAPI:
    app = create_app(Settings(app_env=Environment.TEST, jwt_secret_key=TEST_JWT_SECRET))
    probe = APIRouter()

    @probe.get("/admin/probe")
    def admin_probe(admin: AdminUserDep) -> dict[str, str]:
        return {"rol": admin.role.value}

    app.include_router(probe, prefix=API_V1_PREFIX)
    return app


@pytest.fixture
def api(session: Session) -> Iterator[TestClient]:
    app = app_with_admin_probe()

    def test_session() -> Iterator[Session]:
        yield session

    app.dependency_overrides[get_session] = test_session
    with TestClient(app) as client:
        yield client


def register_user(api: TestClient, email: str = EMAIL, **overrides: object) -> dict[str, object]:
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


def login_user(api: TestClient, email: str = EMAIL, password: str = PASSWORD) -> dict[str, object]:
    response = api.post(f"{API_V1_PREFIX}/auth/login", json={"email": email, "password": password})
    result: dict[str, object] = response.json() | {"_status": response.status_code}
    return result


def bearer(token: object) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}
