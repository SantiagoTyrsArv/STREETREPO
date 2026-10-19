"""Rutas de reportes: /api/v1/reports (HU-02, HU-05, HU-07)."""

import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, Form, Header, Response, UploadFile, status

from app.core.errors import AppError
from app.core.rate_limiting import too_many_requests
from app.modules.auth.presentation.dependencies import CurrentUserDep
from app.modules.reports.application.create_report import ReportSubmission
from app.modules.reports.domain.new_report import (
    DESCRIPTION_MAX_LENGTH,
    InvalidReportError,
    LocationOutsideServiceAreaError,
)
from app.modules.reports.domain.photos import (
    MAX_PHOTO_BYTES,
    InvalidPhotoError,
    PhotoTooLargeError,
    UnsupportedPhotoTypeError,
)
from app.modules.reports.presentation.dependencies import CreateReportDep, limit_reports_per_ip
from app.modules.reports.presentation.schemas import ReportResponse, SeverityLevel
from app.shared.application.rate_limit import RateLimitExceededError
from app.shared.domain.geo import GeoPoint

router = APIRouter(prefix="/reports", tags=["reportes"])

_CREATE_DOC: dict[int | str, dict[str, Any]] = {
    status.HTTP_200_OK: {
        "description": "Reintento con un Idempotency-Key ya usado: el reporte existente",
        "model": ReportResponse,
    },
    status.HTTP_413_CONTENT_TOO_LARGE: {"description": "La foto supera 10 MB"},
    status.HTTP_415_UNSUPPORTED_MEDIA_TYPE: {"description": "La foto no es JPEG, PNG ni WebP"},
    status.HTTP_422_UNPROCESSABLE_CONTENT: {
        "description": "Datos inválidos, foto dañada o ubicación fuera del área de servicio"
    },
    status.HTTP_429_TOO_MANY_REQUESTS: {"description": "Demasiados reportes; ver Retry-After"},
}


@contextmanager
def _create_report_errors() -> Iterator[None]:
    """Traduce los errores del dominio al formato de error de la API."""
    try:
        yield
    except LocationOutsideServiceAreaError as exc:
        raise AppError(
            "LOCATION_OUTSIDE_SERVICE_AREA",
            "La ubicación está fuera del área donde el sistema recibe reportes.",
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            {"field": "location"},
        ) from exc
    except InvalidReportError as exc:
        raise AppError("REPORT_INVALID", str(exc), status.HTTP_422_UNPROCESSABLE_CONTENT) from exc
    except PhotoTooLargeError as exc:
        raise AppError(
            "PHOTO_TOO_LARGE",
            "La foto es demasiado grande. El máximo es 10 MB.",
            status.HTTP_413_CONTENT_TOO_LARGE,
            {"field": "photo", "max_bytes": MAX_PHOTO_BYTES},
        ) from exc
    except UnsupportedPhotoTypeError as exc:
        raise AppError(
            "PHOTO_UNSUPPORTED_TYPE",
            "La foto debe ser una imagen JPEG, PNG o WebP.",
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            {"field": "photo"},
        ) from exc
    except InvalidPhotoError as exc:
        raise AppError(
            "PHOTO_INVALID",
            "No pudimos leer la foto. Toma otra e intenta de nuevo.",
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            {"field": "photo"},
        ) from exc
    except RateLimitExceededError as exc:
        raise too_many_requests(
            "REPORT_RATE_LIMITED",
            "Enviaste muchos reportes en poco tiempo. Intenta de nuevo más tarde.",
            exc.retry_after,
        ) from exc


@router.post(
    "",
    response_model=ReportResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(limit_reports_per_ip)],
    responses=_CREATE_DOC,
)
def create_report(
    *,
    user: CurrentUserDep,
    use_case: CreateReportDep,
    response: Response,
    photo: Annotated[UploadFile, File(description="Foto del daño: JPEG, PNG o WebP, hasta 10 MB")],
    longitude: Annotated[float, Form(ge=-180, le=180)],
    latitude: Annotated[float, Form(ge=-90, le=90)],
    severity: Annotated[SeverityLevel, Form()],
    description: Annotated[str | None, Form(max_length=DESCRIPTION_MAX_LENGTH)] = None,
    idempotency_key: Annotated[
        uuid.UUID | None,
        Header(
            alias="Idempotency-Key",
            description="UUID por envío; un reintento con la misma clave no duplica el reporte",
        ),
    ] = None,
) -> ReportResponse:
    """Crea un reporte con foto, ubicación y severidad, y lo evalúa de inmediato.

    La foto se recodifica sin metadatos (EXIF, GPS). El reporte queda «evaluado» con
    su urgencia U; si no hay vía OSM a 30 m, se marca para revisar la vía.
    """
    # Se lee un byte más del máximo para saber si lo supera sin cargar todo el archivo.
    raw_photo = photo.file.read(MAX_PHOTO_BYTES + 1)
    with _create_report_errors():
        result = use_case.execute(
            ReportSubmission(
                user_id=user.id,
                location=GeoPoint(longitude=longitude, latitude=latitude),
                severity=severity.to_domain(),
                description=description,
                idempotency_key=idempotency_key,
                photo=raw_photo,
            )
        )
    if not result.created:
        response.status_code = status.HTTP_200_OK
    return ReportResponse.from_details(result.report)
