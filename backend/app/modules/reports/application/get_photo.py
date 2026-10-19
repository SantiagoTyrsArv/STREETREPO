"""Caso de uso: entregar la foto de un reporte solo a quien puede verla (propuesta 34)."""

import logging
import uuid
from dataclasses import dataclass

from app.modules.reports.domain.photos import PhotoKeys, can_view_photo
from app.modules.reports.domain.ports import PhotoNotStoredError, PhotoReader, ReportPhotoLookup

logger = logging.getLogger(__name__)


class PhotoNotAvailableError(Exception):
    """No hay foto que mostrar a este usuario.

    Cubre a propósito tres casos: el reporte no existe, no tiene foto o es de otro
    ciudadano. Así la respuesta no revela si existe un reporte ajeno (IDOR, guía 7.1).
    """


@dataclass(frozen=True, slots=True)
class PhotoViewer:
    user_id: uuid.UUID
    is_admin: bool


class GetReportPhoto:
    def __init__(self, photos: ReportPhotoLookup, reader: PhotoReader) -> None:
        self._photos = photos
        self._reader = reader

    def execute(self, report_id: uuid.UUID, viewer: PhotoViewer, *, thumbnail: bool) -> bytes:
        found = self._photos.find_photo(report_id)
        if found is None or not can_view_photo(
            viewer_id=viewer.user_id, viewer_is_admin=viewer.is_admin, owner_id=found.owner_id
        ):
            raise PhotoNotAvailableError(str(report_id))
        if found.photo_key is None:
            raise PhotoNotAvailableError(str(report_id))
        keys = PhotoKeys.from_photo_key(found.photo_key)
        key = keys.thumbnail if thumbnail else keys.photo
        try:
            return self._reader.read(key)
        except PhotoNotStoredError as exc:
            # La fila existe pero el archivo no: inconsistencia que hay que revisar.
            logger.error("Falta el archivo de la foto %s", key)
            raise PhotoNotAvailableError(str(report_id)) from exc
