import os
import tempfile
from pathlib import Path


class InvalidPhotoKeyError(ValueError):
    """La clave saldría de la carpeta de fotos."""


class LocalPhotoStorage:
    """Implementa ``PhotoStorage`` en disco (propuesta 34): en Docker, un volumen propio.

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
