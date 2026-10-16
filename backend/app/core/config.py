"""Configuración centralizada leída de variables de entorno (Twelve-Factor)."""

from enum import StrEnum
from functools import lru_cache

from pydantic import Field, PostgresDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(StrEnum):
    DEV = "dev"
    TEST = "test"
    PROD = "prod"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", frozen=True)

    app_env: Environment = Environment.DEV
    log_level: str = "INFO"

    postgres_db: str = "streetrepo"
    postgres_user: str = "streetrepo"
    postgres_password: str = Field(default="", repr=False)
    postgres_host: str = "localhost"
    postgres_port: int = 5432

    # Lista separada por comas; solo el origen del panel administrativo (guía 7.3).
    cors_origins: str = ""

    # Propiedad simple (no computed_field) para que la clave no aparezca en repr ni en dumps.
    @property
    def database_url(self) -> str:
        return str(
            PostgresDsn.build(
                scheme="postgresql+psycopg",
                username=self.postgres_user,
                password=self.postgres_password,
                host=self.postgres_host,
                port=self.postgres_port,
                path=self.postgres_db,
            )
        )

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def is_production(self) -> bool:
        return self.app_env is Environment.PROD


@lru_cache
def get_settings() -> Settings:
    return Settings()
