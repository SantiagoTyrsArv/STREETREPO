"""Evaluación a ciegas en PostgreSQL (consultas parametrizadas).

Cada SELECT de este archivo lista solo lo que puede ver el evaluador: nunca ``puntaje_u``,
``orden_motor``, ``puntaje_prioridad``, la evaluación, la jerarquía vial, distancias,
confirmaciones, estado, fechas, autor ni órdenes de otros evaluadores.
"""

import uuid
from collections import defaultdict
from collections.abc import Sequence

from sqlalchemy import insert, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modules.critical_services.domain.service_type import CriticalServiceType
from app.modules.reports.domain.severity import Severity
from app.modules.validation.domain.blind import (
    BlindCard,
    BlindZone,
    EvaluatorZone,
    OpenRoundRef,
    OrderAlreadySubmittedError,
    ServicePoint,
)
from app.modules.validation.infrastructure.models import EvaluatorOrderModel
from app.shared.domain.geo import GeoPoint
from app.shared.domain.geo_parameters import PROXIMITY_MAX_RADIUS_M

EVALUATOR_ORDER_PK = "orden_evaluador_pkey"

_OPEN_ROUND = "SELECT id_ronda, nombre, semilla FROM ronda_evaluacion WHERE estado = 'abierta'"
_FIND_OPEN_ROUND = text(_OPEN_ROUND)
# Compartido: varios evaluadores envían a la vez; el cierre (FOR UPDATE) espera a que terminen.
_LOCK_OPEN_ROUND = text(f"{_OPEN_ROUND} FOR SHARE")
_ZONES = text(
    """
    SELECT z.id_zona, z.nombre, count(*) AS n_reportes,
           EXISTS (
               SELECT 1 FROM orden_evaluador oe
               JOIN ronda_reporte r2
                 ON r2.id_ronda = oe.id_ronda AND r2.id_reporte = oe.id_reporte
               WHERE oe.id_ronda = :round_id AND oe.id_usuario = :user_id
                 AND r2.id_zona = z.id_zona
           ) AS enviado
    FROM ronda_reporte rr JOIN zona z ON z.id_zona = rr.id_zona
    WHERE rr.id_ronda = :round_id
    GROUP BY z.id_zona, z.nombre
    ORDER BY z.nombre
    """
)
_ZONE = text(
    """
    SELECT z.id_zona, z.nombre, count(*) AS n_reportes
    FROM ronda_reporte rr JOIN zona z ON z.id_zona = rr.id_zona
    WHERE rr.id_ronda = :round_id AND rr.id_zona = :zone_id
    GROUP BY z.id_zona, z.nombre
    """
)
_ZONE_REPORT_IDS = text(
    "SELECT id_reporte FROM ronda_reporte WHERE id_ronda = :round_id AND id_zona = :zone_id"
)
_CARDS = text(
    """
    SELECT r.id_reporte, r.descripcion, v.nombre AS via, r.severidad,
           ST_X(r.ubicacion) AS lon, ST_Y(r.ubicacion) AS lat
    FROM ronda_reporte rr
    JOIN reporte r ON r.id_reporte = rr.id_reporte
    LEFT JOIN via v ON v.id_via = r.id_via
    WHERE rr.id_ronda = :round_id AND rr.id_zona = :zone_id
    ORDER BY r.id_reporte
    """
)
# Sin la distancia: el minimapa muestra dónde están, no cuánto mide el motor.
_SERVICES = text(
    """
    SELECT rr.id_reporte, s.nombre, s.tipo,
           ST_X(s.ubicacion) AS lon, ST_Y(s.ubicacion) AS lat
    FROM ronda_reporte rr
    JOIN reporte r ON r.id_reporte = rr.id_reporte
    JOIN servicio_critico s
      ON ST_DWithin(s.ubicacion::geography, r.ubicacion::geography, :radius_m)
    WHERE rr.id_ronda = :round_id AND rr.id_zona = :zone_id
    ORDER BY rr.id_reporte, s.id_servicio
    """
)
_HAS_SUBMITTED = text(
    """
    SELECT EXISTS (
        SELECT 1 FROM orden_evaluador oe
        JOIN ronda_reporte rr ON rr.id_ronda = oe.id_ronda AND rr.id_reporte = oe.id_reporte
        WHERE oe.id_ronda = :round_id AND oe.id_usuario = :user_id AND rr.id_zona = :zone_id
    )
    """
)
_PHOTO_KEY = text(
    """
    SELECT e.url_foto
    FROM ronda_reporte rr JOIN evidencia e ON e.id_reporte = rr.id_reporte
    WHERE rr.id_ronda = :round_id AND rr.id_reporte = :report_id
    ORDER BY e.fecha_subida DESC, e.id_evidencia
    LIMIT 1
    """
)


def _violated_constraint(exc: IntegrityError) -> str | None:
    diag = getattr(exc.orig, "diag", None)
    name = getattr(diag, "constraint_name", None)
    return name if isinstance(name, str) else None


class SqlBlindEvaluationRepository:
    """Implementa ``BlindEvaluationRepository``. No confirma: lo hace el caso de uso."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def find_open_round(self, *, lock: bool = False) -> OpenRoundRef | None:
        row = self._session.execute(_LOCK_OPEN_ROUND if lock else _FIND_OPEN_ROUND).one_or_none()
        if row is None:
            return None
        return OpenRoundRef(round_id=row.id_ronda, name=row.nombre, seed=row.semilla)

    def list_zones(self, round_id: uuid.UUID, evaluator_id: uuid.UUID) -> list[EvaluatorZone]:
        rows = self._session.execute(_ZONES, {"round_id": round_id, "user_id": evaluator_id})
        return [
            EvaluatorZone(BlindZone(row.id_zona, row.nombre, row.n_reportes), bool(row.enviado))
            for row in rows
        ]

    def get_zone(self, round_id: uuid.UUID, zone_id: int) -> BlindZone | None:
        row = self._session.execute(_ZONE, {"round_id": round_id, "zone_id": zone_id}).one_or_none()
        return None if row is None else BlindZone(row.id_zona, row.nombre, row.n_reportes)

    def zone_report_ids(self, round_id: uuid.UUID, zone_id: int) -> list[uuid.UUID]:
        return list(
            self._session.execute(
                _ZONE_REPORT_IDS, {"round_id": round_id, "zone_id": zone_id}
            ).scalars()
        )

    def zone_cards(self, round_id: uuid.UUID, zone_id: int) -> list[BlindCard]:
        params = {"round_id": round_id, "zone_id": zone_id}
        services: dict[uuid.UUID, list[ServicePoint]] = defaultdict(list)
        for row in self._session.execute(_SERVICES, params | {"radius_m": PROXIMITY_MAX_RADIUS_M}):
            services[row.id_reporte].append(
                ServicePoint(
                    name=row.nombre,
                    type=CriticalServiceType(row.tipo),
                    location=GeoPoint(row.lon, row.lat),
                )
            )
        return [
            BlindCard(
                report_id=row.id_reporte,
                description=row.descripcion,
                road_name=row.via,
                severity=Severity(row.severidad),
                location=GeoPoint(row.lon, row.lat),
                nearby_services=services.get(row.id_reporte, []),
            )
            for row in self._session.execute(_CARDS, params)
        ]

    def has_submitted(self, round_id: uuid.UUID, evaluator_id: uuid.UUID, zone_id: int) -> bool:
        return bool(
            self._session.execute(
                _HAS_SUBMITTED,
                {"round_id": round_id, "user_id": evaluator_id, "zone_id": zone_id},
            ).scalar_one()
        )

    def save_order(
        self, round_id: uuid.UUID, evaluator_id: uuid.UUID, report_ids: Sequence[uuid.UUID]
    ) -> None:
        rows = [
            {
                "round_id": round_id,
                "user_id": evaluator_id,
                "report_id": report_id,
                "position": position,
            }
            for position, report_id in enumerate(report_ids, start=1)
        ]
        try:
            # La clave primaria (ronda, usuario, reporte) frena el doble envío simultáneo.
            self._session.execute(insert(EvaluatorOrderModel), rows)
            self._session.flush()
        except IntegrityError as exc:
            if _violated_constraint(exc) == EVALUATOR_ORDER_PK:
                raise OrderAlreadySubmittedError from exc
            raise

    def photo_key(self, round_id: uuid.UUID, report_id: uuid.UUID) -> str | None:
        key: str | None = self._session.execute(
            _PHOTO_KEY, {"round_id": round_id, "report_id": report_id}
        ).scalar_one_or_none()
        return key
