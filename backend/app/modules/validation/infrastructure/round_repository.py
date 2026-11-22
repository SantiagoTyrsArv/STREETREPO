"""Rondas de evaluación en PostgreSQL (consultas parametrizadas)."""

import uuid
from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import select, text, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modules.reports.domain.severity import Severity
from app.modules.reports.domain.status import ReportStatus
from app.modules.validation.domain.rounds import (
    EvaluatorLabel,
    RoundAlreadyOpenError,
    RoundCandidate,
    RoundEntry,
    RoundProgress,
    RoundStatus,
    RoundSummary,
    ZoneProgress,
)
from app.modules.validation.domain.zones import Concentration
from app.modules.validation.infrastructure.models import (
    EvaluationRoundModel,
    RoundReportModel,
)

ONE_OPEN_ROUND_INDEX = "uq_ronda_abierta"

_HAS_OPEN = text("SELECT EXISTS (SELECT 1 FROM ronda_evaluacion WHERE estado = 'abierta')")
_CANDIDATES = text(
    """
    SELECT r.id_reporte, r.id_zona, r.puntaje_prioridad, r.severidad, r.fecha_creacion,
           (SELECT count(*) FROM confirmacion AS cf
             WHERE cf.id_reporte = r.id_reporte) AS confirmaciones
    FROM reporte AS r
    WHERE r.id_zona IS NOT NULL
      AND r.puntaje_prioridad IS NOT NULL
      AND r.estado <> CAST(:repaired AS estado_reporte)
    """
)
_PROGRESS_ZONES = text(
    """
    SELECT z.id_zona, z.nombre, CAST(z.concentracion AS text) AS concentracion,
           count(*) AS n_reportes
    FROM ronda_reporte rr JOIN zona z ON z.id_zona = rr.id_zona
    WHERE rr.id_ronda = :round_id
    GROUP BY z.id_zona, z.nombre, z.concentracion
    ORDER BY z.nombre
    """
)
# Primer envío de cada evaluador por zona; la etiqueta se numera por su primer envío en la ronda.
_PROGRESS_EVALUATORS = text(
    """
    SELECT oe.id_usuario, rr.id_zona, min(oe.fecha_envio) AS primer_envio
    FROM orden_evaluador oe
    JOIN ronda_reporte rr ON rr.id_ronda = oe.id_ronda AND rr.id_reporte = oe.id_reporte
    WHERE oe.id_ronda = :round_id
    GROUP BY oe.id_usuario, rr.id_zona
    """
)


def _violated_constraint(exc: IntegrityError) -> str | None:
    diag = getattr(exc.orig, "diag", None)
    name = getattr(diag, "constraint_name", None)
    return name if isinstance(name, str) else None


def _to_summary(row: EvaluationRoundModel) -> RoundSummary:
    return RoundSummary(
        round_id=row.id,
        name=row.name,
        status=RoundStatus(row.state),
        sample_size=row.sample_size,
        opened_at=row.opened_at,
        closed_at=row.closed_at,
    )


class SqlRoundRepository:
    """Implementa ``RoundRepository``. No confirma: lo hace el caso de uso."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def has_open(self) -> bool:
        return bool(self._session.execute(_HAS_OPEN).scalar_one())

    def list_candidates(self) -> list[RoundCandidate]:
        rows = self._session.execute(_CANDIDATES, {"repaired": ReportStatus.REPAIRED.value})
        return [
            RoundCandidate(
                report_id=row.id_reporte,
                zone_id=row.id_zona,
                urgency_score=row.puntaje_prioridad,
                severity=Severity(row.severidad),
                confirmations=row.confirmaciones,
                created_at=row.fecha_creacion,
            )
            for row in rows
        ]

    def add(
        self,
        name: str,
        *,
        sample_size: int,
        seed: int,
        config_id: int,
        admin_id: uuid.UUID,
        entries: Sequence[RoundEntry],
    ) -> uuid.UUID:
        round_row = EvaluationRoundModel(
            name=name,
            sample_size=sample_size,
            seed=seed,
            config_id=config_id,
            user_id=admin_id,
        )
        self._session.add(round_row)
        try:
            # El índice único parcial es la garantía real de «una sola abierta» (carreras).
            self._session.flush()
        except IntegrityError as exc:
            if _violated_constraint(exc) == ONE_OPEN_ROUND_INDEX:
                raise RoundAlreadyOpenError from exc
            raise
        self._session.add_all(
            RoundReportModel(
                round_id=round_row.id,
                report_id=entry.report_id,
                zone_id=entry.zone_id,
                priority_score=entry.urgency_score,
                engine_order=entry.motor_order,
            )
            for entry in entries
        )
        self._session.flush()
        return round_row.id

    def lock_status(self, round_id: uuid.UUID) -> RoundStatus | None:
        state = self._session.execute(
            select(EvaluationRoundModel.state)
            .where(EvaluationRoundModel.id == round_id)
            .with_for_update()
        ).scalar_one_or_none()
        return None if state is None else RoundStatus(state)

    def mark_closed(self, round_id: uuid.UUID) -> None:
        self._session.execute(
            update(EvaluationRoundModel)
            .where(EvaluationRoundModel.id == round_id)
            .values(state=RoundStatus.CLOSED.value, closed_at=text("now()"))
        )

    def get_progress(self, round_id: uuid.UUID) -> RoundProgress | None:
        row = self._session.get(EvaluationRoundModel, round_id)
        if row is None:
            return None
        self._session.refresh(row)
        params = {"round_id": round_id}
        submissions = self._session.execute(_PROGRESS_EVALUATORS, params).all()
        first_seen: dict[uuid.UUID, datetime] = {}
        for sub in submissions:
            current = first_seen.get(sub.id_usuario)
            if current is None or sub.primer_envio < current:
                first_seen[sub.id_usuario] = sub.primer_envio
        ordered = sorted(first_seen, key=lambda user: (first_seen[user], user))
        labels = {user: EvaluatorLabel(k) for k, user in enumerate(ordered, start=1)}
        zones = [
            ZoneProgress(
                zone_id=z.id_zona,
                name=z.nombre,
                concentration=Concentration(z.concentracion),
                n_reports=z.n_reportes,
                submitted_by=sorted(
                    (labels[s.id_usuario] for s in submissions if s.id_zona == z.id_zona),
                    key=lambda label: label.number,
                ),
            )
            for z in self._session.execute(_PROGRESS_ZONES, params)
        ]
        return RoundProgress(summary=_to_summary(row), zones=zones)

    def list_rounds(self, limit: int, offset: int) -> list[RoundSummary]:
        rows = self._session.scalars(
            select(EvaluationRoundModel)
            .order_by(EvaluationRoundModel.opened_at.desc(), EvaluationRoundModel.id.desc())
            .limit(limit)
            .offset(offset)
        )
        return [_to_summary(row) for row in rows]
