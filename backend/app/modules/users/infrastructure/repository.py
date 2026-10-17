import uuid
from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modules.users.domain.anonymization import (
    ANONYMIZED_NAME,
    UNUSABLE_PASSWORD_HASH,
    anonymized_email,
)
from app.modules.users.domain.deletion_request import DeletionRequest, DeletionRequestStatus
from app.modules.users.domain.entities import NewUser, PolicyConsent, User
from app.modules.users.domain.ports import EmailAlreadyRegisteredError
from app.modules.users.infrastructure.models import DataDeletionRequestModel, UserModel

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
        self._flush_checking_email(row)
        self._session.refresh(row)
        return _to_entity(row)

    def update_profile(self, user_id: uuid.UUID, name: str, email: str) -> User:
        row = self._session.get_one(UserModel, user_id)
        row.name = name
        row.email = email
        self._flush_checking_email(row)
        return _to_entity(row)

    def anonymize(self, user_id: uuid.UUID) -> None:
        # Se conservan rol, fecha de registro y el consentimiento (versión y fecha): son la
        # constancia de que hubo autorización, no datos que identifiquen al titular.
        self._session.execute(
            update(UserModel)
            .where(UserModel.id == user_id)
            .values(
                name=ANONYMIZED_NAME,
                email=anonymized_email(user_id),
                password_hash=UNUSABLE_PASSWORD_HASH,
                is_active=False,
            )
        )
        self._session.expire_all()

    def _flush_checking_email(self, row: UserModel) -> None:
        try:
            # Savepoint: un correo repetido no invalida el resto de la transacción.
            with self._session.begin_nested():
                self._session.add(row)
                self._session.flush()
        except IntegrityError as exc:
            if _EMAIL_UNIQUE_CONSTRAINT in str(exc.orig):
                raise EmailAlreadyRegisteredError("Ya existe una cuenta con ese correo") from exc
            raise


class SqlDeletionRequestRepository:
    """Implementa ``DeletionRequestRepository`` sobre ``solicitud_supresion``."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def add_attended(self, user_id: uuid.UUID, at: datetime) -> DeletionRequest:
        row = DataDeletionRequestModel(
            user_id=user_id,
            status=DeletionRequestStatus.ATTENDED,
            requested_at=at,
            attended_at=at,
        )
        self._session.add(row)
        self._session.flush()
        return DeletionRequest(
            id=row.id,
            user_id=row.user_id,
            status=row.status,
            requested_at=row.requested_at,
            attended_at=row.attended_at,
        )
