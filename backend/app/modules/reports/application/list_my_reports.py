"""Caso de uso: «Mis reportes», creados y confirmados (decisión 49)."""

import uuid

from app.modules.reports.domain.my_reports import MAX_PAGE_SIZE, MyReportsPage
from app.modules.reports.domain.ports import MyReportsReader


class ListMyReports:
    def __init__(self, reader: MyReportsReader) -> None:
        self._reader = reader

    def execute(self, user_id: uuid.UUID, limit: int, offset: int) -> MyReportsPage:
        if not 1 <= limit <= MAX_PAGE_SIZE:
            raise ValueError(f"limit debe estar entre 1 y {MAX_PAGE_SIZE}")
        if offset < 0:
            raise ValueError("offset no puede ser negativo")
        return self._reader.list_for_user(user_id, limit, offset)
