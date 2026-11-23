"""Casos de uso del evaluador: vista a ciegas y envío del orden (objetivo 4, HU-09)."""

import logging
import uuid
from collections.abc import Sequence

from app.modules.reports.domain.photos import PhotoKeys
from app.modules.reports.domain.ports import PhotoNotStoredError, PhotoReader
from app.modules.validation.domain.blind import (
    BlindPhotoNotAvailableError,
    CurrentRoundView,
    NoOpenRoundError,
    OpenRoundRef,
    OrderAlreadySubmittedError,
    ZoneNotInRoundError,
    ZoneView,
    shuffle_for,
    validate_order,
)
from app.modules.validation.domain.ports import BlindEvaluationRepository
from app.shared.application.transaction import TransactionManager

logger = logging.getLogger(__name__)


def _open_round(repository: BlindEvaluationRepository, *, lock: bool = False) -> OpenRoundRef:
    found = repository.find_open_round(lock=lock)
    if found is None:
        raise NoOpenRoundError
    return found


class ViewCurrentRound:
    def __init__(self, repository: BlindEvaluationRepository) -> None:
        self._repository = repository

    def execute(self, evaluator_id: uuid.UUID) -> CurrentRoundView:
        current = _open_round(self._repository)
        return CurrentRoundView(
            round_id=current.round_id,
            name=current.name,
            zones=self._repository.list_zones(current.round_id, evaluator_id),
        )


class ViewZone:
    """Tarjetas a ciegas de una zona, en el orden inicial propio del evaluador."""

    def __init__(self, repository: BlindEvaluationRepository) -> None:
        self._repository = repository

    def execute(self, evaluator_id: uuid.UUID, zone_id: int) -> ZoneView:
        current = _open_round(self._repository)
        zone = self._repository.get_zone(current.round_id, zone_id)
        if zone is None:
            raise ZoneNotInRoundError(zone_id)
        cards = {
            card.report_id: card for card in self._repository.zone_cards(current.round_id, zone_id)
        }
        order = shuffle_for(cards, current.seed, evaluator_id)
        return ZoneView(
            zone=zone,
            cards=[cards[report_id] for report_id in order],
            submitted=self._repository.has_submitted(current.round_id, evaluator_id, zone_id),
        )


class SubmitOrder:
    """Guarda, una sola vez y en una transacción, el orden del evaluador para una zona."""

    def __init__(
        self, repository: BlindEvaluationRepository, transaction: TransactionManager
    ) -> None:
        self._repository = repository
        self._transaction = transaction

    def execute(
        self, evaluator_id: uuid.UUID, zone_id: int, report_ids: Sequence[uuid.UUID]
    ) -> None:
        try:
            self._submit(evaluator_id, zone_id, report_ids)
            self._transaction.commit()
        except BaseException:
            self._transaction.rollback()
            raise

    def _submit(
        self, evaluator_id: uuid.UUID, zone_id: int, report_ids: Sequence[uuid.UUID]
    ) -> None:
        # Bloqueo compartido: la ronda no se cierra mientras se guarda el orden.
        current = _open_round(self._repository, lock=True)
        if self._repository.get_zone(current.round_id, zone_id) is None:
            raise ZoneNotInRoundError(zone_id)
        if self._repository.has_submitted(current.round_id, evaluator_id, zone_id):
            raise OrderAlreadySubmittedError
        validate_order(self._repository.zone_report_ids(current.round_id, zone_id), report_ids)
        self._repository.save_order(current.round_id, evaluator_id, report_ids)


class GetBlindPhoto:
    """Foto de un reporte de la ronda abierta; cualquier otro reporte responde igual (404)."""

    def __init__(self, repository: BlindEvaluationRepository, reader: PhotoReader) -> None:
        self._repository = repository
        self._reader = reader

    def execute(self, report_id: uuid.UUID, *, thumbnail: bool) -> bytes:
        current = self._repository.find_open_round()
        photo_key = (
            None if current is None else self._repository.photo_key(current.round_id, report_id)
        )
        if photo_key is None:
            raise BlindPhotoNotAvailableError(str(report_id))
        keys = PhotoKeys.from_photo_key(photo_key)
        key = keys.thumbnail if thumbnail else keys.photo
        try:
            return self._reader.read(key)
        except PhotoNotStoredError as exc:
            # La fila existe pero el archivo no: inconsistencia que hay que revisar.
            logger.error("Falta el archivo de la foto %s", key)
            raise BlindPhotoNotAvailableError(str(report_id)) from exc
