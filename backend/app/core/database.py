"""Motor y sesiones de SQLAlchemy (infraestructura compartida)."""

from collections.abc import Iterator
from functools import lru_cache

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings


class Base(DeclarativeBase):
    """Base declarativa común para los modelos ORM de los módulos."""


@lru_cache
def get_engine() -> Engine:
    return create_engine(get_settings().database_url, pool_pre_ping=True)


@lru_cache
def _session_factory() -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(), autoflush=False, expire_on_commit=False)


def create_session() -> Session:
    """Sesión nueva para procesos fuera de una petición HTTP (CLI, tareas)."""
    return _session_factory()()


def get_session() -> Iterator[Session]:
    """Dependencia de FastAPI: una sesión por petición."""
    with create_session() as session:
        yield session
