"""Rutas de reportes: /api/v1/reports (HU-02, HU-05, HU-07)."""

import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, Form, Header, Query, Response, UploadFile, status

from app.core.errors import AppError
from app.core.rate_limiting import too_many_requests
from app.modules.auth.presentation.dependencies import CurrentUserDep
from app.modules.reports.application.create_report import ReportSubmission
from app.modules.reports.application.get_photo import PhotoNotAvailableError, PhotoViewer
from app.modules.reports.domain.duplicates import PossibleDuplicateError
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
from app.modules.reports.domain.report_view import FullReportView, ReportNotVisibleError
from app.modules.reports.presentation.dependencies import (
    CreateReportDep,
    FindPossibleDuplicatesDep,
    GetReportDep,
    GetReportPhotoDep,
    limit_reports_per_ip,
)
from app.modules.reports.presentation.schemas import (
    ConfirmedReportDetail,
    NearbyReportsResponse,
    OwnReportDetail,
    ReportDetailResponse,
    ReportResponse,
    SeverityLevel,
)
from app.modules.users.domain.entities import User
from app.modules.users.domain.role import UserRole
from app.shared.application.rate_limit import RateLimitExceededError
from app.shared.domain.geo import GeoPoint

router = APIRouter(prefix="/reports", tags=["reportes"])

_CREATE_DOC: dict[int | str, dict[str, Any]] = {
    status.HTTP_200_OK: {
        "description": "Reintento con un Idempotency-Key ya usado: el reporte existente",
        "model": ReportResponse,
    },
    status.HTTP_409_CONFLICT: {
        "description": "Hay reportes activos a 25 m (REPORT_DUPLICATE_NEARBY); "
        "reenviar con create_anyway=true para crearlo de todos modos"
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
    except PossibleDuplicateError as exc:
        nearby = NearbyReportsResponse.from_candidates(exc.candidates)
        raise AppError(
            "REPORT_DUPLICATE_NEARBY",
            "Ya hay un reporte activo muy cerca. Puedes confirmarlo en lugar de crear otro.",
            status.HTTP_409_CONFLICT,
            nearby.model_dump(mode="json"),
        ) from exc
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
    create_anyway: Annotated[
        bool,
        Form(description="true si el ciudadano vio los posibles duplicados y decide crearlo"),
    ] = False,
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

    Si hay reportes activos a 25 m responde 409 con ellos, salvo que llegue
    ``create_anyway=true``.
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
                create_anyway=create_anyway,
            )
        )
    if not result.created:
        response.status_code = status.HTTP_200_OK
    return ReportResponse.from_details(result.report)


@contextmanager
def _nearby_errors() -> Iterator[None]:
    try:
        yield
    except LocationOutsideServiceAreaError as exc:
        raise AppError(
            "LOCATION_OUTSIDE_SERVICE_AREA",
            "La ubicación está fuera del área donde el sistema recibe reportes.",
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            {"field": "location"},
        ) from exc
    except RateLimitExceededError as exc:
        raise too_many_requests(
            "NEARBY_RATE_LIMITED",
            "Hiciste muchas consultas en poco tiempo. Intenta de nuevo más tarde.",
            exc.retry_after,
        ) from exc


@router.get(
    "/nearby",
    response_model=NearbyReportsResponse,
    responses={
        status.HTTP_422_UNPROCESSABLE_CONTENT: {
            "description": "Punto inválido o fuera del área de servicio"
        },
        status.HTTP_429_TOO_MANY_REQUESTS: {"description": "Demasiadas consultas; ver Retry-After"},
    },
)
def find_nearby_reports(
    user: CurrentUserDep,
    use_case: FindPossibleDuplicatesDep,
    longitude: Annotated[float, Query(ge=-180, le=180)],
    latitude: Annotated[float, Query(ge=-90, le=90)],
) -> NearbyReportsResponse:
    """Reportes activos a 25 m del punto, para la pantalla «Posible duplicado» (HU-15).

    No incluye el autor ni la ubicación exacta de los reportes ajenos: la ubicación va
    redondeada a 4 decimales y la distancia se mide desde ella (propuesta 43).
    """
    with _nearby_errors():
        candidates = use_case.execute(user.id, GeoPoint(longitude=longitude, latitude=latitude))
    return NearbyReportsResponse.from_candidates(candidates)


@router.get(
    "/{report_id}",
    response_model=ReportDetailResponse,
    responses={
        status.HTTP_404_NOT_FOUND: {
            "description": "El reporte no existe o el usuario no puede verlo (REPORT_NOT_FOUND)"
        }
    },
)
def get_report(
    report_id: uuid.UUID, user: CurrentUserDep, use_case: GetReportDep
) -> OwnReportDetail | ConfirmedReportDetail:
    """Detalle del reporte con su historial de estados.

    - Autor: ``relation: own``, completo. Administrador que no es el autor: ``relation:
      staff``, la misma vista completa.
    - Quien lo confirmó: ``relation: confirmed``, vista pública y observaciones en null.
    - Cualquier otro: 404, igual que si no existiera.
    """
    try:
        view = use_case.execute(report_id, _viewer(user))
    except ReportNotVisibleError as exc:
        raise AppError(
            "REPORT_NOT_FOUND", "No encontramos ese reporte.", status.HTTP_404_NOT_FOUND
        ) from exc
    if isinstance(view, FullReportView):
        return OwnReportDetail.from_full(view)
    return ConfirmedReportDetail.from_limited(view)


# La foto puede mostrar rostros o placas: ningún intermediario ni el navegador la guarda,
# para que tras una supresión no queden copias (Ley 1581).
_PHOTO_HEADERS = {"Cache-Control": "private, no-store"}
_PHOTO_DOC: dict[int | str, dict[str, Any]] = {
    status.HTTP_200_OK: {"content": {"image/jpeg": {}}, "description": "Foto en JPEG"},
    status.HTTP_404_NOT_FOUND: {
        "description": "El reporte no existe, no tiene foto o es de otro ciudadano"
    },
}


def _photo_response(
    use_case: GetReportPhotoDep, report_id: uuid.UUID, viewer: PhotoViewer, *, thumbnail: bool
) -> Response:
    try:
        content = use_case.execute(report_id, viewer, thumbnail=thumbnail)
    except PhotoNotAvailableError as exc:
        raise AppError(
            "PHOTO_NOT_FOUND", "No encontramos esa foto.", status.HTTP_404_NOT_FOUND
        ) from exc
    return Response(content=content, media_type="image/jpeg", headers=_PHOTO_HEADERS)


@router.get("/{report_id}/photo", response_class=Response, responses=_PHOTO_DOC)
def get_report_photo(
    report_id: uuid.UUID, user: CurrentUserDep, use_case: GetReportPhotoDep
) -> Response:
    """Foto del reporte (hasta 1600 px). Solo para su autor y los administradores."""
    return _photo_response(use_case, report_id, _viewer(user), thumbnail=False)


@router.get("/{report_id}/photo/thumbnail", response_class=Response, responses=_PHOTO_DOC)
def get_report_photo_thumbnail(
    report_id: uuid.UUID, user: CurrentUserDep, use_case: GetReportPhotoDep
) -> Response:
    """Miniatura de la foto (hasta 400 px), para listas y mapas. Mismo acceso que la foto."""
    return _photo_response(use_case, report_id, _viewer(user), thumbnail=True)


def _viewer(user: User) -> PhotoViewer:
    return PhotoViewer(user_id=user.id, is_admin=user.role is UserRole.ADMIN)
