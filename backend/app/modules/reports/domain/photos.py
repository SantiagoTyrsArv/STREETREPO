"""Reglas de la foto de evidencia (guía 7.2 y 11, propuestas 34 y 35).

La foto se recodifica siempre en el servidor: lo que se guarda nunca es el
archivo que envió el cliente, así que no conserva EXIF, GPS ni datos del dispositivo.
"""

import uuid
from dataclasses import dataclass
from typing import Final

MAX_PHOTO_BYTES: Final = 10 * 1024 * 1024
# Tope de píxeles antes de decodificar, contra las bombas de descompresión: una
# imagen de pocos KB puede declarar dimensiones que agoten la memoria. 50 MP cubre
# las cámaras de los celulares actuales.
MAX_PHOTO_PIXELS: Final = 50_000_000
# Formatos aceptados según el contenido decodificado, nunca según la extensión.
ALLOWED_PHOTO_FORMATS: Final = frozenset({"JPEG", "PNG", "WEBP"})

PHOTO_MAX_SIDE_PX: Final = 1600
PHOTO_JPEG_QUALITY: Final = 85
THUMBNAIL_MAX_SIDE_PX: Final = 400

STORED_PHOTO_FORMAT: Final = "jpg"


class PhotoTooLargeError(ValueError):
    """La foto supera ``MAX_PHOTO_BYTES``."""


class UnsupportedPhotoTypeError(ValueError):
    """El contenido no es JPEG, PNG ni WebP."""


class InvalidPhotoError(ValueError):
    """La imagen está dañada o declara más píxeles de los permitidos."""


@dataclass(frozen=True, slots=True)
class ProcessedPhoto:
    """Foto recodificada a JPEG, sin metadatos, y su miniatura."""

    content: bytes
    thumbnail: bytes


@dataclass(frozen=True, slots=True)
class PhotoKeys:
    """Claves relativas en el almacenamiento; ``evidencia.url_foto`` guarda ``photo``."""

    photo: str
    thumbnail: str

    @classmethod
    def new(cls) -> "PhotoKeys":
        # Nombre aleatorio: no revela el reporte ni el usuario, y no se puede adivinar.
        # Las dos primeras letras reparten los archivos en subcarpetas.
        name = uuid.uuid4().hex
        return cls.for_name(name)

    @classmethod
    def for_name(cls, name: str) -> "PhotoKeys":
        folder = name[:2]
        return cls(
            photo=f"{folder}/{name}.{STORED_PHOTO_FORMAT}",
            thumbnail=f"{folder}/{name}_min.{STORED_PHOTO_FORMAT}",
        )

    @classmethod
    def from_photo_key(cls, photo_key: str) -> "PhotoKeys":
        """Claves de una foto ya guardada (la miniatura sigue la misma convención)."""
        name = photo_key.rsplit("/", 1)[-1].removesuffix(f".{STORED_PHOTO_FORMAT}")
        return cls.for_name(name)


@dataclass(frozen=True, slots=True)
class StoredEvidence:
    """Fila de ``evidencia`` para una foto ya guardada."""

    photo_key: str
    file_format: str
    size_bytes: int
