"""Caso de uso ManageWeights: versión vigente, historial de versiones y guardar (HU-14)."""

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from app.modules.admin.application.manage_weights import ManageWeights
from app.modules.admin.domain.ranking_view import MAX_PAGE_SIZE
from app.modules.admin.domain.weights_view import WeightVersionView
from app.modules.priority.application.evaluate_report import WeightsNotConfiguredError
from app.modules.priority.application.update_weights import WeightsUpdateResult
from app.modules.priority.domain.entities import WeightVersion
from app.modules.priority.domain.weights import DEFAULT_WEIGHTS, Weights

ADMIN_ID = uuid.UUID("00000000-0000-0000-0000-0000000000ad")
NOW = datetime(2026, 11, 9, tzinfo=UTC)
NEW_WEIGHTS = Weights(Decimal("0.40"), Decimal("0.40"), Decimal("0.20"))


def _view(version_id: int, weights: Weights = DEFAULT_WEIGHTS) -> WeightVersionView:
    return WeightVersionView(
        id=version_id, weights=weights, created_at=NOW, created_by_name=None, is_current=True
    )


class FakeReader:
    def __init__(self, current: WeightVersionView | None) -> None:
        self.current_view = current
        self.pages: list[tuple[int, int]] = []

    def current(self) -> WeightVersionView | None:
        return self.current_view

    def list_versions(self, limit: int, offset: int) -> Sequence[WeightVersionView]:
        self.pages.append((limit, offset))
        return ()


class FakeUpdate:
    def __init__(self, reader: FakeReader) -> None:
        self.reader = reader
        self.calls: list[tuple[Weights, uuid.UUID, int]] = []

    def execute(
        self, weights: Weights, admin_id: uuid.UUID, base_version_id: int
    ) -> WeightsUpdateResult:
        self.calls.append((weights, admin_id, base_version_id))
        self.reader.current_view = _view(base_version_id + 1, weights)
        version = WeightVersion(base_version_id + 1, weights, admin_id, NOW, is_current=True)
        return WeightsUpdateResult(version=version, recalculated_reports=4)


def _manage(reader: FakeReader) -> tuple[ManageWeights, FakeUpdate]:
    update = FakeUpdate(reader)
    return ManageWeights(reader, update), update  # type: ignore[arg-type]


def test_current_returns_the_current_version() -> None:
    manage, _ = _manage(FakeReader(_view(1)))

    assert manage.current() == _view(1)


def test_current_without_versions_raises() -> None:
    manage, _ = _manage(FakeReader(None))

    with pytest.raises(WeightsNotConfiguredError):
        manage.current()


def test_versions_pass_the_page_to_the_reader() -> None:
    reader = FakeReader(_view(1))
    manage, _ = _manage(reader)

    manage.versions(limit=10, offset=20)

    assert reader.pages == [(10, 20)]


@pytest.mark.parametrize(("limit", "offset"), [(0, 0), (MAX_PAGE_SIZE + 1, 0), (10, -1)])
def test_versions_reject_bad_pages(limit: int, offset: int) -> None:
    manage, _ = _manage(FakeReader(_view(1)))

    with pytest.raises(ValueError, match=r"limit|offset"):
        manage.versions(limit=limit, offset=offset)


def test_save_delegates_and_returns_the_new_current_version() -> None:
    manage, update = _manage(FakeReader(_view(1)))

    saved = manage.save(NEW_WEIGHTS, ADMIN_ID, base_version_id=1)

    assert update.calls == [(NEW_WEIGHTS, ADMIN_ID, 1)]
    assert saved.version == _view(2, NEW_WEIGHTS)
    assert saved.recalculated_reports == 4
