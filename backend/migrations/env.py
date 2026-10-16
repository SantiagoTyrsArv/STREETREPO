"""Entorno de Alembic: usa la configuración y los metadatos de la aplicación."""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool, text

import app.models  # noqa: F401  - registra los modelos en Base.metadata
from app.core.config import get_settings
from app.core.database import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

config.set_main_option("sqlalchemy.url", get_settings().database_url.replace("%", "%%"))
target_metadata = Base.metadata

# Tablas que crea la extensión PostGIS; no son parte del esquema de la aplicación.
_POSTGIS_TABLES = {"spatial_ref_sys"}


def include_object(_obj: object, name: str | None, type_: str, *_: object) -> bool:
    return not (type_ == "table" and name in _POSTGIS_TABLES)


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        include_object=include_object,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        # La imagen postgis/postgis instala tiger y topology en el search_path;
        # se limita a public para que autogenerate no las tome como propias.
        connection.execute(text("SET search_path TO public"))
        connection.commit()
        context.configure(
            connection=connection, target_metadata=target_metadata, include_object=include_object
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
