"""Registro, inicio de sesión, rotación de refresco y cierre de sesión con dobles."""

import uuid
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime, timedelta

import pytest

from app.modules.auth.application.errors import (
    AccountLockedError,
    InvalidCredentialsError,
    InvalidRefreshTokenError,
    PolicyNotAcceptedError,
    PolicyVersionMismatchError,
)
from app.modules.auth.application.login import Login, Logout, RefreshSession, login_attempt_key
from app.modules.auth.application.register import RegisterCitizen, Registration
from app.modules.auth.application.sessions import SessionIssuer, hash_refresh_token
from app.modules.auth.domain.entities import AccessClaims, StoredRefreshToken
from app.modules.auth.domain.lockout import DEFAULT_LOCKOUT_POLICY
from app.modules.auth.domain.passwords import WeakPasswordError
from app.modules.auth.infrastructure.memory_login_attempts import InMemoryLoginAttemptStore
from app.modules.users.domain.entities import NewUser, User
from app.modules.users.domain.ports import EmailAlreadyRegisteredError
from app.modules.users.domain.role import UserRole

NOW = datetime(2026, 10, 16, 12, tzinfo=UTC)
POLICY = "1.0"
PASSWORD = "una frase de paso larga"


class FakeHasher:
    """Hash reversible solo para pruebas; ``outdated:`` simula parámetros viejos."""

    def __init__(self) -> None:
        self.verified: list[str] = []

    def hash(self, password: str) -> str:
        return f"hash:{password}"

    def verify(self, password_hash: str, password: str) -> bool:
        self.verified.append(password_hash)
        return password_hash.split(":", 1)[1] == password

    def needs_rehash(self, password_hash: str) -> bool:
        return password_hash.startswith("outdated:")


class FakeUsers:
    def __init__(self) -> None:
        self.by_id: dict[uuid.UUID, User] = {}

    def get_by_id(self, user_id: uuid.UUID) -> User | None:
        return self.by_id.get(user_id)

    def get_by_email(self, email: str) -> User | None:
        return next((u for u in self.by_id.values() if u.email == email), None)

    def update_password_hash(self, user_id: uuid.UUID, password_hash: str) -> None:
        self.by_id[user_id] = replace(self.by_id[user_id], password_hash=password_hash)

    def add(self, user: NewUser) -> User:
        if self.get_by_email(user.email):
            raise EmailAlreadyRegisteredError("repetido")
        created = User(
            id=uuid.uuid4(),
            name=user.name,
            email=user.email,
            password_hash=user.password_hash,
            role=user.role,
            is_active=True,
            consent=user.consent,
            registered_at=NOW,
        )
        self.by_id[created.id] = created
        return created


class FakeRefreshTokens:
    def __init__(self) -> None:
        self.rows: dict[uuid.UUID, tuple[str, StoredRefreshToken]] = {}

    def add(
        self, user_id: uuid.UUID, token_hash: str, issued_at: datetime, expires_at: datetime
    ) -> uuid.UUID:
        token_id = uuid.uuid4()
        self.rows[token_id] = (
            token_hash,
            StoredRefreshToken(token_id, user_id, expires_at, revoked=False, replaced_by=None),
        )
        return token_id

    def get_by_hash(self, token_hash: str) -> StoredRefreshToken | None:
        return next((t for h, t in self.rows.values() if h == token_hash), None)

    def _update(self, token_id: uuid.UUID, **changes: object) -> None:
        token_hash, token = self.rows[token_id]
        self.rows[token_id] = (token_hash, replace(token, **changes))  # type: ignore[arg-type]

    def mark_replaced(self, token_id: uuid.UUID, replaced_by: uuid.UUID) -> None:
        self._update(token_id, revoked=True, replaced_by=replaced_by)

    def revoke_chain(self, token_id: uuid.UUID) -> None:
        current: uuid.UUID | None = token_id
        while current is not None:
            self._update(current, revoked=True)
            current = self.rows[current][1].replaced_by

    def revoke_all_for_user(self, user_id: uuid.UUID) -> None:
        for token_id, (_, token) in list(self.rows.items()):
            if token.user_id == user_id:
                self._update(token_id, revoked=True)

    def active(self) -> list[StoredRefreshToken]:
        return [t for _, t in self.rows.values() if not t.revoked]


class FakeAccessTokens:
    ttl_seconds = 900

    def issue(self, user_id: uuid.UUID, role: UserRole, now: datetime) -> str:
        return f"access:{user_id}:{role.value}"

    def verify(self, token: str) -> AccessClaims:  # pragma: no cover - no se usa aquí
        raise NotImplementedError


@dataclass
class FakeClock:
    current: datetime = NOW

    def now(self) -> datetime:
        return self.current


class Transaction:
    def __init__(self) -> None:
        self.commits = 0
        self.rollbacks = 0

    def commit(self) -> None:
        self.commits += 1

    def rollback(self) -> None:
        self.rollbacks += 1


@dataclass
class Auth:
    users: FakeUsers = field(default_factory=FakeUsers)
    hasher: FakeHasher = field(default_factory=FakeHasher)
    refresh_tokens: FakeRefreshTokens = field(default_factory=FakeRefreshTokens)
    clock: FakeClock = field(default_factory=FakeClock)
    transaction: Transaction = field(default_factory=Transaction)
    attempts: InMemoryLoginAttemptStore = field(default_factory=InMemoryLoginAttemptStore)

    def register(self, **overrides: object) -> User:
        data = {
            "name": "  Ana Pérez ",
            "email": " Ana@Example.TEST ",
            "password": PASSWORD,
            "accepted_policy": True,
            "policy_version": POLICY,
        } | overrides
        use_case = RegisterCitizen(self.users, self.hasher, self.clock, self.transaction, POLICY)
        return use_case.execute(Registration(**data))  # type: ignore[arg-type]

    @property
    def sessions(self) -> SessionIssuer:
        return SessionIssuer(FakeAccessTokens(), self.refresh_tokens, timedelta(days=7))

    def login(self, email: str = "ana@example.test", password: str = PASSWORD) -> str:
        use_case = Login(
            self.users,
            self.hasher,
            self.sessions,
            self.clock,
            self.transaction,
            attempts=self.attempts,
            lockout=DEFAULT_LOCKOUT_POLICY,
        )
        return use_case.execute(email, password).refresh_token

    def refresh(self, token: str) -> str:
        use_case = RefreshSession(
            self.users, self.refresh_tokens, self.sessions, self.clock, self.transaction
        )
        return use_case.execute(token).refresh_token


@pytest.fixture
def auth() -> Auth:
    return Auth()


# --- Registro ---------------------------------------------------------------


def test_register_creates_a_citizen_with_consent(auth: Auth) -> None:
    user = auth.register()

    assert user.role is UserRole.CITIZEN
    assert user.name == "Ana Pérez"
    assert user.email == "ana@example.test"
    assert user.password_hash == f"hash:{PASSWORD}"
    assert user.consent is not None
    assert (user.consent.version, user.consent.accepted_at) == (POLICY, NOW)
    assert auth.transaction.commits == 1


def test_register_requires_accepting_the_policy(auth: Auth) -> None:
    with pytest.raises(PolicyNotAcceptedError):
        auth.register(accepted_policy=False)
    assert auth.users.by_id == {}


def test_register_requires_the_current_policy_version(auth: Auth) -> None:
    with pytest.raises(PolicyVersionMismatchError, match=r"1\.0"):
        auth.register(policy_version="0.9")


def test_register_enforces_the_password_policy(auth: Auth) -> None:
    with pytest.raises(WeakPasswordError):
        auth.register(password="corta")


def test_register_rejects_a_repeated_email_and_rolls_back(auth: Auth) -> None:
    auth.register()

    with pytest.raises(EmailAlreadyRegisteredError):
        auth.register(email="ANA@example.test")
    assert auth.transaction.rollbacks == 1


# --- Inicio de sesión -------------------------------------------------------


def test_login_issues_a_stored_refresh_token(auth: Auth) -> None:
    auth.register()

    token = auth.login(email=" ANA@example.test ")

    stored = auth.refresh_tokens.get_by_hash(hash_refresh_token(token))
    assert stored is not None
    assert stored.expires_at == NOW + timedelta(days=7)


def test_login_never_stores_the_refresh_token_in_clear(auth: Auth) -> None:
    auth.register()
    token = auth.login()

    assert all(token not in h for h, _ in auth.refresh_tokens.rows.values())


def test_login_with_wrong_password_fails(auth: Auth) -> None:
    auth.register()

    with pytest.raises(InvalidCredentialsError):
        auth.login(password="otra frase cualquiera")


def test_login_with_unknown_email_still_verifies_a_hash(auth: Auth) -> None:
    # Mismo trabajo que con un correo real: el tiempo no revela qué correos existen.
    with pytest.raises(InvalidCredentialsError):
        auth.login(email="nadie@example.test")
    assert len(auth.hasher.verified) == 1


def test_inactive_user_cannot_log_in(auth: Auth) -> None:
    user = auth.register()
    auth.users.by_id[user.id] = replace(user, is_active=False)

    with pytest.raises(InvalidCredentialsError):
        auth.login()


def test_login_upgrades_an_outdated_hash(auth: Auth) -> None:
    user = auth.register()
    auth.users.by_id[user.id] = replace(user, password_hash=f"outdated:{PASSWORD}")

    auth.login()

    assert auth.users.by_id[user.id].password_hash == f"hash:{PASSWORD}"


# --- Bloqueo progresivo ------------------------------------------------------

WRONG = "otra frase cualquiera"


def _fail_logins(auth: Auth, times: int, email: str = "ana@example.test") -> None:
    for _ in range(times):
        with pytest.raises(InvalidCredentialsError):
            auth.login(email=email, password=WRONG)


def test_login_locks_after_five_consecutive_failures(auth: Auth) -> None:
    auth.register()
    _fail_logins(auth, 4)
    auth.clock.current += timedelta(seconds=1)
    _fail_logins(auth, 1)
    verified_before = len(auth.hasher.verified)

    # Ni la contraseña correcta entra, y durante el bloqueo no se verifica ningún hash.
    with pytest.raises(AccountLockedError) as locked:
        auth.login()
    assert locked.value.retry_after == timedelta(minutes=1)
    assert len(auth.hasher.verified) == verified_before


def test_lock_expires_and_success_resets_the_count(auth: Auth) -> None:
    auth.register()
    _fail_logins(auth, 5)

    auth.clock.current += timedelta(minutes=1)
    auth.login()

    assert auth.attempts.get(login_attempt_key("ana@example.test")) is None
    _fail_logins(auth, 4)  # vuelve a tener 5 intentos libres
    auth.login()


def test_each_failure_after_the_lock_doubles_it(auth: Auth) -> None:
    auth.register()
    _fail_logins(auth, 5)
    auth.clock.current += timedelta(minutes=1)
    _fail_logins(auth, 1)

    with pytest.raises(AccountLockedError) as locked:
        auth.login()
    assert locked.value.retry_after == timedelta(minutes=2)


def test_unknown_emails_are_locked_too(auth: Auth) -> None:
    # Si solo se bloquearan las cuentas reales, el bloqueo revelaría qué correos existen.
    _fail_logins(auth, 5, email="nadie@example.test")

    with pytest.raises(AccountLockedError):
        auth.login(email="nadie@example.test")


def test_lock_is_per_email_and_ignores_case_and_spaces(auth: Auth) -> None:
    auth.register()
    auth.register(email="otra@example.test")
    _fail_logins(auth, 5, email=" ANA@example.test ")

    with pytest.raises(AccountLockedError):
        auth.login(email="ana@example.test")
    auth.login(email="otra@example.test")


def test_attempt_key_does_not_contain_the_email() -> None:
    key = login_attempt_key(" Ana@Example.test ")

    assert "ana" not in key
    assert key == login_attempt_key("ana@example.test")


# --- Refresco con rotación ---------------------------------------------------


def test_refresh_rotates_the_token(auth: Auth) -> None:
    auth.register()
    first = auth.login()

    second = auth.refresh(first)

    assert second != first
    old = auth.refresh_tokens.get_by_hash(hash_refresh_token(first))
    new = auth.refresh_tokens.get_by_hash(hash_refresh_token(second))
    assert old is not None
    assert new is not None
    assert old.revoked
    assert old.replaced_by == new.id
    assert not new.revoked


def test_reusing_a_rotated_token_revokes_the_whole_session(auth: Auth) -> None:
    auth.register()
    first = auth.login()
    second = auth.refresh(first)
    auth.refresh(second)

    with pytest.raises(InvalidRefreshTokenError):
        auth.refresh(first)  # alguien copió el primer token

    assert auth.refresh_tokens.active() == []


def test_reuse_does_not_close_other_sessions(auth: Auth) -> None:
    auth.register()
    phone = auth.login()
    panel = auth.login()
    auth.refresh(phone)

    with pytest.raises(InvalidRefreshTokenError):
        auth.refresh(phone)

    assert auth.refresh(panel)


def test_unknown_refresh_token_fails(auth: Auth) -> None:
    with pytest.raises(InvalidRefreshTokenError):
        auth.refresh("inventado")


def test_expired_refresh_token_fails(auth: Auth) -> None:
    auth.register()
    token = auth.login()
    auth.clock.current = NOW + timedelta(days=7)

    with pytest.raises(InvalidRefreshTokenError, match="venció"):
        auth.refresh(token)


def test_refresh_of_a_deactivated_user_revokes_everything(auth: Auth) -> None:
    user = auth.register()
    token = auth.login()
    auth.login()
    auth.users.by_id[user.id] = replace(user, is_active=False)

    with pytest.raises(InvalidRefreshTokenError):
        auth.refresh(token)

    assert auth.refresh_tokens.active() == []


# --- Cierre de sesión --------------------------------------------------------


def test_logout_revokes_the_session(auth: Auth) -> None:
    auth.register()
    token = auth.refresh(auth.login())

    Logout(auth.refresh_tokens, auth.transaction).execute(token)

    assert auth.refresh_tokens.active() == []
    with pytest.raises(InvalidRefreshTokenError):
        auth.refresh(token)


def test_logout_is_idempotent(auth: Auth) -> None:
    logout = Logout(auth.refresh_tokens, auth.transaction)

    logout.execute("desconocido")
    logout.execute("desconocido")

    assert auth.transaction.commits == 0
