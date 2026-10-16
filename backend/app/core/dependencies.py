"""Dependencias de FastAPI compartidas por los módulos."""

from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.database import get_session


def get_app_settings(request: Request) -> Settings:
    """La configuración con la que se creó la aplicación (las pruebas inyectan la suya)."""
    settings: Settings = request.app.state.settings
    return settings


SettingsDep = Annotated[Settings, Depends(get_app_settings)]
SessionDep = Annotated[Session, Depends(get_session)]
