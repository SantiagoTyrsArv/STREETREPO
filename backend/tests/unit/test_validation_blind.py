"""Evaluación a ciegas: orden inicial por evaluador, validación del orden y casos de uso."""

import dataclasses
import random
import uuid
from collections.abc import Sequence

import pytest

from app.modules.critical_services.domain.service_type import CriticalServiceType
from app.modules.reports.domain.photos import PhotoKeys
from app.modules.reports.domain.ports import PhotoNotStoredError
from app.modules.reports.domain.severity import Severity
from app.modules.validation.application.blind_evaluation import (
    GetBlindPhoto,
    SubmitOrder,
    ViewCurrentRound,
    ViewZone,
)
from app.modules.validation.domain.blind import (
    BlindCard,
    BlindPhotoNotAvailableError,
    BlindZone,
    EvaluatorZone,
    InvalidOrderError,
    NoOpenRoundError,
    OpenRoundRef,
    OrderAlreadySubmittedError,
    ServicePoint,
    ZoneNotInRoundError,
    shuffle_for,
    validate_order,
)
from app.shared.domain.geo import GeoPoint

ROUND = OpenRoundRef(round_id=uuid.UUID(int=900), name="Piloto 1", seed=12345)
EVALUATOR_A = uuid.UUID("00000000-0000-0000-0000-00000000000a")
EVALUATOR_B = uuid.UUID("00000000-0000-0000-0000-00000000000b")
ZONE = BlindZone(id=1, name="Centro", n_reports=6)
OTHER_ZONE = BlindZone(id=2, name="Obonuco", n_reports=5)
IDS = [uuid.UUID(int=n) for n in range(1, 7)]
OTHER_IDS = [uuid.UUID(int=n) for n in range(101, 106)]


def _card(report_id: uuid.UUID) -> BlindCard:
    return BlindCard(
        report_id=report_id,
        description="Hueco",
        road_name="Carrera 27",
        severity=Severity.HIGH,
        location=GeoPoint(-77.28, 1.21),
        nearby_services=[
            ServicePoint("Hospital", CriticalServiceType.HOSPITAL, GeoPoint(-77.281, 1.211))
        ],
    )


# --- dominio --------------------------------------------------------------------------


def test_blind_card_has_only_the_allowed_fields() -> None:
    names = {field.name for field in dataclasses.fields(BlindCard)}

    assert names == {
        "report_id",
        "description",
        "road_name",
        "severity",
        "location",
        "nearby_services",
    }


def test_blind_zone_does_not_carry_the_concentration() -> None:
    assert {field.name for field in dataclasses.fields(BlindZone)} == {"id", "name", "n_reports"}


def test_service_point_does_not_carry_the_distance() -> None:
    assert {field.name for field in dataclasses.fields(ServicePoint)} == {
        "name",
        "type",
        "location",
    }


def test_shuffle_is_a_permutation_and_stable() -> None:
    first = shuffle_for(IDS, ROUND.seed, EVALUATOR_A)

    assert sorted(first) == sorted(IDS)
    assert shuffle_for(IDS, ROUND.seed, EVALUATOR_A) == first


def test_shuffle_does_not_depend_on_the_input_order() -> None:
    assert shuffle_for(list(reversed(IDS)), ROUND.seed, EVALUATOR_A) == shuffle_for(
        IDS, ROUND.seed, EVALUATOR_A
    )


def test_shuffle_differs_between_evaluators() -> None:
    assert shuffle_for(IDS, ROUND.seed, EVALUATOR_A) != shuffle_for(IDS, ROUND.seed, EVALUATOR_B)


def test_shuffle_follows_the_documented_formula() -> None:
    expected = sorted(IDS)
    random.Random(f"{ROUND.seed}:{EVALUATOR_A}").shuffle(expected)  # noqa: S311

    assert shuffle_for(IDS, ROUND.seed, EVALUATOR_A) == expected


def test_valid_order_passes() -> None:
    validate_order(set(IDS), list(reversed(IDS)))


@pytest.mark.parametrize(
    "submitted",
    [
        pytest.param([], id="vacio"),
        pytest.param([*IDS[:-1], IDS[0]], id="repetido"),
        pytest.param(IDS[:-1], id="faltante"),
        pytest.param([*IDS[:-1], OTHER_IDS[0]], id="de-otra-zona"),
        pytest.param([*IDS, OTHER_IDS[0]], id="sobrante"),
        pytest.param([*IDS, IDS[0]], id="todos-y-un-repetido"),
    ],
)
def test_invalid_orders_are_rejected(submitted: list[uuid.UUID]) -> None:
    with pytest.raises(InvalidOrderError):
        validate_order(set(IDS), submitted)


# --- casos de uso -----------------------------------------------------------------------


class FakeRepository:
    def __init__(self, *, open_round: OpenRoundRef | None = ROUND) -> None:
        self.open_round = open_round
        self.zones = {ZONE.id: (ZONE, IDS), OTHER_ZONE.id: (OTHER_ZONE, OTHER_IDS)}
        self.submitted: set[tuple[uuid.UUID, int]] = set()
        self.saved: list[tuple[uuid.UUID, uuid.UUID, list[uuid.UUID]]] = []
        self.locked = False
        self.race = False
        self.photos: dict[uuid.UUID, str] = {}

    def find_open_round(self, *, lock: bool = False) -> OpenRoundRef | None:
        self.locked = self.locked or lock
        return self.open_round

    def list_zones(self, round_id: uuid.UUID, evaluator_id: uuid.UUID) -> list[EvaluatorZone]:
        return [
            EvaluatorZone(zone, (evaluator_id, zone.id) in self.submitted)
            for zone, _ in self.zones.values()
        ]

    def get_zone(self, round_id: uuid.UUID, zone_id: int) -> BlindZone | None:
        found = self.zones.get(zone_id)
        return None if found is None else found[0]

    def zone_report_ids(self, round_id: uuid.UUID, zone_id: int) -> list[uuid.UUID]:
        return list(self.zones[zone_id][1])

    def zone_cards(self, round_id: uuid.UUID, zone_id: int) -> list[BlindCard]:
        return [_card(report_id) for report_id in self.zones[zone_id][1]]

    def has_submitted(self, round_id: uuid.UUID, evaluator_id: uuid.UUID, zone_id: int) -> bool:
        return (evaluator_id, zone_id) in self.submitted

    def save_order(
        self, round_id: uuid.UUID, evaluator_id: uuid.UUID, report_ids: Sequence[uuid.UUID]
    ) -> None:
        if self.race:
            raise OrderAlreadySubmittedError
        self.saved.append((round_id, evaluator_id, list(report_ids)))

    def photo_key(self, round_id: uuid.UUID, report_id: uuid.UUID) -> str | None:
        return self.photos.get(report_id)


class FakeTransaction:
    def __init__(self) -> None:
        self.commits = 0
        self.rollbacks = 0

    def commit(self) -> None:
        self.commits += 1

    def rollback(self) -> None:
        self.rollbacks += 1


class FakeReader:
    def __init__(self, files: dict[str, bytes]) -> None:
        self.files = files

    def read(self, key: str) -> bytes:
        try:
            return self.files[key]
        except KeyError as exc:
            raise PhotoNotStoredError(key) from exc


def test_current_round_lists_zones_with_submitted_flag() -> None:
    repo = FakeRepository()
    repo.submitted.add((EVALUATOR_A, ZONE.id))

    view = ViewCurrentRound(repo).execute(EVALUATOR_A)

    assert (view.round_id, view.name) == (ROUND.round_id, ROUND.name)
    assert view.zones == [EvaluatorZone(ZONE, True), EvaluatorZone(OTHER_ZONE, False)]


def test_current_round_without_open_round_fails() -> None:
    with pytest.raises(NoOpenRoundError):
        ViewCurrentRound(FakeRepository(open_round=None)).execute(EVALUATOR_A)


def test_zone_view_shuffles_cards_per_evaluator() -> None:
    repo = FakeRepository()

    view_a = ViewZone(repo).execute(EVALUATOR_A, ZONE.id)
    view_b = ViewZone(repo).execute(EVALUATOR_B, ZONE.id)

    assert view_a.zone == ZONE
    assert view_a.submitted is False
    assert [c.report_id for c in view_a.cards] == shuffle_for(IDS, ROUND.seed, EVALUATOR_A)
    assert [c.report_id for c in view_b.cards] == shuffle_for(IDS, ROUND.seed, EVALUATOR_B)


def test_zone_view_reports_submission() -> None:
    repo = FakeRepository()
    repo.submitted.add((EVALUATOR_A, ZONE.id))

    assert ViewZone(repo).execute(EVALUATOR_A, ZONE.id).submitted is True


def test_zone_view_of_a_zone_outside_the_round_fails() -> None:
    with pytest.raises(ZoneNotInRoundError):
        ViewZone(FakeRepository()).execute(EVALUATOR_A, 99)


def test_zone_view_without_open_round_fails() -> None:
    with pytest.raises(NoOpenRoundError):
        ViewZone(FakeRepository(open_round=None)).execute(EVALUATOR_A, ZONE.id)


def test_submit_saves_the_order_and_commits() -> None:
    repo, tx = FakeRepository(), FakeTransaction()
    order = list(reversed(IDS))

    SubmitOrder(repo, tx).execute(EVALUATOR_A, ZONE.id, order)

    assert repo.saved == [(ROUND.round_id, EVALUATOR_A, order)]
    assert repo.locked is True
    assert (tx.commits, tx.rollbacks) == (1, 0)


def test_submit_rejects_an_invalid_order_without_saving() -> None:
    repo, tx = FakeRepository(), FakeTransaction()

    with pytest.raises(InvalidOrderError):
        SubmitOrder(repo, tx).execute(EVALUATOR_A, ZONE.id, [*IDS[:-1], OTHER_IDS[0]])

    assert repo.saved == []
    assert (tx.commits, tx.rollbacks) == (0, 1)


def test_submit_twice_is_rejected() -> None:
    repo, tx = FakeRepository(), FakeTransaction()
    repo.submitted.add((EVALUATOR_A, ZONE.id))

    with pytest.raises(OrderAlreadySubmittedError):
        SubmitOrder(repo, tx).execute(EVALUATOR_A, ZONE.id, IDS)

    assert repo.saved == []
    assert tx.rollbacks == 1


def test_submit_race_is_reported_as_already_submitted() -> None:
    repo, tx = FakeRepository(), FakeTransaction()
    repo.race = True

    with pytest.raises(OrderAlreadySubmittedError):
        SubmitOrder(repo, tx).execute(EVALUATOR_A, ZONE.id, IDS)

    assert (tx.commits, tx.rollbacks) == (0, 1)


def test_submit_without_open_round_fails() -> None:
    tx = FakeTransaction()

    with pytest.raises(NoOpenRoundError):
        SubmitOrder(FakeRepository(open_round=None), tx).execute(EVALUATOR_A, ZONE.id, IDS)

    assert tx.rollbacks == 1


def test_submit_to_a_zone_outside_the_round_fails() -> None:
    tx = FakeTransaction()

    with pytest.raises(ZoneNotInRoundError):
        SubmitOrder(FakeRepository(), tx).execute(EVALUATOR_A, 99, IDS)

    assert tx.rollbacks == 1


def test_photo_of_a_report_in_the_round() -> None:
    repo = FakeRepository()
    keys = PhotoKeys.for_name("ab" * 16)
    repo.photos[IDS[0]] = keys.photo
    reader = FakeReader({keys.photo: b"foto", keys.thumbnail: b"mini"})

    use_case = GetBlindPhoto(repo, reader)

    assert use_case.execute(IDS[0], thumbnail=False) == b"foto"
    assert use_case.execute(IDS[0], thumbnail=True) == b"mini"


def test_photo_outside_the_round_or_without_file_is_not_available() -> None:
    repo = FakeRepository()
    keys = PhotoKeys.for_name("cd" * 16)
    repo.photos[IDS[1]] = keys.photo
    use_case = GetBlindPhoto(repo, FakeReader({}))

    with pytest.raises(BlindPhotoNotAvailableError):
        use_case.execute(IDS[0], thumbnail=False)
    with pytest.raises(BlindPhotoNotAvailableError):
        use_case.execute(IDS[1], thumbnail=False)


def test_photo_without_open_round_is_not_available() -> None:
    with pytest.raises(BlindPhotoNotAvailableError):
        GetBlindPhoto(FakeRepository(open_round=None), FakeReader({})).execute(
            IDS[0], thumbnail=True
        )
