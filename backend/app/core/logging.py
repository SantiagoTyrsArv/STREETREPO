"""Logs estructurados en JSON con identificador de correlación (guía 8.5).

No registrar datos personales: solo método, ruta, estado y duración.
"""

import json
import logging
import time
import uuid
from contextvars import ContextVar
from datetime import UTC, datetime

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

CORRELATION_HEADER = "X-Request-ID"
_MAX_REQUEST_ID_LENGTH = 64

correlation_id: ContextVar[str] = ContextVar("correlation_id", default="-")


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "ts": datetime.fromtimestamp(record.created, UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": correlation_id.get(),
        }
        extra = getattr(record, "http", None)
        if extra is not None:
            payload["http"] = extra
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def configure_logging(level: str) -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level.upper())
    # uvicorn trae su propio access log en texto; lo sustituye RequestLoggingMiddleware.
    logging.getLogger("uvicorn.access").disabled = True


def _safe_request_id(raw: str | None) -> str:
    if raw and len(raw) <= _MAX_REQUEST_ID_LENGTH and raw.replace("-", "").isalnum():
        return raw
    return uuid.uuid4().hex


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        token = correlation_id.set(_safe_request_id(request.headers.get(CORRELATION_HEADER)))
        start = time.perf_counter()
        try:
            response = await call_next(request)
            response.headers[CORRELATION_HEADER] = correlation_id.get()
            logging.getLogger("app.http").info(
                "request",
                extra={
                    "http": {
                        "method": request.method,
                        "path": request.url.path,
                        "status": response.status_code,
                        "duration_ms": round((time.perf_counter() - start) * 1000, 1),
                    }
                },
            )
            return response
        finally:
            correlation_id.reset(token)
