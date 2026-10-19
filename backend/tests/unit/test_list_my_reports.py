"""Caso de uso ListMyReports: reportes creados y confirmados por el usuario."""

import uuid

import pytest

from app.modules.reports.application.list_my_reports import ListMyReports
from app.modules.reports.domain.my_reports import MAX_PAGE_SIZE, MyReportsPage

USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


class FakeReader:
    def __init__(self) -> None:
        self.calls: list[tuple[uuid.UUID, int, int]] = []

    def list_for_user(self, user_id: uuid.UUID, limit: int, offset: int) -> MyReportsPage:
        self.calls.append((user_id, limit, offset))
        return MyReportsPage(items=(), total=0, limit=limit, offset=offset)


def test_reader_receives_the_user_and_page() -> None:
    reader = FakeReader()

    page = ListMyReports(reader).execute(USER_ID, limit=20, offset=40)

    assert reader.calls == [(USER_ID, 20, 40)]
    assert (page.limit, page.offset) == (20, 40)


def test_page_size_is_capped() -> None:
    with pytest.raises(ValueError, match="limit"):
        ListMyReports(FakeReader()).execute(USER_ID, limit=MAX_PAGE_SIZE + 1, offset=0)


def test_page_size_must_be_positive() -> None:
    with pytest.raises(ValueError, match="limit"):
        ListMyReports(FakeReader()).execute(USER_ID, limit=0, offset=0)


def test_negative_offset_is_rejected() -> None:
    with pytest.raises(ValueError, match="offset"):
        ListMyReports(FakeReader()).execute(USER_ID, limit=20, offset=-1)
