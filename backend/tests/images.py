"""Imágenes generadas en memoria para las pruebas de fotos."""

import io

from PIL import Image

# Etiquetas EXIF usadas en las pruebas.
EXIF_ORIENTATION = 0x0112
EXIF_MAKE = 0x010F
EXIF_GPS_IFD = 0x8825
ROTATE_90_CW = 6


def image_bytes(
    image_format: str = "JPEG",
    size: tuple[int, int] = (64, 48),
    mode: str = "RGB",
    color: object = (200, 30, 30),
    *,
    exif: Image.Exif | None = None,
) -> bytes:
    image = Image.new(mode, size, color)  # type: ignore[arg-type]
    buffer = io.BytesIO()
    options: dict[str, object] = {}
    if exif is not None:
        options["exif"] = exif
    image.save(buffer, format=image_format, **options)
    return buffer.getvalue()


def jpeg_with_metadata(size: tuple[int, int] = (64, 48)) -> bytes:
    """JPEG con marca del dispositivo, GPS y orientación «girar 90°»."""
    exif = Image.Exif()
    exif[EXIF_MAKE] = "TelefonoDePrueba"
    exif[EXIF_ORIENTATION] = ROTATE_90_CW
    exif.get_ifd(EXIF_GPS_IFD)[2] = (1.0, 12.0, 49.0)  # GPSLatitude
    return image_bytes(size=size, exif=exif)


def open_image(raw: bytes) -> Image.Image:
    return Image.open(io.BytesIO(raw))
