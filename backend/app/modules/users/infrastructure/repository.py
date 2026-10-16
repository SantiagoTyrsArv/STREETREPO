import uuid

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modules.users.domain.entities import NewUser, PolicyConsent, User
from app.modules.users.domain.ports import EmailAlreadyRegisteredError
from app.modules.users.infrastructure.models import UserModel

# Nombre que PostgreSQL da a la restricción UNIQUE de usuario.correo (migración 0002).
_EMAIL_UNIQUE_CONSTRAINT = "usuario_correo_key"


def _to_entity(row: UserModel) -> User:
    consent = None
    if row.accepted_policy and row.accepted_policy_at and row.policy_version:
        consent = PolicyConsent(version=row.policy_version, accepted_at=row.accepted_policy_at)
    return User(
        id=row.id,
        name=row.name,
        email=row.email,
        password_hash=row.password_hash,
        role=row.role,
        is_active=row.is_active,
        consent=consent,
        registered_at=row.registered_at,
    )


class SqlUserRepository:
    """Implementa ``UserRepository`` sobre ``usuario``."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_id(self, user_id: uuid.UUID) -> User | None:
        row = self._session.get(UserModel, user_id)
        return None if row is None else _to_entity(row)

    def get_by_email(self, email: str) -> User | None:
        row = self._session.scalars(select(UserModel).where(UserModel.email == email)).one_or_none()
        return None if row is None else _to_entity(row)

    def update_password_hash(self, user_id: uuid.UUID, password_hash: str) -> None:
        self._session.execute(
            update(UserModel).where(UserModel.id == user_id).values(password_hash=password_hash)
        )

    def add(self, user: NewUser) -> User:
        consent = user.consent
        row = UserModel(
            name=user.name,
            email=user.email,
            password_hash=user.password_hash,
            role=user.role,
            accepted_policy=consent is not None,
            accepted_policy_at=None if consent is None else consent.accepted_at,
            policy_version=None if consent is None else consent.version,
        )
        try:
            # Savepoint: un correo repetido no invalida el resto de la transacción.
            with self._session.begin_nested():
                self._session.add(row)
                self._session.flush()
        except IntegrityError as exc:
            if _EMAIL_UNIQUE_CONSTRAINT in str(exc.orig):
                raise EmailAlreadyRegisteredError("Ya existe una cuenta con ese correo") from exc
            raise
        self._session.refresh(row)
        return _to_entity(row)
