import uuid
from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import Connection, text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_engine

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
