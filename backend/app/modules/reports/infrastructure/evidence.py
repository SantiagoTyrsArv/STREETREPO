import uuid
from collections.abc import Sequence

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.modules.reports.domain.photos import ReportPhoto
from app.modules.reports.infrastructure.models import EvidenceModel, ReportModel


class SqlReportPhotoEraser:
    """Implementa ``ReportPhotoEraser``: quita la evidencia de los reportes del titular.

    El reporte se conserva sin foto, como dato de la vía (propuesta 39).
    """

    def __init__(self, session: Session) -> None:
        self._session = session

    def detach_photos(self, user_id: uuid.UUID) -> Sequence[str]:
        own_reports = select(ReportModel.id).where(ReportModel.user_id == user_id)
        keys = self._session.execute(
            delete(EvidenceModel)
            .where(EvidenceModel.report_id.in_(own_reports))
            .returning(EvidenceModel.photo_url)
        ).scalars()
        return sorted(keys)


class SqlEvidenceKeys:
    """Implementa ``EvidenceKeys``. Lee todas las claves: a la escala del MVP son pocas
    miles de filas de texto corto."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def referenced_photo_keys(self) -> Sequence[str]:
        return list(self._session.execute(select(EvidenceModel.photo_url)).scalars())


class SqlReportPhotoLookup:
    """Implementa ``ReportPhotoLookup``: dueño del reporte y su foto más reciente."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def find_photo(self, report_id: uuid.UUID) -> ReportPhoto | None:
        owner_id = self._session.execute(
            select(ReportModel.user_id).where(ReportModel.id == report_id)
        ).scalar_one_or_none()
        if owner_id is None:
            return None
        photo_key = self._session.execute(
            select(EvidenceModel.photo_url)
            .where(EvidenceModel.report_id == report_id)
            .order_by(EvidenceModel.uploaded_at.desc(), EvidenceModel.id)
            .limit(1)
        ).scalar_one_or_none()
        return ReportPhoto(owner_id=owner_id, photo_key=photo_key)
