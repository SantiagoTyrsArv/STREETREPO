import uuid
from datetime import datetime

from sqlalchemy import select, text, update
from sqlalchemy.orm import Session

from app.modules.auth.domain.entities import StoredRefreshToken
from app.modules.auth.infrastructure.models import RefreshTokenModel

# Sigue la cadena reemplazado_por desde un token: la sesión es el token y todos
# los que lo sucedieron por rotación.
_REVOKE_CHAIN = text(
    """
    WITH RECURSIVE cadena AS (
        SELECT id_token, reemplazado_por FROM token_refresco WHERE id_token = :id
        UNION ALL
        SELECT t.id_token, t.reemplazado_por
        FROM token_refresco AS t JOIN cadena AS c ON t.id_token = c.reemplazado_por
    )
    UPDATE token_refresco SET revocado = true
    WHERE id_token IN (SELECT id_token FROM cadena)
    """
)


class SqlRefreshTokenRepository:
    """Implementa ``RefreshTokenRepository`` sobre ``token_refresco``."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def add(
        self, user_id: uuid.UUID, token_hash: str, issued_at: datetime, expires_at: datetime
    ) -> uuid.UUID:
        row = RefreshTokenModel(
            user_id=user_id, token_hash=token_hash, issued_at=issued_at, expires_at=expires_at
        )
        self._session.add(row)
        self._session.flush()
        return row.id

    def get_by_hash(self, token_hash: str) -> StoredRefreshToken | None:
        row = self._session.scalars(
            select(RefreshTokenModel)
            .where(RefreshTokenModel.token_hash == token_hash)
            # Bloquea la fila: dos refrescos simultáneos con el mismo token se
            # serializan y el segundo se trata como reutilización.
            .with_for_update()
            .execution_options(populate_existing=True)
        ).one_or_none()
        if row is None:
            return None
        return StoredRefreshToken(
            id=row.id,
            user_id=row.user_id,
            expires_at=row.expires_at,
            revoked=row.revoked,
            replaced_by=row.replaced_by,
        )

    def mark_replaced(self, token_id: uuid.UUID, replaced_by: uuid.UUID) -> None:
        self._session.execute(
            update(RefreshTokenModel)
            .where(RefreshTokenModel.id == token_id)
            .values(revoked=True, replaced_by=replaced_by)
        )

    def revoke_chain(self, token_id: uuid.UUID) -> None:
        self._session.execute(_REVOKE_CHAIN, {"id": token_id})
        self._session.expire_all()

    def revoke_all_for_user(self, user_id: uuid.UUID) -> None:
        self._session.execute(
            update(RefreshTokenModel)
            .where(RefreshTokenModel.user_id == user_id, RefreshTokenModel.revoked.is_(False))
            .values(revoked=True)
        )
