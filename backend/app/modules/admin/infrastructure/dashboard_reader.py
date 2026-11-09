"""Lecturas del tablero de priorización con SQL parametrizado sobre PostGIS (HU-08)."""

from collections.abc import Sequence
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.modules.admin.domain.ranking_view import (
    HeatPoint,
    RankingItem,
    RankingPage,
    StatusSummary,
)
from app.modules.reports.domain.severity import Severity
from app.modules.reports.domain.status import ReportStatus
from app.shared.domain.geo import BoundingBox

# Orden de ``priority/domain/ranking.py::ranking_key`` (guía 2.2): U desc → severidad desc →
# confirmaciones desc → más antiguo primero. ``id_reporte`` solo estabiliza la paginación.
# S, F y P salen de la evaluación más reciente; U de la copia vigente en ``reporte``.
_RANKING_PAGE = text(
    """
    SELECT r.id_reporte, r.estado, r.severidad, e.s_severidad, e.f_flujo, e.p_proximidad,
           r.puntaje_prioridad, r.id_via, v.nombre AS nombre_via, r.fecha_creacion,
           (SELECT count(*) FROM confirmacion AS cf
            WHERE cf.id_reporte = r.id_reporte) AS confirmaciones
    FROM reporte AS r
    JOIN LATERAL (
        SELECT ep.s_severidad, ep.f_flujo, ep.p_proximidad
        FROM evaluacion_prioridad AS ep
        WHERE ep.id_reporte = r.id_reporte
        ORDER BY ep.id_evaluacion DESC
        LIMIT 1
    ) AS e ON true
    LEFT JOIN via AS v ON v.id_via = r.id_via
    WHERE r.estado = ANY(CAST(:estados AS estado_reporte[]))
      AND r.puntaje_prioridad IS NOT NULL
    ORDER BY r.puntaje_prioridad DESC, r.severidad DESC, confirmaciones DESC,
             r.fecha_creacion ASC, r.id_reporte ASC
    LIMIT :limite OFFSET :desplazamiento
    """
)

_RANKING_TOTAL = text(
    """
    SELECT count(*) FROM reporte AS r
    WHERE r.estado = ANY(CAST(:estados AS estado_reporte[]))
      AND r.puntaje_prioridad IS NOT NULL
      AND EXISTS (SELECT 1 FROM evaluacion_prioridad AS ep WHERE ep.id_reporte = r.id_reporte)
    """
)

_SUMMARY = text(
    """
    SELECT count(*) FILTER (WHERE estado <> CAST(:reparado AS estado_reporte)) AS activos,
           count(*) FILTER (WHERE estado = CAST(:evaluado AS estado_reporte)) AS evaluados,
           count(*) FILTER (WHERE estado = CAST(:priorizado AS estado_reporte)) AS priorizados,
           count(*) FILTER (WHERE estado = CAST(:reparado AS estado_reporte)) AS reparados
    FROM reporte
    """
)

# Dos consultas (con y sin rectángulo) para que el filtro use el índice GiST. Se repiten
# a propósito: SQL literal, sin concatenar texto (guía 5).
_HEAT_ALL = text(
    """
    SELECT ST_Y(ubicacion) AS lat, ST_X(ubicacion) AS lon, puntaje_prioridad
    FROM reporte
    WHERE estado <> CAST(:reparado AS estado_reporte) AND puntaje_prioridad IS NOT NULL
    ORDER BY puntaje_prioridad DESC, id_reporte
    LIMIT :limite
    """
)

_HEAT_IN_BBOX = text(
    """
    SELECT ST_Y(ubicacion) AS lat, ST_X(ubicacion) AS lon, puntaje_prioridad
    FROM reporte
    WHERE estado <> CAST(:reparado AS estado_reporte) AND puntaje_prioridad IS NOT NULL
      AND ST_Intersects(ubicacion, ST_MakeEnvelope(:oeste, :sur, :este, :norte, 4326))
    ORDER BY puntaje_prioridad DESC, id_reporte
    LIMIT :limite
    """
)


class SqlDashboardReader:
    """Implementa ``DashboardReader``."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def ranking(self, statuses: frozenset[ReportStatus], limit: int, offset: int) -> RankingPage:
        states = sorted(status.value for status in statuses)
        rows = self._session.execute(
            _RANKING_PAGE, {"estados": states, "limite": limit, "desplazamiento": offset}
        ).all()
        total = self._session.execute(_RANKING_TOTAL, {"estados": states}).scalar_one()
        return RankingPage(items=[_ranking_item(row) for row in rows], total=int(total))

    def summary(self) -> StatusSummary:
        row = self._session.execute(
            _SUMMARY,
            {
                "reparado": ReportStatus.REPAIRED.value,
                "evaluado": ReportStatus.EVALUATED.value,
                "priorizado": ReportStatus.PRIORITIZED.value,
            },
        ).one()
        return StatusSummary(
            active=int(row.activos),
            evaluated=int(row.evaluados),
            prioritized=int(row.priorizados),
            repaired=int(row.reparados),
        )

    def heat_points(self, bbox: BoundingBox | None, limit: int) -> Sequence[HeatPoint]:
        params: dict[str, Any] = {"reparado": ReportStatus.REPAIRED.value, "limite": limit}
        if bbox is None:
            rows = self._session.execute(_HEAT_ALL, params).all()
        else:
            params |= {
                "oeste": bbox.west,
                "sur": bbox.south,
                "este": bbox.east,
                "norte": bbox.north,
            }
            rows = self._session.execute(_HEAT_IN_BBOX, params).all()
        return [
            HeatPoint(lat=row.lat, lon=row.lon, urgency_score=row.puntaje_prioridad) for row in rows
        ]


def _ranking_item(row: Any) -> RankingItem:
    return RankingItem(
        report_id=row.id_reporte,
        status=ReportStatus(row.estado),
        severity=Severity(row.severidad),
        severity_score=row.s_severidad,
        flow_score=row.f_flujo,
        proximity_score=row.p_proximidad,
        urgency_score=row.puntaje_prioridad,
        road_id=row.id_via,
        road_name=row.nombre_via,
        confirmations=int(row.confirmaciones),
        created_at=row.fecha_creacion,
    )
