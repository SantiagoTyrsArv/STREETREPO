"""Sondas de vida y disponibilidad (guía 8.5)."""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app import __version__
from app.core.database import get_session
from app.core.errors import error_body

logger = logging.getLogger(__name__)

router = APIRouter(tags=["salud"])


class HealthResponse(BaseModel):
    status: str
    version: str = __version__


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """La aplicación está viva."""
    return HealthResponse(status="ok")


@router.get(
    "/ready",
    response_model=HealthResponse,
    responses={status.HTTP_503_SERVICE_UNAVAILABLE: {"description": "Base de datos no disponible"}},
)
def ready(session: Annotated[Session, Depends(get_session)]) -> HealthResponse | JSONResponse:
    """La base de datos responde y tiene PostGIS disponible."""
    try:
        session.execute(text("SELECT postgis_version()"))
    except SQLAlchemyError:
        logger.warning("Base de datos no disponible para /ready")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=error_body("DB_UNAVAILABLE", "La base de datos no está disponible."),
        )
    return HealthResponse(status="ok")
