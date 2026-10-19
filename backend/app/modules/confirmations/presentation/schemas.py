import uuid

from pydantic import BaseModel, ConfigDict


class ConfirmationResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_id: uuid.UUID
    # Total de confirmaciones del reporte tras esta.
    confirmations: int
