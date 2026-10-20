"""Límite de solicitudes: ventana deslizante en memoria y dependencia HTTP por IP."""

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.rate_limiting import LOGIN_LIMIT_PER_IP, retry_after_seconds
from app.main import API_V1_PREFIX
from app.shared.application.rate_limit import RateLimit, RateLimitExceededError
from app.shared.infrastructure.memory_rate_limiter import InMemoryRateLimiter

NOW = datetime(2026, 10, 16, 12, tzinfo=UTC)
THREE_PER_MINUTE = RateLimit(max_requests=3, window=timedelta(minutes=1))


@pytest.mark.parametrize(("max_requests", "window"), [(0, timedelta(minutes=1)), (1, timedelta(0))])
def test_rate_limit_rejects_invalid_values(max_requests: int, window: timedelta) -> None:
    with pytest.raises(ValueError, match="debe"):
        RateLimit(max_requests, window)


def test_limiter_allows_up_to_the_limit_and_then_rejects() -> None:
    limiter = InMemoryRateLimiter()
    for i in range(3):
        limiter.hit("ip", THREE_PER_MINUTE, NOW + timedelta(seconds=i))

    ten_seconds_later = NOW + timedelta(seconds=10)

    with pytest.raises(RateLimitExceededError) as exceeded:
        limiter.hit("ip", THREE_PER_MINUTE, ten_seconds_later)

    # El primer cupo se libera un minuto después de la primera solicitud.
    assert exceeded.value.retry_after == timedelta(seconds=50)


def test_window_slides_and_rejected_requests_do_not_consume_quota() -> None:
    limiter = InMemoryRateLimiter()
    for i in range(3):
        limiter.hit("ip", THREE_PER_MINUTE, NOW + timedelta(seconds=i))
    half_a_minute_later, a_minute_later = NOW + timedelta(seconds=30), NOW + timedelta(minutes=1)
    with pytest.raises(RateLimitExceededError):
        limiter.hit("ip", THREE_PER_MINUTE, half_a_minute_later)

    limiter.hit("ip", THREE_PER_MINUTE, a_minute_later)

    with pytest.raises(RateLimitExceededError):
        limiter.hit("ip", THREE_PER_MINUTE, a_minute_later)


def test_keys_have_independent_quotas() -> None:
    limiter = InMemoryRateLimiter()
    one = RateLimit(1, timedelta(minutes=1))
    limiter.hit("login:1.1.1.1", one, NOW)

    limiter.hit("login:2.2.2.2", one, NOW)
    limiter.hit("register:1.1.1.1", one, NOW)
    with pytest.raises(RateLimitExceededError):
        limiter.hit("login:1.1.1.1", one, NOW)


def test_limiter_forgets_the_least_recent_key_when_full() -> None:
    limiter = InMemoryRateLimiter(max_keys=2)
    one = RateLimit(1, timedelta(minutes=1))
    limiter.hit("a", one, NOW)
    limiter.hit("b", one, NOW)

    limiter.hit("c", one, NOW)

    limiter.hit("a", one, NOW)  # "a" se había descartado: vuelve a tener cupo


@pytest.mark.parametrize(
    ("delta", "seconds"),
    [(timedelta(0), 1), (timedelta(milliseconds=1), 1), (timedelta(seconds=59.2), 60)],
)
def test_retry_after_rounds_up_to_whole_seconds(delta: timedelta, seconds: int) -> None:
    assert retry_after_seconds(delta) == seconds


# Cuerpos inválidos: la dependencia del límite corre antes que la validación del cuerpo,
# así que se prueba sin tocar la base de datos (cada intento responde 422 hasta el límite).
@pytest.mark.parametrize("path", ["/auth/login", "/auth/register"])
def test_auth_routes_are_limited_per_ip(client: TestClient, settings: Settings, path: str) -> None:
    limit = (
        LOGIN_LIMIT_PER_IP
        if path == "/auth/login"
        else RateLimit(max_requests=settings.register_per_ip_per_hour, window=timedelta(hours=1))
    )
    url = f"{API_V1_PREFIX}{path}"
    statuses = {client.post(url, json={}).status_code for _ in range(limit.max_requests)}

    blocked = client.post(url, json={})

    assert statuses == {422}
    assert blocked.status_code == 429
    body = blocked.json()
    assert body["code"] == "RATE_LIMITED"
    assert body["details"]["retry_after_s"] == int(blocked.headers["Retry-After"])
    assert 0 < int(blocked.headers["Retry-After"]) <= limit.window.total_seconds()


def test_other_routes_are_not_limited(client: TestClient) -> None:
    statuses = {client.get("/health").status_code for _ in range(40)}

    assert statuses == {200}
