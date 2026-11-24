"""Límite global de solicitudes por IP (decisión 30c, guía 7.3)."""

import asyncio
from datetime import UTC, datetime, timedelta

import pytest
from starlette.applications import Starlette
from starlette.responses import PlainTextResponse
from starlette.routing import Route
from starlette.testclient import TestClient
from starlette.types import Message, Receive, Scope, Send

from app.core.config import Environment, Settings
from app.core.global_rate_limit import GLOBAL_RATE_LIMIT_EXEMPT_PATHS, GlobalRateLimitMiddleware
from app.main import API_V1_PREFIX, create_app
from app.shared.application.rate_limit import RateLimit
from app.shared.infrastructure.memory_rate_limiter import InMemoryRateLimiter
from tests.conftest import PANEL_ORIGIN, TEST_JWT_SECRET

LIMIT = RateLimit(max_requests=3, window=timedelta(minutes=5))
MESSAGE = "Demasiadas solicitudes desde tu conexión. Intenta de nuevo en unos minutos."


class FakeClock:
    def __init__(self) -> None:
        self.current = datetime(2026, 11, 24, 12, 0, tzinfo=UTC)

    def now(self) -> datetime:
        return self.current


def _ok(_: object) -> PlainTextResponse:
    return PlainTextResponse("ok")


def _app(clock: FakeClock) -> Starlette:
    app = Starlette(routes=[Route("/ping", _ok), Route("/health", _ok), Route("/ready", _ok)])
    app.add_middleware(
        GlobalRateLimitMiddleware, limiter=InMemoryRateLimiter(), limit=LIMIT, clock=clock
    )
    return app


def _client(app: Starlette, host: str = "203.0.113.7") -> TestClient:
    return TestClient(app, client=(host, 50000))


def _exhaust(client: TestClient) -> None:
    for _ in range(LIMIT.max_requests):
        assert client.get("/ping").status_code == 200


def test_allows_requests_up_to_the_limit() -> None:
    client = _client(_app(FakeClock()))

    statuses = [client.get("/ping").status_code for _ in range(LIMIT.max_requests)]

    assert statuses == [200] * LIMIT.max_requests


def test_rejects_with_429_and_retry_after() -> None:
    client = _client(_app(FakeClock()))
    _exhaust(client)

    response = client.get("/ping")

    assert response.status_code == 429
    body = response.json()
    assert body["code"] == "RATE_LIMITED"
    assert body["message"] == MESSAGE
    assert body["details"]["retry_after_s"] >= 1
    assert response.headers["Retry-After"] == str(body["details"]["retry_after_s"])


@pytest.mark.parametrize("path", ["/health", "/ready"])
def test_exempt_paths_are_never_limited(path: str) -> None:
    client = _client(_app(FakeClock()))
    _exhaust(client)

    assert client.get(path).status_code == 200


def test_probes_and_docs_are_exempt_by_default() -> None:
    assert {"/health", "/ready", "/docs", "/openapi.json"} <= GLOBAL_RATE_LIMIT_EXEMPT_PATHS


def test_rejected_request_does_not_consume_quota() -> None:
    clock = FakeClock()
    client = _client(_app(clock))
    _exhaust(client)
    assert client.get("/ping").status_code == 429

    clock.current += LIMIT.window

    assert client.get("/ping").status_code == 200


def test_counts_per_client_ip() -> None:
    app = _app(FakeClock())
    _exhaust(_client(app, "203.0.113.7"))

    assert _client(app, "198.51.100.9").get("/ping").status_code == 200


def test_missing_client_uses_unknown_key() -> None:
    middleware = GlobalRateLimitMiddleware(
        _ok_asgi, limiter=InMemoryRateLimiter(), limit=LIMIT, clock=FakeClock()
    )
    statuses = [asyncio.run(_call(middleware, client=None)) for _ in range(LIMIT.max_requests + 1)]

    assert statuses == [200, 200, 200, 429]


def test_ignores_non_http_scopes() -> None:
    seen: list[str] = []

    async def inner(scope: Scope, receive: Receive, send: Send) -> None:
        seen.append(scope["type"])

    middleware = GlobalRateLimitMiddleware(
        inner,
        limiter=InMemoryRateLimiter(),
        limit=RateLimit(max_requests=1, window=timedelta(minutes=5)),
        clock=FakeClock(),
    )
    for _ in range(3):
        asyncio.run(middleware({"type": "lifespan"}, _no_receive, _no_send))

    assert seen == ["lifespan"] * 3


async def _ok_asgi(scope: Scope, receive: Receive, send: Send) -> None:
    await send({"type": "http.response.start", "status": 200, "headers": []})
    await send({"type": "http.response.body", "body": b"ok"})


async def _call(app: GlobalRateLimitMiddleware, *, client: tuple[str, int] | None) -> int:
    messages: list[Message] = []

    async def send(message: Message) -> None:
        messages.append(message)

    scope: Scope = {
        "type": "http",
        "method": "GET",
        "path": "/ping",
        "headers": [],
        "client": client,
    }
    await app(scope, _no_receive, send)
    return int(messages[0]["status"])


async def _no_receive() -> Message:
    return {"type": "http.request", "body": b""}


async def _no_send(message: Message) -> None:
    return None


# --- cableado en la aplicación -----------------------------------------------------------


def test_global_limit_applies_to_api_routes() -> None:
    settings = Settings(
        app_env=Environment.TEST,
        cors_origins=PANEL_ORIGIN,
        jwt_secret_key=TEST_JWT_SECRET,
        global_requests_per_ip=2,
    )
    client = TestClient(create_app(settings), raise_server_exceptions=False)
    url = f"{API_V1_PREFIX}/privacy-policy"
    headers = {"Origin": PANEL_ORIGIN}

    statuses = [client.get(url, headers=headers).status_code for _ in range(2)]
    blocked = client.get(url, headers=headers)

    assert statuses == [200, 200]
    assert blocked.status_code == 429
    # Pasa por CORS y por las cabeceras de seguridad como cualquier otro error.
    assert blocked.headers["access-control-allow-origin"] == PANEL_ORIGIN
    assert blocked.headers["X-Content-Type-Options"] == "nosniff"
    assert client.get("/health").status_code == 200


def test_global_limit_defaults_are_generous() -> None:
    settings = Settings()

    assert (settings.global_requests_per_ip, settings.global_window_seconds) == (600, 300)
    assert settings.login_per_ip_per_5_minutes == 30
