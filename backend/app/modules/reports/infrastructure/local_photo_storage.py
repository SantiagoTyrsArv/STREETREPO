import os
import tempfile
from collections.abc import Sequence
from datetime import datetime
from pathlib import Path


class InvalidPhotoKeyError(ValueError):
    """La clave saldría de la carpeta de fotos."""


class LocalPhotoStorage:
    """Implementa ``PhotoStorage`` y ``PhotoInventory`` en disco (propuesta 34).

    En Docker, la carpeta es un volumen propio.

    Las claves son relativas a ``root``; pasar a almacenamiento de objetos solo exige
    otro adaptador con el mismo puerto.
    """

    def __init__(self, root: Path) -> None:
        self._root = root.resolve()

    def _path(self, key: str) -> Path:
        path = (self._root / key).resolve()
        # Las claves las genera el sistema, pero se verifica igual (defensa en profundidad).
        if not path.is_relative_to(self._root) or path == self._root:
            raise InvalidPhotoKeyError(f"Clave de foto no válida: {key!r}")
        return path

    def save(self, key: str, content: bytes) -> None:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        # Escritura atómica: nadie lee un archivo a medio escribir.
        descriptor, temporary = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
        try:
            with os.fdopen(descriptor, "wb") as file:
                file.write(content)
            Path(temporary).replace(path)
        except BaseException:
            Path(temporary).unlink(missing_ok=True)
            raise

    def delete(self, key: str) -> None:
        self._path(key).unlink(missing_ok=True)

    def exists(self, key: str) -> bool:
        return self._path(key).is_file()

    def list_keys(self, *, modified_before: datetime) -> Sequence[str]:
        if not self._root.is_dir():
            return []
        cutoff = modified_before.timestamp()
        return sorted(
            path.relative_to(self._root).as_posix()
            for path in self._root.rglob("*.jpg")
            if path.is_file() and path.stat().st_mtime < cutoff
        )
