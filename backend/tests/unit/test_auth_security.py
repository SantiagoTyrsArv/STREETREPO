"""Contraseñas (política y Argon2id) y tokens de acceso (JWT)."""

import uuid
from datetime import UTC, datetime, timedelta

import jwt
import pytest

from app.modules.auth.domain.passwords import (
    MAX_PASSWORD_LENGTH,
    MIN_PASSWORD_LENGTH,
    WeakPasswordError,
    check_password_policy,
)
from app.modules.auth.domain.ports import InvalidAccessTokenError
from app.modules.auth.infrastructure.jwt_tokens import ISSUER, JwtAccessTokenService
from app.modules.auth.infrastructure.passwords import Argon2PasswordHasher
from app.modules.users.domain.entities import normalize_email
from app.modules.users.domain.role import UserRole
from tests.conftest import TEST_JWT_SECRET

USER_ID = uuid.UUID("00000000-0000-0000-0000-0000000000c1")


@pytest.mark.parametrize("length", [MIN_PASSWORD_LENGTH, 64, MAX_PASSWORD_LENGTH])
def test_password_policy_accepts_lengths_in_range(length: int) -> None:
    check_password_policy("x" * length)


@pytest.mark.parametrize(
    ("length", "message"),
    [(MIN_PASSWORD_LENGTH - 1, "al menos 12"), (MAX_PASSWORD_LENGTH + 1, "como máximo 128")],
)
def test_password_policy_rejects_lengths_out_of_range(length: int, message: str) -> None:
    with pytest.raises(WeakPasswordError, match=message):
        check_password_policy("x" * length)


def test_password_policy_does_not_require_character_classes() -> None:
    # ASVS V2.1.9: una frase larga sin números ni símbolos es válida.
    check_password_policy("frase de paso larga sin simbolos")


@pytest.mark.parametrize(
    ("raw", "expected"), [("  Ana@Example.TEST ", "ana@example.test"), ("a@b.co", "a@b.co")]
)
def test_email_is_normalized(raw: str, expected: str) -> None:
    assert normalize_email(raw) == expected


@pytest.fixture(scope="module")
def hasher() -> Argon2PasswordHasher:
    return Argon2PasswordHasher()


def test_argon2id_hash_verifies_only_the_right_password(hasher: Argon2PasswordHasher) -> None:
    password_hash = hasher.hash("correcta horse battery")

    assert password_hash.startswith("$argon2id$")
    assert hasher.verify(password_hash, "correcta horse battery")
    assert not hasher.verify(password_hash, "incorrecta")


def test_argon2_hashes_are_salted(hasher: Argon2PasswordHasher) -> None:
    assert hasher.hash("misma clave segura") != hasher.hash("misma clave segura")


def test_invalid_hash_never_verifies(hasher: Argon2PasswordHasher) -> None:
    assert not hasher.verify("no-es-un-hash", "lo que sea")
    assert hasher.needs_rehash("no-es-un-hash")


def test_current_hash_does_not_need_rehash(hasher: Argon2PasswordHasher) -> None:
    assert not hasher.needs_rehash(hasher.hash("contraseña larga de prueba"))


NOW = datetime(2026, 10, 16, 12, tzinfo=UTC)


@pytest.fixture
def tokens() -> JwtAccessTokenService:
    return JwtAccessTokenService(TEST_JWT_SECRET, ttl_minutes=15)


def _decode_unverified(token: str) -> dict[str, object]:
    return jwt.decode(token, options={"verify_signature": False})


def test_access_token_round_trip(tokens: JwtAccessTokenService) -> None:
    token = tokens.issue(USER_ID, UserRole.ADMIN, datetime.now(UTC))

    claims = tokens.verify(token)

    assert claims.user_id == USER_ID
    assert claims.role is UserRole.ADMIN
    assert tokens.ttl_seconds == 15 * 60


def test_access_token_carries_the_required_claims(tokens: JwtAccessTokenService) -> None:
    payload = _decode_unverified(tokens.issue(USER_ID, UserRole.CITIZEN, NOW))

    assert payload["sub"] == str(USER_ID)
    assert payload["role"] == "ciudadano"
    assert payload["iss"] == ISSUER
    assert payload["exp"] == int((NOW + timedelta(minutes=15)).timestamp())


def test_expired_access_token_is_rejected(tokens: JwtAccessTokenService) -> None:
    token = tokens.issue(USER_ID, UserRole.CITIZEN, datetime.now(UTC) - timedelta(minutes=16))

    with pytest.raises(InvalidAccessTokenError):
        tokens.verify(token)


def test_token_signed_with_another_key_is_rejected(tokens: JwtAccessTokenService) -> None:
    other = JwtAccessTokenService("f" * 64, ttl_minutes=15)

    with pytest.raises(InvalidAccessTokenError):
        tokens.verify(other.issue(USER_ID, UserRole.ADMIN, datetime.now(UTC)))


def _forge(payload: dict[str, object], algorithm: str = "HS256") -> str:
    key = "" if algorithm == "none" else TEST_JWT_SECRET
    return jwt.encode(payload, key, algorithm=algorithm)


def _valid_payload() -> dict[str, object]:
    now = datetime.now(UTC)
    return {
        "sub": str(USER_ID),
        "role": "administrador",
        "typ": "access",
        "iss": ISSUER,
        "iat": now,
        "exp": now + timedelta(minutes=5),
    }


def test_unsigned_token_is_rejected(tokens: JwtAccessTokenService) -> None:
    # Ataque clásico: "alg": "none" sin firma.
    with pytest.raises(InvalidAccessTokenError):
        tokens.verify(_forge(_valid_payload(), algorithm="none"))


def test_token_with_another_algorithm_is_rejected(tokens: JwtAccessTokenService) -> None:
    with pytest.raises(InvalidAccessTokenError):
        tokens.verify(_forge(_valid_payload(), algorithm="HS512"))


@pytest.mark.parametrize("claim", ["sub", "role", "typ", "iss", "iat", "exp"])
def test_token_without_a_required_claim_is_rejected(
    tokens: JwtAccessTokenService, claim: str
) -> None:
    payload = _valid_payload()
    del payload[claim]

    with pytest.raises(InvalidAccessTokenError):
        tokens.verify(_forge(payload))


@pytest.mark.parametrize(
    ("claim", "value"),
    [("typ", "refresh"), ("iss", "otro-sistema"), ("role", "superusuario"), ("sub", "no-uuid")],
)
def test_token_with_a_wrong_claim_is_rejected(
    tokens: JwtAccessTokenService, claim: str, value: str
) -> None:
    payload = _valid_payload() | {claim: value}

    with pytest.raises(InvalidAccessTokenError):
        tokens.verify(_forge(payload))


def test_garbage_token_is_rejected(tokens: JwtAccessTokenService) -> None:
    with pytest.raises(InvalidAccessTokenError):
        tokens.verify("esto.no.es-un-jwt")


def test_short_secret_is_refused() -> None:
    with pytest.raises(ValueError, match="al menos 32"):
        JwtAccessTokenService("corta", ttl_minutes=15)
