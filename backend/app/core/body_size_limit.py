"""Rechazo de peticiones demasiado grandes antes de leer el cuerpo (decisión 46d).

FastAPI lee el formulario completo antes de llamar a la ruta y a sus dependencias, así que
una foto de 50 MB se recibiría entera para después rechazarla. Este middleware ASGI mira la
cabecera ``Content-Length`` y responde 413 sin leer nada. Las peticiones sin esa cabecera
(cuerpo por trozos) las limita el proxy inverso del despliegue (HU-17).
"""

import json
from typing import Final

from starlette.types import ASGIApp, Receive, Scope, Send

from app.core.errors import error_body
from app.modules.reports.domain.photos import MAX_PHOTO_BYTES

# Margen para los demás campos del formulario (ubicación, severidad, descripción de hasta
# 500 caracteres) y los separadores multipart.
MULTIPART_OVERHEAD_BYTES: Final = 64 * 1024
REPORT_REQUEST_MAX_BYTES: Final = MAX_PHOTO_BYTES + MULTIPART_OVERHEAD_BYTES


class BodySizeLimitMiddleware:
    """Limita ``POST create_report_path`` a ``REPORT_REQUEST_MAX_BYTES``."""

    def __init__(self, app: ASGIApp, *, create_report_path: str) -> None:
        self._app = app
        self._create_report_path = create_report_path

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if (
            scope["type"] != "http"
            or scope["method"] != "POST"
            or scope["path"] != self._create_report_path
        ):
            await self._app(scope, receive, send)
            return
        declared = dict(scope["headers"]).get(b"content-length")
        if declared is not None:
            try:
                size = int(declared)
            except ValueError:
                await _reply(send, 400, "INVALID_CONTENT_LENGTH", "La petición no es válida.", {})
                return
            if size > REPORT_REQUEST_MAX_BYTES:
                await _reply(
                    send,
                    413,
                    "PHOTO_TOO_LARGE",
                    "La foto es demasiado grande. El máximo es 10 MB.",
                    {"field": "photo", "max_bytes": MAX_PHOTO_BYTES},
                )
                return
        await self._app(scope, receive, send)


async def _reply(
    send: Send, status_code: int, code: str, message: str, details: dict[str, object]
) -> None:
    body = json.dumps(error_body(code, message, details)).encode()
    await send(
        {
            "type": "http.response.start",
            "status": status_code,
            "headers": [
                (b"content-type", b"application/json"),
                (b"content-length", str(len(body)).encode()),
                # El cliente no terminó de enviar el cuerpo: se cierra la conexión.
                (b"connection", b"close"),
            ],
        }
    )
    await send({"type": "http.response.body", "body": body})
