"""Caso de uso: detalle completo de un reporte para el administrador."""

import uuid

from app.modules.admin.domain.errors import ReportNotFoundError
from app.modules.admin.domain.ports import AdminReportReader
from app.modules.admin.domain.report_detail import AdminReportDetail


class GetAdminReport:
    def __init__(self, reader: AdminReportReader) -> None:
        self._reader = reader

    def execute(self, report_id: uuid.UUID) -> AdminReportDetail:
        detail = self._reader.get(report_id)
        if detail is None:
            raise ReportNotFoundError(str(report_id))
        return detail
