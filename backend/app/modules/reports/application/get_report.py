"""Caso de uso: detalle de un reporte para su autor, un administrador o quien lo confirmó."""

import dataclasses
import uuid

from app.modules.reports.application.get_photo import PhotoViewer
from app.modules.reports.domain.ports import ReportViewReader
from app.modules.reports.domain.report_view import (
    FullReportView,
    LimitedReportView,
    ReportNotVisibleError,
)


class GetReport:
    def __init__(self, reader: ReportViewReader) -> None:
        self._reader = reader

    def execute(
        self, report_id: uuid.UUID, viewer: PhotoViewer
    ) -> FullReportView | LimitedReportView:
        details = self._reader.get_details(report_id)
        if details is None:
            raise ReportNotVisibleError(str(report_id))
        # El rol manda sobre la relación: un administrador siempre ve el reporte completo.
        if viewer.is_admin or details.user_id == viewer.user_id:
            return FullReportView(
                details=details,
                confirmations=self._reader.confirmations(report_id),
                history=tuple(self._reader.history(report_id)),
                is_own=details.user_id == viewer.user_id,
            )
        confirmed_at = self._reader.confirmed_at(report_id, viewer.user_id)
        public = self._reader.public_view(report_id)
        if confirmed_at is None or public is None:
            raise ReportNotVisibleError(str(report_id))
        return LimitedReportView(
            public=public,
            confirmed_at=confirmed_at,
            history=tuple(
                dataclasses.replace(entry, note=None) for entry in self._reader.history(report_id)
            ),
        )
