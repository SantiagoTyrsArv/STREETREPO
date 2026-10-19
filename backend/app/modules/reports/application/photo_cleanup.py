"""Borrado de los archivos de fotos: con reintentos y limpieza de huérfanas (propuesta 39)."""

import logging
import time
from collections.abc import Callable, Sequence
from datetime import timedelta
from typing import Final

from app.modules.reports.domain.photos import PhotoKeys
from app.modules.reports.domain.ports import EvidenceKeys, PhotoInventory, PhotoStorage
from app.shared.application.clock import Clock

logger = logging.getLogger(__name__)

# Pausas entre intentos: cubren fallos pasajeros del disco sin demorar mucho la respuesta.
RETRY_DELAYS_S: Final = (0.1, 0.5)
# Una foto sin fila en ``evidencia`` y más antigua que esto es huérfana. El margen evita
# borrar la de un reporte que se está creando: sus archivos se escriben antes de confirmar.
ORPHAN_MIN_AGE: Final = timedelta(hours=1)


class PhotoFileCleanup:
    """Implementa ``PhotoFileRemover`` del módulo de usuarios."""

    def __init__(
        self,
        storage: PhotoStorage,
        *,
        retry_delays_s: Sequence[float] = RETRY_DELAYS_S,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._storage = storage
        self._retry_delays_s = tuple(retry_delays_s)
        self._sleep = sleep

    def remove(self, photo_keys: Sequence[str]) -> Sequence[str]:
        failed: list[str] = []
        for photo_key in photo_keys:
            keys = PhotoKeys.from_photo_key(photo_key)
            # Lista, no generador: si falla la foto, igual se intenta con la miniatura.
            deleted = [self.delete_file(key) for key in (keys.photo, keys.thumbnail)]
            if not all(deleted):
                failed.append(photo_key)
        if failed:
            # Solo claves aleatorias, sin datos personales (guía 7.2).
            logger.warning(
                "No se pudieron borrar %d fotos; las recoge purge-orphan-photos", len(failed)
            )
        return failed

    def delete_file(self, key: str) -> bool:
        """Borra un archivo con reintentos; ``False`` si no se pudo."""
        for delay in (*self._retry_delays_s, None):
            try:
                self._storage.delete(key)
            except OSError:
                if delay is None:
                    logger.exception("No se pudo borrar la foto %s", key)
                    return False
                self._sleep(delay)
            else:
                return True
        return False  # pragma: no cover - el bucle siempre retorna


class PurgeOrphanPhotos:
    """Borra los archivos que ninguna fila de ``evidencia`` referencia.

    Recoge lo que no se pudo borrar tras una supresión o tras una creación fallida.
    Se ejecuta con ``python -m app.cli purge-orphan-photos`` (por ejemplo, a diario).
    """

    def __init__(
        self,
        inventory: PhotoInventory,
        evidence: EvidenceKeys,
        cleanup: PhotoFileCleanup,
        clock: Clock,
    ) -> None:
        self._inventory = inventory
        self._evidence = evidence
        self._cleanup = cleanup
        self._clock = clock

    def execute(self) -> int:
        """Número de archivos huérfanos borrados."""
        stored = self._inventory.list_keys(modified_before=self._clock.now() - ORPHAN_MIN_AGE)
        referenced: set[str] = set()
        for photo_key in self._evidence.referenced_photo_keys():
            keys = PhotoKeys.from_photo_key(photo_key)
            referenced.update((keys.photo, keys.thumbnail))
        orphans = [key for key in stored if key not in referenced]
        deleted = 0
        for key in orphans:
            # Cada archivo por separado: una miniatura huérfana puede no tener su foto.
            if self._cleanup.delete_file(key):
                deleted += 1
        if deleted:
            logger.info("Se borraron %d fotos huérfanas", deleted)
        return deleted
