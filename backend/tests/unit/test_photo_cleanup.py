"""Borrado de archivos de fotos con reintentos y limpieza de huérfanas (propuesta 39)."""

import os
from datetime import UTC, datetime, timedelta
from pathlib import Path

from app.modules.reports.application.photo_cleanup import (
    ORPHAN_MIN_AGE,
    RETRY_DELAYS_S,
    PhotoFileCleanup,
    PurgeOrphanPhotos,
)
from app.modules.reports.domain.photos import PhotoKeys
from app.modules.reports.infrastructure.local_photo_storage import LocalPhotoStorage

NOW = datetime(2026, 10, 19, 12, tzinfo=UTC)


class FlakyStorage:
    """Falla las primeras ``failures`` veces que se borra cada clave."""

    def __init__(self, failures: int) -> None:
        self._failures = failures
        self.attempts: dict[str, int] = {}
        self.deleted: list[str] = []

    def save(self, key: str, content: bytes) -> None:  # pragma: no cover - no se usa
        raise NotImplementedError

    def delete(self, key: str) -> None:
        self.attempts[key] = self.attempts.get(key, 0) + 1
        if self.attempts[key] <= self._failures:
            raise OSError("disco ocupado")
        self.deleted.append(key)


class FixedClock:
    def now(self) -> datetime:
        return NOW


def _cleanup(storage: object, sleeps: list[float]) -> PhotoFileCleanup:
    return PhotoFileCleanup(storage, sleep=sleeps.append)  # type: ignore[arg-type]


def test_removes_the_photo_and_its_thumbnail() -> None:
    storage = FlakyStorage(failures=0)
    keys = PhotoKeys.for_name("ab12")

    failed = _cleanup(storage, []).remove([keys.photo])

    assert failed == []
    assert storage.deleted == [keys.photo, keys.thumbnail]


def test_a_passing_failure_is_retried() -> None:
    storage = FlakyStorage(failures=1)
    sleeps: list[float] = []
    keys = PhotoKeys.for_name("ab12")

    failed = _cleanup(storage, sleeps).remove([keys.photo])

    assert failed == []
    assert storage.attempts == {keys.photo: 2, keys.thumbnail: 2}
    assert sleeps == [RETRY_DELAYS_S[0], RETRY_DELAYS_S[0]]


def test_gives_up_after_the_last_attempt_without_raising() -> None:
    storage = FlakyStorage(failures=99)
    sleeps: list[float] = []
    keys = PhotoKeys.for_name("ab12")

    failed = _cleanup(storage, sleeps).remove([keys.photo])

    assert failed == [keys.photo]
    # Se intenta también la miniatura aunque la foto haya fallado.
    assert storage.attempts == {keys.photo: 3, keys.thumbnail: 3}
    assert sleeps == [*RETRY_DELAYS_S, *RETRY_DELAYS_S]


def test_missing_files_count_as_removed(tmp_path: Path) -> None:
    storage = LocalPhotoStorage(tmp_path)

    assert _cleanup(storage, []).remove(["ab/ab12.jpg"]) == []


# --- Purga de huérfanas ------------------------------------------------------------


def _store(storage: LocalPhotoStorage, root: Path, key: str, age: timedelta) -> None:
    storage.save(key, b"jpeg")
    moment = (NOW - age).timestamp()
    os.utime(root / key, (moment, moment))


class FakeEvidence:
    def __init__(self, keys: list[str]) -> None:
        self._keys = keys

    def referenced_photo_keys(self) -> list[str]:
        return self._keys


def test_purge_removes_only_old_unreferenced_files(tmp_path: Path) -> None:
    storage = LocalPhotoStorage(tmp_path)
    old = ORPHAN_MIN_AGE + timedelta(minutes=1)
    kept, orphan, recent = (PhotoKeys.for_name(name) for name in ("aa01", "bb02", "cc03"))
    for keys in (kept, orphan):
        _store(storage, tmp_path, keys.photo, old)
        _store(storage, tmp_path, keys.thumbnail, old)
    # Puede ser de un reporte que se está creando: sus archivos van antes de confirmar.
    _store(storage, tmp_path, recent.photo, timedelta(minutes=5))

    deleted = PurgeOrphanPhotos(
        inventory=storage,
        evidence=FakeEvidence([kept.photo]),
        cleanup=PhotoFileCleanup(storage),
        clock=FixedClock(),
    ).execute()

    assert deleted == 2
    assert storage.list_keys(modified_before=NOW + timedelta(days=1)) == sorted(
        [kept.photo, kept.thumbnail, recent.photo]
    )


def test_purge_removes_a_thumbnail_left_without_its_photo(tmp_path: Path) -> None:
    storage = LocalPhotoStorage(tmp_path)
    keys = PhotoKeys.for_name("dd04")
    _store(storage, tmp_path, keys.thumbnail, ORPHAN_MIN_AGE * 2)

    deleted = PurgeOrphanPhotos(
        inventory=storage,
        evidence=FakeEvidence([]),
        cleanup=PhotoFileCleanup(storage),
        clock=FixedClock(),
    ).execute()

    assert deleted == 1


def test_listing_an_empty_or_missing_folder(tmp_path: Path) -> None:
    assert LocalPhotoStorage(tmp_path / "no-existe").list_keys(modified_before=NOW) == []


def test_listing_ignores_unfinished_temporary_files(tmp_path: Path) -> None:
    (tmp_path / "ab").mkdir()
    (tmp_path / "ab" / "x.tmp").write_bytes(b"a medio escribir")

    assert LocalPhotoStorage(tmp_path).list_keys(modified_before=NOW + timedelta(days=1)) == []
