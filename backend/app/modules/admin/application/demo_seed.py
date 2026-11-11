"""Caso de uso: cargar y borrar los datos de demostración del panel (decisión 76).

Son reportes sobre vías reales, evaluados por el motor real, para que el ranking y el
mapa de calor tengan contenido en las capturas y la demostración. **No son datos de
campo**: cuelgan de dos cuentas de ``@demo.invalid`` y se borran enteros con ``remove``.
"""

import uuid
from collections.abc import Iterator, Sequence
from typing import Protocol

from app.modules.admin.domain.demo import (
    DEMO_ADMIN_EMAIL,
    DEMO_ADMIN_NAME,
    DEMO_CITIZEN_EMAIL,
    DEMO_CITIZEN_NAME,
    DEMO_CREDENTIAL_MARKER,
    DEMO_DESCRIPTION,
    DEMO_PRIORITIZED_NOTE,
    DEMO_REPAIRED_NOTE,
    DEMO_REPORT_COUNT,
    DemoDataStore,
    DemoPoint,
    DemoPointSource,
    NotEnoughOsmDataError,
)
from app.modules.reports.domain.new_report import NewReport
from app.modules.reports.domain.photos import (
    STORED_PHOTO_FORMAT,
    PhotoKeys,
    ProcessedPhoto,
    StoredEvidence,
)
from app.modules.reports.domain.ports import (
    PhotoProcessor,
    PhotoStorage,
    PriorityEvaluator,
    StatusHistoryRecorder,
)
from app.modules.reports.domain.status import ReportStatus
from app.modules.reports.domain.status_machine import (
    StatusChange,
    change_status,
    initial_status_change,
)
from app.modules.users.domain.entities import NewUser, User
from app.modules.users.domain.ports import PhotoFileRemover
from app.modules.users.domain.role import UserRole
from app.shared.application.transaction import TransactionManager
from app.shared.domain.geo import BoundingBox

# Con 32 reportes: 8 quedan priorizados (posiciones 0, 4, 8…) y 4 reparados (2, 10, 18
# y 26). Como las severidades van en ciclo de tres, cada estado recibe las tres.
_PRIORITIZED_EVERY = 4
_REPAIRED_EVERY = 8
_REPAIRED_OFFSET = 2


class DemoUsers(Protocol):
    def get_by_email(self, email: str) -> User | None: ...

    def add(self, user: NewUser) -> User: ...


class DemoReports(Protocol):
    def add(self, report: NewReport) -> uuid.UUID: ...

    def add_evidence(self, report_id: uuid.UUID, evidence: StoredEvidence) -> None: ...


def _demo_user(name: str, email: str, role: UserRole) -> NewUser:
    # Sin consentimiento: la cuenta no es de una persona ni guarda datos personales.
    return NewUser(
        name=name, email=email, password_hash=DEMO_CREDENTIAL_MARKER, role=role, consent=None
    )


def _status_changes(position: int, admin_id: uuid.UUID) -> Iterator[StatusChange]:
    """Cambios posteriores a la evaluación, con la máquina de estados real."""
    prioritized = change_status(
        ReportStatus.EVALUATED,
        ReportStatus.PRIORITIZED,
        changed_by=admin_id,
        note=DEMO_PRIORITIZED_NOTE,
    )
    if position % _PRIORITIZED_EVERY == 0:
        yield prioritized
    elif position % _REPAIRED_EVERY == _REPAIRED_OFFSET:
        yield prioritized
        yield change_status(
            ReportStatus.PRIORITIZED,
            ReportStatus.REPAIRED,
            changed_by=admin_id,
            note=DEMO_REPAIRED_NOTE,
        )


class SeedDemo:
    def __init__(
        self,
        *,
        users: DemoUsers,
        points: DemoPointSource,
        reports: DemoReports,
        statuses: StatusHistoryRecorder,
        evaluator: PriorityEvaluator,
        photo_processor: PhotoProcessor,
        photo_storage: PhotoStorage,
        photo_files: PhotoFileRemover,
        demo_data: DemoDataStore,
        photos: Sequence[bytes],
        service_area: BoundingBox,
        transaction: TransactionManager,
    ) -> None:
        if not photos:
            raise ValueError("Se necesita al menos una foto de demostración")
        self._users = users
        self._points = points
        self._reports = reports
        self._statuses = statuses
        self._evaluator = evaluator
        self._photo_processor = photo_processor
        self._photo_storage = photo_storage
        self._photo_files = photo_files
        self._demo_data = demo_data
        self._photos = tuple(photos)
        self._service_area = service_area
        self._transaction = transaction

    def execute(self) -> int:
        """Crea los datos en una sola transacción y devuelve cuántos reportes creó; ``0``
        si ya existían. Lanza ``NotEnoughOsmDataError`` si faltan datos de OSM.
        """
        if self._users.get_by_email(DEMO_CITIZEN_EMAIL) is not None:
            return 0
        points = self._points.pick(self._service_area)
        if len(points) < DEMO_REPORT_COUNT:
            raise NotEnoughOsmDataError(
                f"Los datos de OSM solo dan para {len(points)} de {DEMO_REPORT_COUNT} puntos de "
                "demostración. Carga primero las vías y los servicios críticos: "
                "python -m app.cli osm-import"
            )
        photos = [self._photo_processor.process(raw) for raw in self._photos]

        saved: list[str] = []
        try:
            citizen = self._users.add(
                _demo_user(DEMO_CITIZEN_NAME, DEMO_CITIZEN_EMAIL, UserRole.CITIZEN)
            )
            admin = self._users.add(_demo_user(DEMO_ADMIN_NAME, DEMO_ADMIN_EMAIL, UserRole.ADMIN))
            for position, point in enumerate(points):
                photo = photos[position % len(photos)]
                report_id = self._add_report(citizen.id, point, photo, saved)
                for change in _status_changes(position, admin.id):
                    self._statuses.apply(report_id, change)
            self._transaction.commit()
        except Exception:
            self._transaction.rollback()
            # Los archivos no se revierten con la transacción: se borran a mano.
            self._photo_files.remove(saved)
            raise
        return len(points)

    def remove(self) -> int:
        """Borra los reportes y las cuentas de demostración; devuelve cuántos reportes."""
        try:
            removal = self._demo_data.delete_all()
            self._transaction.commit()
        except Exception:
            self._transaction.rollback()
            raise
        # Después de confirmar, como en la supresión (propuesta 39): si el borrado de
        # filas fallara, los reportes no deben quedar apuntando a fotos que ya no existen.
        self._photo_files.remove(removal.photo_keys)
        return removal.reports

    def _add_report(
        self, citizen_id: uuid.UUID, point: DemoPoint, photo: ProcessedPhoto, saved: list[str]
    ) -> uuid.UUID:
        """Mismos pasos que ``CreateReport``, sin cupo ni aviso de duplicado."""
        report = NewReport.create(
            user_id=citizen_id,
            location=point.location,
            severity=point.severity,
            description=DEMO_DESCRIPTION,
            idempotency_key=None,
            service_area=self._service_area,
        )
        keys = PhotoKeys.new()
        saved.append(keys.photo)
        self._photo_storage.save(keys.photo, photo.content)
        self._photo_storage.save(keys.thumbnail, photo.thumbnail)
        report_id = self._reports.add(report)
        self._statuses.apply(report_id, initial_status_change(citizen_id))
        self._reports.add_evidence(
            report_id, StoredEvidence(keys.photo, STORED_PHOTO_FORMAT, len(photo.content))
        )
        # El motor real calcula S, F, P y U y pasa el reporte a evaluado.
        self._evaluator.evaluate(report_id)
        return report_id
