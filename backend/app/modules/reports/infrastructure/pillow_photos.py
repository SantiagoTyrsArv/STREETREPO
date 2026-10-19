import io

from PIL import Image, ImageOps, UnidentifiedImageError

from app.modules.reports.domain.photos import (
    ALLOWED_PHOTO_FORMATS,
    MAX_PHOTO_PIXELS,
    PHOTO_JPEG_QUALITY,
    PHOTO_MAX_SIDE_PX,
    THUMBNAIL_MAX_SIDE_PX,
    InvalidPhotoError,
    ProcessedPhoto,
    UnsupportedPhotoTypeError,
)

_WHITE = (255, 255, 255)


def _to_rgb(image: Image.Image) -> Image.Image:
    """JPEG no admite transparencia: se compone sobre blanco en lugar de dejarla negra."""
    if image.mode in {"RGBA", "LA"} or (image.mode == "P" and "transparency" in image.info):
        rgba = image.convert("RGBA")
        background = Image.new("RGB", rgba.size, _WHITE)
        background.paste(rgba, mask=rgba.getchannel("A"))
        return background
    return image.convert("RGB")


def _encode_jpeg(image: Image.Image, max_side: int) -> bytes:
    resized = image.copy()
    resized.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)
    buffer = io.BytesIO()
    # Sin exif ni icc_profile: el archivo nuevo no lleva metadatos del original.
    resized.save(buffer, format="JPEG", quality=PHOTO_JPEG_QUALITY, optimize=True)
    return buffer.getvalue()


class PillowPhotoProcessor:
    """Implementa ``PhotoProcessor`` (propuesta 35).

    Identifica el formato por el contenido, revisa las dimensiones antes de
    decodificar, aplica la orientación EXIF y recodifica a JPEG sin metadatos.
    """

    def process(self, raw: bytes) -> ProcessedPhoto:
        try:
            with Image.open(io.BytesIO(raw)) as image:
                if image.format not in ALLOWED_PHOTO_FORMATS:
                    raise UnsupportedPhotoTypeError("La foto debe ser JPEG, PNG o WebP")
                # Image.open solo lee la cabecera: se revisa antes de decodificar.
                width, height = image.size
                if width * height > MAX_PHOTO_PIXELS:
                    raise InvalidPhotoError("La foto tiene demasiados píxeles")
                image.load()
                upright = ImageOps.exif_transpose(image)
                rgb = _to_rgb(upright)
        except (UnsupportedPhotoTypeError, InvalidPhotoError):
            raise
        except UnidentifiedImageError as exc:
            raise UnsupportedPhotoTypeError("La foto debe ser JPEG, PNG o WebP") from exc
        except Image.DecompressionBombError as exc:
            # Pillow la lanza al abrir cabeceras con dimensiones extremas, antes del tope propio.
            raise InvalidPhotoError("La foto tiene demasiados píxeles") from exc
        except (OSError, SyntaxError, ValueError) as exc:
            # Archivo truncado o dañado.
            raise InvalidPhotoError("No se pudo leer la foto") from exc
        return ProcessedPhoto(
            content=_encode_jpeg(rgb, PHOTO_MAX_SIDE_PX),
            thumbnail=_encode_jpeg(rgb, THUMBNAIL_MAX_SIDE_PX),
        )
