"""Derechos del titular (Ley 1581, guía 7.2): actualizar sus datos y suprimirlos."""

from dataclasses import dataclass

from app.modules.auth.application.reauthentication import PasswordConfirmation
from app.modules.auth.domain.ports import RefreshTokenRepository
from app.modules.users.domain.deletion_request import DeletionRequest
from app.modules.users.domain.entities import User, normalize_email
from app.modules.users.domain.ports import (
    DeletionRequestRepository,
    ReportTextEraser,
    UserRepository,
)
from app.shared.application.clock import Clock
from app.shared.application.transaction import TransactionManager


@dataclass(frozen=True, slots=True)
class ProfileChanges:
    """Campos en ``None`` no cambian. ``current_password`` solo se exige si cambia el correo."""

    name: str | None = None
    email: str | None = None
    current_password: str | None = None


class UpdateMyData:
    """Derecho a actualizar y rectificar: nombre y correo.

    Cambiar el correo exige la contraseña actual, porque el correo da acceso a la cuenta
    (propuesta 26).
    """

    def __init__(
        self,
        users: UserRepository,
        confirmation: PasswordConfirmation,
        transaction: TransactionManager,
    ) -> None:
        self._users = users
        self._confirmation = confirmation
        self._transaction = transaction

    def execute(self, user: User, changes: ProfileChanges) -> User:
        name = user.name if changes.name is None else changes.name.strip()
        email = user.email if changes.email is None else normalize_email(changes.email)
        if email != user.email:
            self._confirmation.confirm(user, changes.current_password)
        if (name, email) == (user.name, user.email):
            return user
        try:
            updated = self._users.update_profile(user.id, name, email)
            self._transaction.commit()
        except Exception:
            self._transaction.rollback()
            raise
        return updated


class RequestDataDeletion:
    """Derecho a la supresión, atendido de inmediato y en una sola transacción (decisión 23a).

    Anonimiza la cuenta, borra la descripción libre de sus reportes, revoca todas sus
    sesiones y deja la constancia ``atendida``. Si algo falla, no se aplica nada.
    """

    def __init__(
        self,
        *,
        users: UserRepository,
        deletion_requests: DeletionRequestRepository,
        report_texts: ReportTextEraser,
        refresh_tokens: RefreshTokenRepository,
        confirmation: PasswordConfirmation,
        clock: Clock,
        transaction: TransactionManager,
    ) -> None:
        self._users = users
        self._deletion_requests = deletion_requests
        self._report_texts = report_texts
        self._refresh_tokens = refresh_tokens
        self._confirmation = confirmation
        self._clock = clock
        self._transaction = transaction

    def execute(self, user: User, current_password: str) -> DeletionRequest:
        self._confirmation.confirm(user, current_password)
        try:
            request = self._deletion_requests.add_attended(user.id, self._clock.now())
            self._report_texts.clear_descriptions(user.id)
            # TODO(propuesta-10): definir en la fase 5, cuando exista su almacenamiento, el
            # trato de las fotos del titular con rostros o placas (decisión del 2026-10-16).
            self._users.anonymize(user.id)
            self._refresh_tokens.revoke_all_for_user(user.id)
            self._transaction.commit()
        except Exception:
            self._transaction.rollback()
            raise
        return request
