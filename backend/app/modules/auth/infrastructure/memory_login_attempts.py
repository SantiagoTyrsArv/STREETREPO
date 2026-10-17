"""Fallos de inicio de sesión en memoria del proceso (decisión 25, ``docs/adr/0005``)."""

import threading
from collections import OrderedDict

from app.modules.auth.domain.lockout import FailedLogins

DEFAULT_MAX_KEYS = 10_000


class InMemoryLoginAttemptStore:
    """Se descartan primero las cuentas menos recientes al pasar de ``max_keys``."""

    def __init__(self, max_keys: int = DEFAULT_MAX_KEYS) -> None:
        self._max_keys = max_keys
        self._records: OrderedDict[str, FailedLogins] = OrderedDict()
        self._lock = threading.Lock()

    def get(self, key: str) -> FailedLogins | None:
        with self._lock:
            return self._records.get(key)

    def save(self, key: str, record: FailedLogins) -> None:
        with self._lock:
            self._records.pop(key, None)
            self._records[key] = record
            while len(self._records) > self._max_keys:
                self._records.popitem(last=False)

    def clear(self, key: str) -> None:
        with self._lock:
            self._records.pop(key, None)
