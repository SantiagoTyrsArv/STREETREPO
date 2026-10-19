"""Punto de entrada de la API de Street Repo."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.core.config import Settings, get_settings
from app.core.errors import register_error_handlers
from app.core.health import router as health_router
from app.core.logging import CORRELATION_HEADER, RequestLoggingMiddleware, configure_logging
from app.core.security_headers import SecurityHeadersMiddleware
from app.modules.auth.infrastructure.jwt_tokens import JwtAccessTokenService
from app.modules.auth.infrastructure.memory_login_attempts import InMemoryLoginAttemptStore
from app.modules.auth.presentation.privacy_policy import router as privacy_policy_router
from app.modules.auth.presentation.router import router as auth_router
from app.modules.confirmations.presentation.router import router as confirmations_router
from app.modules.reports.presentation.me_router import router as my_reports_router
from app.modules.reports.presentation.router import router as reports_router
from app.modules.users.presentation.router import router as users_router
from app.shared.infrastructure.memory_rate_limiter import InMemoryRateLimiter

API_V1_PREFIX = "/api/v1"


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.log_level)
    if settings.is_production:
        # Falla al arrancar, no en el primer inicio de sesión, si falta la clave de los JWT.
        JwtAccessTokenService(settings.jwt_secret_key, settings.access_token_ttl_minutes)
        # La pantalla «Política de datos» debe poder mostrar el texto que se acepta (Ley 1581).
        if settings.privacy_policy_url is None:
            raise ValueError("PRIVACY_POLICY_URL es obligatoria en producción")
        # El texto que se acepta no debe poder alterarse en tránsito (guía 7.3, propuesta 33).
        if settings.privacy_policy_url.scheme != "https":
            raise ValueError("PRIVACY_POLICY_URL debe usar https en producción")

    app = FastAPI(
        title="Street Repo API",
        description="Reporte ciudadano y priorización de daños viales en Pasto, Nariño.",
        version=__version__,
        docs_url=None if settings.is_production else "/docs",
        redoc_url=None,
    )
    app.state.settings = settings
    # Contadores anti abuso en memoria de este proceso (decisión 25).
    app.state.rate_limiter = InMemoryRateLimiter()
    app.state.login_attempts = InMemoryLoginAttemptStore()

    # Starlette ejecuta primero el último middleware añadido.
    app.add_middleware(SecurityHeadersMiddleware, enable_hsts=settings.is_production)
    app.add_middleware(RequestLoggingMiddleware)
    # CORS va por fuera de todos: responde el preflight antes que nada y añade sus
    # cabeceras a toda respuesta, incluidos los errores de los demás middlewares.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["Authorization", "Content-Type", "Idempotency-Key", CORRELATION_HEADER],
        expose_headers=[CORRELATION_HEADER],
    )

    register_error_handlers(app)
    app.include_router(health_router)
    app.include_router(auth_router, prefix=API_V1_PREFIX)
    app.include_router(privacy_policy_router, prefix=API_V1_PREFIX)
    app.include_router(users_router, prefix=API_V1_PREFIX)
    app.include_router(my_reports_router, prefix=API_V1_PREFIX)
    app.include_router(reports_router, prefix=API_V1_PREFIX)
    app.include_router(confirmations_router, prefix=API_V1_PREFIX)
    return app


app = create_app()
