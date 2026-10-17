"""Derechos del titular con dobles: actualizar datos, confirmar contraseña y suprimir."""

import uuid
from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta

import pytest

from app.modules.auth.application.errors import (
    AccountLockedError,
    PasswordConfirmationRequiredError,
    WrongPasswordError,
)
from app.modules.auth.application.login import login_attempt_key
from app.modules.auth.application.reauthentication import PasswordConfirmation
from app.modules.auth.domain.lockout import DEFAULT_LOCKOUT_POLICY
from app.modules.auth.infrastructure.memory_login_attempts import InMemoryLoginAttemptStore
from app.modules.users.application.data_rights import (
    ProfileChanges,
    RequestDataDeletion,
    UpdateMyData,
)
from app.modules.users.domain.anonymization import (
    ANONYMIZED_NAME,
    UNUSABLE_PASSWORD_HASH,
    anonymized_email,
)
from app.modules.users.domain.deletion_request import DeletionRequest, DeletionRequestStatus
from app.modules.users.domain.entities import User
from app.modules.users.domain.ports import EmailAlreadyRegisteredError
from app.modules.users.domain.role import UserRole
from tests.unit.test_auth_application import (
    NOW,
    PASSWORD,
    FakeClock,
    FakeHasher,
    FakeUsers,
    Transaction,
)


class DataRightsUsers(FakeUsers):
    def update_profile(self, user_id: uuid.UUID, name: str, email: str) -> User:
        other = self.get_by_email(email)
        if other is not None and other.id != user_id:
            raise EmailAlreadyRegisteredError("repetido")
        self.by_id[user_id] = replace(self.by_id[user_id], name=name, email=email)
        return self.by_id[user_id]

    def anonymize(self, user_id: uuid.UUID) -> None:
        self.by_id[user_id] = replace(
            self.by_id[user_id],
            name=ANONYMIZED_NAME,
            email=anonymized_email(user_id),
            password_hash=UNUSABLE_PASSWORD_HASH,
            is_active=False,
        )


class FakeDeletionRequests:
    def __init__(self) -> None:
        self.rows: list[DeletionRequest] = []

    def add_attended(self, user_id: uuid.UUID, at: datetime) -> DeletionRequest:
        request = DeletionRequest(uuid.uuid4(), user_id, DeletionRequestStatus.ATTENDED, at, at)
        self.rows.append(request)
        return request


class FakeReportTexts:
    def __init__(self) -> None:
        self.cleared: list[uuid.UUID] = []

    def clear_descriptions(self, user_id: uuid.UUID) -> None:
        self.cleared.append(user_id)


class FakeSessions:
    """Solo lo que usa la supresión del puerto ``RefreshTokenRepository``."""

    def __init__(self, fail: bool = False) -> None:
        self.revoked_for: list[uuid.UUID] = []
        self._fail = fail

    def revoke_all_for_user(self, user_id: uuid.UUID) -> None:
        if self._fail:
            raise RuntimeError("falla de la base")
        self.revoked_for.append(user_id)


@dataclass
class Rights:
    users: DataRightsUsers = field(default_factory=DataRightsUsers)
    hasher: FakeHasher = field(default_factory=FakeHasher)
    attempts: InMemoryLoginAttemptStore = field(default_factory=InMemoryLoginAttemptStore)
    clock: FakeClock = field(default_factory=FakeClock)
    transaction: Transaction = field(default_factory=Transaction)
    deletion_requests: FakeDeletionRequests = field(default_factory=FakeDeletionRequests)
    report_texts: FakeReportTexts = field(default_factory=FakeReportTexts)
    sessions: FakeSessions = field(default_factory=FakeSessions)

    @property
    def confirmation(self) -> PasswordConfirmation:
        return PasswordConfirmation(self.hasher, self.attempts, DEFAULT_LOCKOUT_POLICY, self.clock)

    def add_user(self, email: str = "ana@example.test") -> User:
        user = User(
            id=uuid.uuid4(),
            name="Ana Pérez",
            email=email,
            password_hash=f"hash:{PASSWORD}",
            role=UserRole.CITIZEN,
            is_active=True,
            consent=None,
            registered_at=NOW,
        )
        self.users.by_id[user.id] = user
        return user

    def update(self, user: User, **changes: str | None) -> User:
        use_case = UpdateMyData(self.users, self.confirmation, self.transaction)
        return use_case.execute(user, ProfileChanges(**changes))

    def delete(self, user: User, password: str = PASSWORD) -> DeletionRequest:
        use_case = RequestDataDeletion(
            users=self.users,
            deletion_requests=self.deletion_requests,
            report_texts=self.report_texts,
            refresh_tokens=self.sessions,  # type: ignore[arg-type]
            confirmation=self.confirmation,
            clock=self.clock,
            transaction=self.transaction,
        )
        return use_case.execute(user, password)


@pytest.fixture
def rights() -> Rights:
    return Rights()


# --- Confirmación de contraseña ---------------------------------------------


def test_confirmation_requires_a_password(rights: Rights) -> None:
    with pytest.raises(PasswordConfirmationRequiredError):
        rights.confirmation.confirm(rights.add_user(), None)


def test_wrong_confirmations_count_towards_the_login_lockout(rights: Rights) -> None:
    user = rights.add_user()
    for _ in range(5):
        with pytest.raises(WrongPasswordError):
            rights.confirmation.confirm(user, "no es la contraseña")

    with pytest.raises(AccountLockedError):
        rights.confirmation.confirm(user, PASSWORD)
    assert rights.attempts.get(login_attempt_key(user.email)) is not None


def test_right_confirmation_clears_previous_failures(rights: Rights) -> None:
    user = rights.add_user()
    with pytest.raises(WrongPasswordError):
        rights.confirmation.confirm(user, "no es la contraseña")

    rights.confirmation.confirm(user, PASSWORD)

    assert rights.attempts.get(login_attempt_key(user.email)) is None


# --- Actualizar datos ---------------------------------------------------------


def test_update_name_does_not_need_the_password(rights: Rights) -> None:
    user = rights.add_user()

    updated = rights.update(user, name="  Ana María  ")

    assert updated.name == "Ana María"
    assert updated.email == user.email
    assert rights.transaction.commits == 1
    assert rights.hasher.verified == []


def test_update_email_requires_the_current_password(rights: Rights) -> None:
    user = rights.add_user()

    with pytest.raises(PasswordConfirmationRequiredError):
        rights.update(user, email="nueva@example.test")
    with pytest.raises(WrongPasswordError):
        rights.update(user, email="nueva@example.test", current_password="otra")
    assert rights.users.by_id[user.id].email == user.email
    assert rights.transaction.commits == 0


def test_update_email_with_the_password_normalizes_it(rights: Rights) -> None:
    user = rights.add_user()

    updated = rights.update(user, email=" Nueva@Example.TEST ", current_password=PASSWORD)

    assert updated.email == "nueva@example.test"


def test_same_email_with_other_case_is_not_a_change(rights: Rights) -> None:
    user = rights.add_user()

    unchanged = rights.update(user, email="ANA@example.test")

    assert unchanged == user
    assert rights.transaction.commits == 0


def test_update_rejects_an_email_of_another_account_and_rolls_back(rights: Rights) -> None:
    user = rights.add_user()
    rights.add_user(email="otra@example.test")

    with pytest.raises(EmailAlreadyRegisteredError):
        rights.update(user, email="otra@example.test", current_password=PASSWORD)
    assert rights.transaction.rollbacks == 1


# --- Supresión ----------------------------------------------------------------


def test_deletion_anonymizes_revokes_and_records_the_request(rights: Rights) -> None:
    user = rights.add_user()

    request = rights.delete(user)

    stored = rights.users.by_id[user.id]
    assert (stored.name, stored.email) == (ANONYMIZED_NAME, anonymized_email(user.id))
    assert stored.password_hash == UNUSABLE_PASSWORD_HASH
    assert not stored.is_active
    assert rights.report_texts.cleared == [user.id]
    assert rights.sessions.revoked_for == [user.id]
    assert request.status is DeletionRequestStatus.ATTENDED
    assert request.requested_at == request.attended_at == NOW
    assert rights.transaction.commits == 1


def test_deletion_requires_the_right_password(rights: Rights) -> None:
    user = rights.add_user()

    with pytest.raises(WrongPasswordError):
        rights.delete(user, password="otra frase")
    assert rights.users.by_id[user.id] == user
    assert rights.deletion_requests.rows == []


def test_deletion_is_all_or_nothing(rights: Rights) -> None:
    rights.sessions = FakeSessions(fail=True)
    user = rights.add_user()

    with pytest.raises(RuntimeError):
        rights.delete(user)
    assert rights.transaction.rollbacks == 1
    assert rights.transaction.commits == 0


def test_anonymized_email_is_unique_and_not_personal() -> None:
    first, second = uuid.uuid4(), uuid.uuid4()

    assert anonymized_email(first) != anonymized_email(second)
    assert anonymized_email(first).endswith("@anonimo.invalid")


def test_lock_expiry_lets_the_titular_confirm_again(rights: Rights) -> None:
    user = rights.add_user()
    for _ in range(5):
        with pytest.raises(WrongPasswordError):
            rights.confirmation.confirm(user, "no es la contraseña")

    rights.clock.current += timedelta(minutes=1)

    rights.confirmation.confirm(user, PASSWORD)
