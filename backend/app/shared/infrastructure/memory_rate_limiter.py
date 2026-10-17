"""Límite de solicitudes en memoria del proceso (decisión 25, ``docs/adr/0005``).

Sirve mientras la API corra en un solo proceso: con varios procesos cada uno lleva
su propia cuenta y se reinicia al reiniciar la API.
"""

import threading
from collections import OrderedDict, deque
from datetime import datetime

from app.shared.application.rate_limit import RateLimit, RateLimitExceededError

DEFAULT_MAX_KEYS = 10_000


class InMemoryRateLimiter:
    """Ventana deslizante exacta: guarda la hora de cada solicitud aceptada por clave.

    Las claves se descartan de la menos usada a la más usada al pasar de ``max_keys``,
    para que una ráfaga de claves distintas no agote la memoria.
    """

    def __init__(self, max_keys: int = DEFAULT_MAX_KEYS) -> None:
        self._max_keys = max_keys
        self._hits: OrderedDict[str, deque[datetime]] = OrderedDict()
        # Las rutas síncronas de FastAPI corren en un pool de hilos.
        self._lock = threading.Lock()

    def hit(self, key: str, limit: RateLimit, now: datetime) -> None:
        with self._lock:
            hits = self._hits.pop(key, None) or deque()
            window_start = now - limit.window
            while hits and hits[0] <= window_start:
                hits.popleft()
            self._hits[key] = hits
            if len(hits) >= limit.max_requests:
                raise RateLimitExceededError(hits[0] + limit.window - now)
            hits.append(now)
            while len(self._hits) > self._max_keys:
                self._hits.popitem(last=False)
