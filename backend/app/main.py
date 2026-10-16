"""Punto de entrada de la API de Street Repo."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import Settings, get_settings
from app.core.errors import register_error_handlers
from app.core.health import router as health_router
from app.core.logging import CORRELATION_HEADER, RequestLoggingMiddleware, configure_logging
from app.core.security_headers import SecurityHeadersMiddleware

API_V1_PREFIX = "/api/v1"


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.log_level)

    app = FastAPI(
        title="Street Repo API",
        description="Reporte ciudadano y priorización de daños viales en Pasto, Nariño.",
        version="0.1.0",
        docs_url=None if settings.is_production else "/docs",
        redoc_url=None,
    )

    app.add_middleware(SecurityHeadersMiddleware, enable_hsts=settings.is_production)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["Authorization", "Content-Type", "Idempotency-Key", CORRELATION_HEADER],
        expose_headers=[CORRELATION_HEADER],
    )
    # Se añade al final para ejecutarse primero y envolver a los demás.
    app.add_middleware(RequestLoggingMiddleware)

    register_error_handlers(app)
    app.include_router(health_router)
    return app


app = create_app()
