import uuid

from pydantic import BaseModel, ConfigDict, Field


class ConfirmationRequest(BaseModel):
    """Dónde está quien confirma: debe estar a 50 m o menos del daño (propuesta 112)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    longitude: float = Field(ge=-180, le=180)
    latitude: float = Field(ge=-90, le=90)
    # Aviso de «Posible duplicado» desde el que se confirma (objetivo 4); opcional.
    duplicate_warning_id: uuid.UUID | None = None


class ConfirmationResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_id: uuid.UUID
    # Total de confirmaciones del reporte tras esta.
    confirmations: int
