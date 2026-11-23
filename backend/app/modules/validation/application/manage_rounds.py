"""Casos de uso de las rondas de evaluación (objetivo 4)."""

import secrets
import uuid

from app.modules.priority.application.evaluate_report import WeightsNotConfiguredError
from app.modules.priority.domain.ports import WeightVersionRepository
from app.modules.validation.domain.ports import RoundRepository, ZoneRepository
from app.modules.validation.domain.rounds import (
    NoZonesError,
    RoundAlreadyClosedError,
    RoundAlreadyOpenError,
    RoundNotFoundError,
    RoundProgress,
    RoundStatus,
    RoundSummary,
    sample_and_rank,
)
from app.shared.application.transaction import TransactionManager

SEED_BITS = 31


class OpenRound:
    """Congela la muestra de cada zona con su U y el orden del motor, en una transacción."""

    def __init__(
        self,
        zones: ZoneRepository,
        rounds: RoundRepository,
        weights: WeightVersionRepository,
        transaction: TransactionManager,
    ) -> None:
        self._zones = zones
        self._rounds = rounds
        self._weights = weights
        self._transaction = transaction

    def execute(self, name: str, sample_size: int, admin_id: uuid.UUID) -> uuid.UUID:
        try:
            round_id = self._open(name, sample_size, admin_id)
            self._transaction.commit()
        except BaseException:
            self._transaction.rollback()
            raise
        return round_id

    def _open(self, name: str, sample_size: int, admin_id: uuid.UUID) -> uuid.UUID:
        if self._rounds.has_open():
            raise RoundAlreadyOpenError
        zones = self._zones.list_with_counts()
        if not zones:
            raise NoZonesError
        version = self._weights.get_current()
        if version is None:
            raise WeightsNotConfiguredError
        seed = secrets.randbits(SEED_BITS)
        entries = sample_and_rank(
            self._rounds.list_candidates(),
            sample_size,
            seed,
            {zone.id: zone.name for zone in zones},
        )
        return self._rounds.add(
            name.strip(),
            sample_size=sample_size,
            seed=seed,
            config_id=version.id,
            admin_id=admin_id,
            entries=entries,
        )


class CloseRound:
    def __init__(self, rounds: RoundRepository, transaction: TransactionManager) -> None:
        self._rounds = rounds
        self._transaction = transaction

    def execute(self, round_id: uuid.UUID) -> None:
        try:
            status = self._rounds.lock_status(round_id)
            if status is None:
                raise RoundNotFoundError(round_id)
            if status is RoundStatus.CLOSED:
                raise RoundAlreadyClosedError(round_id)
            self._rounds.mark_closed(round_id)
            self._transaction.commit()
        except BaseException:
            self._transaction.rollback()
            raise


class ReadRounds:
    def __init__(self, rounds: RoundRepository) -> None:
        self._rounds = rounds

    def list(self, limit: int, offset: int) -> list[RoundSummary]:
        return self._rounds.list_rounds(limit, offset)

    def progress(self, round_id: uuid.UUID) -> RoundProgress:
        progress = self._rounds.get_progress(round_id)
        if progress is None:
            raise RoundNotFoundError(round_id)
        return progress
