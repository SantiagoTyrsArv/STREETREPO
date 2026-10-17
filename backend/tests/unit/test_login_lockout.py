"""Política de bloqueo progresivo y almacén en memoria de fallos de inicio de sesión."""

from datetime import UTC, datetime, timedelta

import pytest

from app.modules.auth.domain.lockout import DEFAULT_LOCKOUT_POLICY, FailedLogins
from app.modules.auth.infrastructure.memory_login_attempts import InMemoryLoginAttemptStore

NOW = datetime(2026, 10, 16, 12, tzinfo=UTC)
POLICY = DEFAULT_LOCKOUT_POLICY


@pytest.mark.parametrize(
    ("failures", "minutes"),
    [(1, None), (4, None), (5, 1), (6, 2), (7, 4), (8, 8), (9, 15), (10, 15), (500, 15)],
)
def test_lock_duration_doubles_up_to_the_cap(failures: int, minutes: int | None) -> None:
    expected = timedelta(minutes=minutes) if minutes is not None else None

    assert POLICY.lock_duration(failures) == expected


def _failures(times: int, start: datetime = NOW) -> FailedLogins | None:
    record: FailedLogins | None = None
    for i in range(times):
        record = POLICY.register_failure(record, start + timedelta(seconds=i))
    return record


def test_fifth_failure_locks_until_one_minute_later() -> None:
    record = _failures(5)

    assert record is not None
    assert record.count == 5
    assert record.locked_until == record.last_failure_at + timedelta(minutes=1)


def test_failures_are_forgotten_after_an_hour_without_failing() -> None:
    previous = _failures(4)
    assert previous is not None

    record = POLICY.register_failure(previous, previous.last_failure_at + timedelta(hours=1))

    assert record.count == 1
    assert record.locked_until is None


def test_remaining_lock() -> None:
    record = _failures(5)
    assert record is not None
    unlock = record.locked_until
    assert unlock is not None

    assert POLICY.remaining_lock(None, NOW) is None
    assert POLICY.remaining_lock(_failures(3), NOW) is None
    assert POLICY.remaining_lock(record, unlock - timedelta(seconds=10)) == timedelta(seconds=10)
    assert POLICY.remaining_lock(record, unlock) is None


def test_store_saves_reads_and_clears() -> None:
    store = InMemoryLoginAttemptStore()
    record = FailedLogins(2, NOW, None)

    store.save("k", record)
    assert store.get("k") == record
    store.clear("k")
    store.clear("k")  # borrar algo que no existe no falla
    assert store.get("k") is None


def test_store_discards_the_least_recent_key_when_full() -> None:
    store = InMemoryLoginAttemptStore(max_keys=2)
    store.save("a", FailedLogins(1, NOW, None))
    store.save("b", FailedLogins(1, NOW, None))
    store.save("a", FailedLogins(2, NOW, None))  # "a" pasa a ser la más reciente

    store.save("c", FailedLogins(1, NOW, None))

    assert store.get("b") is None
    assert store.get("a") is not None
    assert store.get("c") is not None
