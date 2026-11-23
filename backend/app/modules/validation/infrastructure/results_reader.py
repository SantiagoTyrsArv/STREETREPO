"""Lecturas de los resultados de una ronda en PostgreSQL (consultas parametrizadas).

Solo las usa el administrador. Los evaluadores salen numerados («Evaluador k»), nunca con
nombre ni correo.
"""

import uuid
from collections import defaultdict
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Row, text
from sqlalchemy.orm import Session

from app.modules.reports.domain.status import ReportStatus
from app.modules.validation.domain.results import (
    DedupSummary,
    ReviewReport,
    ReviewWarning,
    RoundData,
    WarningCandidate,
    ZoneRoundData,
)
from app.modules.validation.domain.rounds import RoundEntry, RoundSummary, number_evaluators
from app.modules.validation.domain.warnings import WarningDecision
from app.modules.validation.domain.zones import Concentration
from app.modules.validation.infrastructure.round_repository import SqlRoundRepository

_ENTRIES = text(
    """
    SELECT rr.id_zona, z.nombre, CAST(z.concentracion AS text) AS concentracion,
           rr.id_reporte, rr.puntaje_u, rr.orden_motor
    FROM ronda_reporte AS rr
    JOIN zona AS z ON z.id_zona = rr.id_zona
    WHERE rr.id_ronda = :round_id
    ORDER BY z.nombre, z.id_zona, rr.orden_motor
    """
)

_ORDERS = text(
    """
    SELECT oe.id_usuario, rr.id_zona, oe.id_reporte, oe.posicion, oe.fecha_envio
    FROM orden_evaluador AS oe
    JOIN ronda_reporte AS rr ON rr.id_ronda = oe.id_ronda AND rr.id_reporte = oe.id_reporte
    WHERE oe.id_ronda = :round_id
    """
)

# Deduplicación por zona: todos los reportes de la zona, no solo la muestra (diseño, 8).
_DEDUP_REPORTS = text(
    """
    SELECT r.id_zona,
           count(*) AS reportes,
           count(*) FILTER (WHERE c.n > 0) AS confirmados,
           coalesce(sum(c.n), 0) AS confirmaciones
    FROM reporte AS r
    CROSS JOIN LATERAL (
        SELECT count(*) AS n FROM confirmacion AS cf WHERE cf.id_reporte = r.id_reporte
    ) AS c
    WHERE r.id_zona IN (
        SELECT DISTINCT rr.id_zona FROM ronda_reporte AS rr WHERE rr.id_ronda = :round_id
    )
    GROUP BY r.id_zona
    """
)

_DEDUP_WARNINGS = text(
    """
    SELECT a.id_zona,
           count(*) AS avisos,
           count(*) FILTER (WHERE a.decision = 'confirmo') AS confirmo,
           count(*) FILTER (WHERE a.decision = 'creo_igual') AS creo_igual,
           count(*) FILTER (WHERE a.decision = 'pendiente') AS pendiente
    FROM aviso_duplicado AS a
    WHERE a.id_zona IN (
        SELECT DISTINCT rr.id_zona FROM ronda_reporte AS rr WHERE rr.id_ronda = :round_id
    )
    GROUP BY a.id_zona
    """
)

_REVIEW_REPORTS = text(
    """
    SELECT r.id_reporte, z.nombre AS zona, r.fecha_creacion, v.nombre AS via,
           CAST(r.estado AS text) AS estado,
           (SELECT count(*) FROM confirmacion AS cf
             WHERE cf.id_reporte = r.id_reporte) AS confirmaciones
    FROM reporte AS r
    JOIN zona AS z ON z.id_zona = r.id_zona
    LEFT JOIN via AS v ON v.id_via = r.id_via
    WHERE r.id_zona IN (
        SELECT DISTINCT rr.id_zona FROM ronda_reporte AS rr WHERE rr.id_ronda = :round_id
    )
    ORDER BY z.nombre, r.fecha_creacion, r.id_reporte
    """
)

_REVIEW_WARNINGS = text(
    """
    SELECT a.id_aviso, z.nombre AS zona, a.fecha, CAST(a.decision AS text) AS decision,
           a.id_reporte_resultante, c.id_reporte AS candidato, c.distancia_m
    FROM aviso_duplicado AS a
    JOIN zona AS z ON z.id_zona = a.id_zona
    LEFT JOIN aviso_duplicado_candidato AS c ON c.id_aviso = a.id_aviso
    WHERE a.id_zona IN (
        SELECT DISTINCT rr.id_zona FROM ronda_reporte AS rr WHERE rr.id_ronda = :round_id
    )
    ORDER BY a.fecha, a.id_aviso, c.distancia_m, c.id_reporte
    """
)

_NO_DEDUP = DedupSummary(0, 0, 0, 0, 0, 0, 0)


class SqlRoundResultsReader:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._rounds = SqlRoundRepository(session)

    def summary(self, round_id: uuid.UUID) -> RoundSummary | None:
        progress = self._rounds.get_progress(round_id)
        return None if progress is None else progress.summary

    def load(self, round_id: uuid.UUID) -> RoundData | None:
        summary = self.summary(round_id)
        if summary is None:
            return None
        params = {"round_id": round_id}
        entries: dict[int, list[Row[tuple[object, ...]]]] = defaultdict(list)
        for row in self._session.execute(_ENTRIES, params):
            entries[row.id_zona].append(row)

        orders: dict[int, dict[uuid.UUID, dict[uuid.UUID, int]]] = defaultdict(dict)
        first_submission: dict[uuid.UUID, datetime] = {}
        for row in self._session.execute(_ORDERS, params):
            orders[row.id_zona].setdefault(row.id_usuario, {})[row.id_reporte] = row.posicion
            seen = first_submission.get(row.id_usuario)
            if seen is None or row.fecha_envio < seen:
                first_submission[row.id_usuario] = row.fecha_envio

        dedup = self._dedup(params)
        zones = [
            ZoneRoundData(
                zone_id=zone_id,
                name=rows[0].nombre,
                concentration=Concentration(rows[0].concentracion),
                entries=[
                    RoundEntry(
                        report_id=row.id_reporte,
                        zone_id=zone_id,
                        urgency_score=row.puntaje_u,
                        motor_order=row.orden_motor,
                    )
                    for row in rows
                ],
                evaluator_orders=orders.get(zone_id, {}),
                dedup=dedup.get(zone_id, _NO_DEDUP),
            )
            for zone_id, rows in entries.items()
        ]
        return RoundData(
            summary=summary, zones=zones, evaluator_numbers=number_evaluators(first_submission)
        )

    def _dedup(self, params: dict[str, uuid.UUID]) -> dict[int, DedupSummary]:
        reports = {row.id_zona: row for row in self._session.execute(_DEDUP_REPORTS, params)}
        warnings = {row.id_zona: row for row in self._session.execute(_DEDUP_WARNINGS, params)}
        result = {}
        for zone_id in reports.keys() | warnings.keys():
            r, w = reports.get(zone_id), warnings.get(zone_id)
            result[zone_id] = DedupSummary(
                reports=r.reportes if r else 0,
                reports_confirmed=r.confirmados if r else 0,
                confirmations=int(r.confirmaciones) if r else 0,
                warnings_total=w.avisos if w else 0,
                warnings_confirmed=w.confirmo if w else 0,
                warnings_created_anyway=w.creo_igual if w else 0,
                warnings_pending=w.pendiente if w else 0,
            )
        return result

    def review_reports(self, round_id: uuid.UUID) -> list[ReviewReport]:
        return [
            ReviewReport(
                report_id=row.id_reporte,
                zone_name=row.zona,
                created_at=row.fecha_creacion,
                road_name=row.via,
                status=ReportStatus(row.estado),
                confirmations=row.confirmaciones,
            )
            for row in self._session.execute(_REVIEW_REPORTS, {"round_id": round_id})
        ]

    def review_warnings(self, round_id: uuid.UUID) -> list[ReviewWarning]:
        grouped: dict[uuid.UUID, list[Row[tuple[object, ...]]]] = {}
        for row in self._session.execute(_REVIEW_WARNINGS, {"round_id": round_id}):
            grouped.setdefault(row.id_aviso, []).append(row)
        return [
            ReviewWarning(
                warning_id=warning_id,
                zone_name=rows[0].zona,
                shown_at=rows[0].fecha,
                decision=WarningDecision(rows[0].decision),
                resulting_report_id=rows[0].id_reporte_resultante,
                candidates=[
                    WarningCandidate(row.candidato, Decimal(row.distancia_m))
                    for row in rows
                    if row.candidato is not None
                ],
            )
            for warning_id, rows in grouped.items()
        ]
