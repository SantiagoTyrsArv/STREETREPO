"""Borrado de los datos de demostración y lectura de sus fotos de origen (decisión 76)."""

from collections.abc import Sequence
from pathlib import Path
from typing import Final

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.modules.admin.domain.demo import DEMO_EMAIL_DOMAIN, DemoRemoval
from app.modules.reports.infrastructure.models import EvidenceModel, ReportModel
from app.modules.users.infrastructure.models import UserModel
from app.modules.validation.infrastructure.models import DuplicateWarningModel

# backend/app/demo/photos: imágenes genéricas incluidas en el repositorio.
DEMO_PHOTOS_DIR: Final = Path(__file__).resolve().parents[3] / "demo" / "photos"


def load_demo_photos(directory: Path = DEMO_PHOTOS_DIR) -> Sequence[bytes]:
    """Contenido de las fotos de demostración, en orden de nombre."""
    return [path.read_bytes() for path in sorted(directory.glob("*.jpg"))]


class SqlDemoData:
    """Implementa ``DemoDataStore``. Evidencia, historial, evaluaciones y confirmaciones
    se van con el reporte (``ON DELETE CASCADE``); no confirma la transacción.

    Borra las cuentas de un dominio reservado: el de demostración por defecto, o el de la
    prueba de carga (``LOADTEST_EMAIL_DOMAIN``, fase 8).
    """

    def __init__(self, session: Session, email_domain: str = DEMO_EMAIL_DOMAIN) -> None:
        self._session = session
        self._email_domain = email_domain

    def delete_all(self) -> DemoRemoval:
        is_demo_user = UserModel.email.endswith(f"@{self._email_domain}", autoescape=True)
        demo_users = select(UserModel.id).where(is_demo_user)
        demo_reports = select(ReportModel.id).where(ReportModel.user_id.in_(demo_users))

        photo_keys = sorted(
            self._session.execute(
                select(EvidenceModel.photo_url).where(EvidenceModel.report_id.in_(demo_reports))
            ).scalars()
        )
        # Los avisos de posible duplicado retienen a su autor (RESTRICT, decisión 23a): una
        # cuenta de carga que recibió un 409 tiene avisos y no se podría borrar sin esto.
        self._session.execute(
            delete(DuplicateWarningModel).where(DuplicateWarningModel.user_id.in_(demo_users))
        )
        reports = self._session.execute(
            delete(ReportModel).where(ReportModel.user_id.in_(demo_users)).returning(ReportModel.id)
        ).all()
        users = self._session.execute(
            delete(UserModel).where(is_demo_user).returning(UserModel.id)
        ).all()
        self._session.expire_all()
        return DemoRemoval(reports=len(reports), users=len(users), photo_keys=photo_keys)
