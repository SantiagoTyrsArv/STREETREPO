"""Configuración centralizada leída de variables de entorno (Twelve-Factor)."""

from enum import StrEnum
from functools import lru_cache

from pydantic import Field, PostgresDsn, field_validator
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

    # Proxies de los que uvicorn acepta X-Forwarded-For (la lee él mismo de esta variable).
    # Se valida aquí para que la API no arranque con "*": cualquiera podría falsificar su IP
    # y saltarse el límite de intentos (decisión 25, condición 2).
    forwarded_allow_ips: str = "127.0.0.1"

    # Carga OSM (guía 3.1). Área: "sur,oeste,norte,este"; por defecto, el casco urbano
    # aproximado de Pasto. Ajustar si se necesita cubrir corregimientos.
    osm_bbox: str = "1.16,-77.33,1.25,-77.23"
    overpass_url: str = "https://overpass-api.de/api/interpreter"
    osm_user_agent: str = (
        "StreetRepo/0.1 (proyecto de grado, Universidad Cooperativa de Colombia - Pasto)"
    )
    osm_timeout_s: float = 120.0

    # Autenticación (guía 7.1). La clave firma los JWT de acceso: aleatoria, de al menos
    # 32 caracteres y solo por variable de entorno (generar con `openssl rand -hex 32`).
    jwt_secret_key: str = Field(default="", repr=False)
    access_token_ttl_minutes: int = Field(default=15, ge=1, le=60)
    refresh_token_ttl_days: int = Field(default=7, ge=1, le=30)

    # Versión vigente de la política de tratamiento de datos (Ley 1581). El registro
    # exige que el ciudadano haya aceptado exactamente esta versión.
    privacy_policy_version: str = Field(default="1.0", min_length=1, max_length=20)

    @field_validator("forwarded_allow_ips")
    @classmethod
    def _reject_trusting_every_proxy(cls, value: str) -> str:
        if any(address.strip() == "*" for address in value.split(",")):
            raise ValueError("FORWARDED_ALLOW_IPS debe listar la dirección del proxy, nunca '*'")
        return value

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
