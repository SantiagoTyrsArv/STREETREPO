"""Configuración centralizada leída de variables de entorno (Twelve-Factor)."""

from enum import StrEnum
from functools import lru_cache
from pathlib import Path

from pydantic import Field, HttpUrl, PostgresDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.shared.domain.geo import BoundingBox, InvalidGeometryError


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

    # Reportes (fase 5). Área de servicio: "sur,oeste,norte,este"; fuera de ella se rechaza
    # el reporte (propuesta 37). Por defecto es la misma de OSM_BBOX, que ya deja margen
    # alrededor del casco urbano: fuera de los datos cargados, F y P no tendrían sentido.
    report_area_bbox: str = "1.16,-77.33,1.25,-77.23"
    # Límite de creación de reportes (propuesta 38).
    reports_per_user_per_hour: int = Field(default=10, ge=1)
    reports_per_ip_per_hour: int = Field(default=30, ge=1)
    # Carpeta de las fotos de evidencia (propuesta 34); en Docker, un volumen propio
    # que entra en los respaldos.
    photo_storage_dir: Path = Path("storage/photos")

    # Autenticación (guía 7.1). La clave firma los JWT de acceso: aleatoria, de al menos
    # 32 caracteres y solo por variable de entorno (generar con `openssl rand -hex 32`).
    jwt_secret_key: str = Field(default="", repr=False)
    access_token_ttl_minutes: int = Field(default=15, ge=1, le=60)
    refresh_token_ttl_days: int = Field(default=7, ge=1, le=30)

    # Versión vigente de la política de tratamiento de datos (Ley 1581). El registro
    # exige que el ciudadano haya aceptado exactamente esta versión.
    privacy_policy_version: str = Field(default="1.0", min_length=1, max_length=20)
    # Dónde se publica el texto de esa versión. Opcional en dev y test; en producción la
    # API no arranca sin ella (propuesta 27).
    privacy_policy_url: HttpUrl | None = None

    @field_validator("privacy_policy_url", mode="before")
    @classmethod
    def _blank_policy_url_means_none(cls, value: object) -> object:
        # `.env.example` y Compose la dejan vacía cuando no se define.
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @field_validator("report_area_bbox")
    @classmethod
    def _valid_report_area(cls, value: str) -> str:
        # Falla al arrancar, no en el primer reporte.
        try:
            BoundingBox.parse(value)
        except InvalidGeometryError as exc:
            raise ValueError(f"REPORT_AREA_BBOX no es válida: {exc}") from exc
        return value

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
    def report_area(self) -> BoundingBox:
        return BoundingBox.parse(self.report_area_bbox)

    @property
    def is_production(self) -> bool:
        return self.app_env is Environment.PROD


@lru_cache
def get_settings() -> Settings:
    return Settings()
