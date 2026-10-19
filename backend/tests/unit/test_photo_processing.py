"""Procesado de la foto con Pillow (propuesta 35) y almacenamiento en disco (propuesta 34)."""

from pathlib import Path

import pytest

from app.modules.reports.domain.photos import (
    PHOTO_MAX_SIDE_PX,
    THUMBNAIL_MAX_SIDE_PX,
    InvalidPhotoError,
    UnsupportedPhotoTypeError,
)
from app.modules.reports.infrastructure import pillow_photos
from app.modules.reports.infrastructure.local_photo_storage import (
    InvalidPhotoKeyError,
    LocalPhotoStorage,
)
from app.modules.reports.infrastructure.pillow_photos import PillowPhotoProcessor
from tests.images import (
    EXIF_GPS_IFD,
    EXIF_MAKE,
    EXIF_ORIENTATION,
    image_bytes,
    jpeg_with_metadata,
    open_image,
)

processor = PillowPhotoProcessor()


@pytest.mark.parametrize("image_format", ["JPEG", "PNG", "WEBP"])
def test_allowed_formats_are_recoded_to_jpeg(image_format: str) -> None:
    result = processor.process(image_bytes(image_format))

    assert open_image(result.content).format == "JPEG"
    assert open_image(result.thumbnail).format == "JPEG"


def test_all_metadata_is_removed() -> None:
    result = processor.process(jpeg_with_metadata())

    exif = open_image(result.content).getexif()
    assert EXIF_MAKE not in exif
    assert EXIF_ORIENTATION not in exif
    assert not exif.get_ifd(EXIF_GPS_IFD)
    assert b"TelefonoDePrueba" not in result.content


def test_exif_orientation_is_applied_before_removing_it() -> None:
    # La foto es de 64 x 48 con «girar 90°»: guardada derecha queda de 48 x 64.
    result = processor.process(jpeg_with_metadata(size=(64, 48)))

    assert open_image(result.content).size == (48, 64)


def test_large_photo_is_scaled_down_keeping_its_proportion() -> None:
    result = processor.process(image_bytes(size=(4000, 3000)))

    assert open_image(result.content).size == (PHOTO_MAX_SIDE_PX, 1200)
    assert open_image(result.thumbnail).size == (THUMBNAIL_MAX_SIDE_PX, 300)


def test_small_photo_is_not_enlarged() -> None:
    result = processor.process(image_bytes(size=(320, 240)))

    assert open_image(result.content).size == (320, 240)
    assert open_image(result.thumbnail).size == (320, 240)


def test_transparent_png_is_composed_on_white() -> None:
    result = processor.process(image_bytes("PNG", mode="RGBA", color=(0, 0, 0, 0)))

    red, green, blue = open_image(result.content).convert("RGB").getpixel((10, 10))  # type: ignore[misc]
    assert min(red, green, blue) > 240


@pytest.mark.parametrize(
    "raw",
    [
        b"esto no es una imagen",
        b"%PDF-1.7\n%\xe2\xe3\xcf\xd3",
        image_bytes("GIF"),
        image_bytes("BMP"),
    ],
    ids=["texto", "pdf", "gif", "bmp"],
)
def test_content_that_is_not_jpeg_png_or_webp_is_rejected(raw: bytes) -> None:
    with pytest.raises(UnsupportedPhotoTypeError):
        processor.process(raw)


def test_the_extension_does_not_matter_only_the_content() -> None:
    # El procesador ni siquiera recibe el nombre del archivo: un GIF llamado foto.jpg
    # es un GIF.
    with pytest.raises(UnsupportedPhotoTypeError):
        processor.process(image_bytes("GIF"))


def test_truncated_photo_is_rejected() -> None:
    raw = image_bytes(size=(400, 300))

    with pytest.raises(InvalidPhotoError):
        processor.process(raw[: len(raw) // 2])


def test_photo_with_too_many_pixels_is_rejected_before_decoding(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(pillow_photos, "MAX_PHOTO_PIXELS", 100 * 100)

    with pytest.raises(InvalidPhotoError, match="píxeles"):
        processor.process(image_bytes(size=(101, 100)))


def test_decompression_bomb_header_is_rejected() -> None:
    # Imagen de 1 bit que declara unos 182 MP: Pillow la rechaza al leer la cabecera.
    raw = image_bytes("PNG", size=(14_000, 13_000), mode="1", color=0)

    with pytest.raises(InvalidPhotoError, match="píxeles"):
        processor.process(raw)


# --- Almacenamiento en disco ----------------------------------------------------


def test_storage_saves_and_deletes(tmp_path: Path) -> None:
    storage = LocalPhotoStorage(tmp_path)

    storage.save("ab/foto.jpg", b"contenido")

    assert (tmp_path / "ab" / "foto.jpg").read_bytes() == b"contenido"
    assert storage.exists("ab/foto.jpg")
    storage.delete("ab/foto.jpg")
    assert not storage.exists("ab/foto.jpg")


def test_deleting_a_missing_photo_does_not_fail(tmp_path: Path) -> None:
    LocalPhotoStorage(tmp_path).delete("no/existe.jpg")


def test_saving_leaves_no_temporary_files(tmp_path: Path) -> None:
    LocalPhotoStorage(tmp_path).save("ab/foto.jpg", b"contenido")

    assert [path.name for path in (tmp_path / "ab").iterdir()] == ["foto.jpg"]


@pytest.mark.parametrize("key", ["../fuera.jpg", "ab/../../fuera.jpg", "", "."])
def test_keys_cannot_leave_the_photo_folder(tmp_path: Path, key: str) -> None:
    storage = LocalPhotoStorage(tmp_path / "fotos")

    with pytest.raises(InvalidPhotoKeyError):
        storage.save(key, b"x")
    assert not (tmp_path / "fuera.jpg").exists()
