"""Cabeceras de seguridad HTTP (guía 7.3)."""

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

_BASE_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "X-Frame-Options": "DENY",
    "Content-Security-Policy": "default-src 'none'; frame-ancestors 'none'",
}
# La documentación interactiva (/docs) carga recursos externos y necesita una CSP propia.
_DOCS_PATHS = ("/docs", "/redoc", "/openapi.json")
_HSTS = "max-age=31536000; includeSubDomains"


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: object, *, enable_hsts: bool) -> None:
        super().__init__(app)  # type: ignore[arg-type]
        self._enable_hsts = enable_hsts

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)
        for name, value in _BASE_HEADERS.items():
            if name == "Content-Security-Policy" and request.url.path.startswith(_DOCS_PATHS):
                continue
            response.headers.setdefault(name, value)
        if self._enable_hsts:
            response.headers.setdefault("Strict-Transport-Security", _HSTS)
        return response
