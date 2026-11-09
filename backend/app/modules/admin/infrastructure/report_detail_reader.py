"""Detalle del reporte para el administrador con SQL parametrizado."""

import uuid
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.modules.admin.domain.report_detail import (
    AdminHistoryEntry,
    AdminReportDetail,
    EvaluationBreakdown,
    NearestService,
    RoadInfo,
)
from app.modules.reports.domain.severity import Severity
from app.modules.reports.domain.status import ReportStatus
from app.shared.domain.geo import GeoPoint

# Evaluación más reciente con los pesos de su versión y el servicio crítico que dio P.
_DETAIL = text(
    """
    SELECT r.id_reporte, r.estado, r.severidad, r.descripcion, r.fecha_creacion,
           ST_X(r.ubicacion) AS lon, ST_Y(r.ubicacion) AS lat,
           r.id_via, v.nombre AS nombre_via, v.highway_osm,
           u.nombre AS nombre_autor,
           (SELECT count(*) FROM confirmacion AS cf
            WHERE cf.id_reporte = r.id_reporte) AS confirmaciones,
           e.id_evaluacion, e.s_severidad, e.f_flujo, e.p_proximidad, e.u_utilidad,
           e.fecha_calculo, e.id_config, e.w_severidad, e.w_flujo, e.w_proximidad,
           e.distancia_servicio_m, e.id_servicio, e.nombre_servicio, e.tipo_servicio
    FROM reporte AS r
    JOIN usuario AS u ON u.id_usuario = r.id_usuario
    LEFT JOIN via AS v ON v.id_via = r.id_via
    LEFT JOIN LATERAL (
        SELECT ep.id_evaluacion, ep.s_severidad, ep.f_flujo, ep.p_proximidad, ep.u_utilidad,
               ep.fecha_calculo, ep.id_config, ep.distancia_servicio_m, ep.id_servicio,
               c.w_severidad, c.w_flujo, c.w_proximidad,
               s.nombre AS nombre_servicio, s.tipo AS tipo_servicio
        FROM evaluacion_prioridad AS ep
        JOIN configuracion_pesos AS c ON c.id_config = ep.id_config
        LEFT JOIN servicio_critico AS s ON s.id_servicio = ep.id_servicio
        WHERE ep.id_reporte = r.id_reporte
        ORDER BY ep.id_evaluacion DESC
        LIMIT 1
    ) AS e ON true
    WHERE r.id_reporte = :reporte
    """
)

_HISTORY = text(
    """
    SELECT h.estado_anterior, h.estado_nuevo, h.fecha_cambio, h.observacion,
           u.nombre AS nombre_usuario
    FROM historial_estado AS h
    LEFT JOIN usuario AS u ON u.id_usuario = h.id_usuario
    WHERE h.id_reporte = :reporte
    ORDER BY h.fecha_cambio, h.id_historial
    """
)


class SqlAdminReportReader:
    """Implementa ``AdminReportReader``."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, report_id: uuid.UUID) -> AdminReportDetail | None:
        row = self._session.execute(_DETAIL, {"reporte": report_id}).one_or_none()
        if row is None:
            return None
        history = self._session.execute(_HISTORY, {"reporte": report_id}).all()
        return AdminReportDetail(
            id=row.id_reporte,
            status=ReportStatus(row.estado),
            severity=Severity(row.severidad),
            description=row.descripcion,
            location=GeoPoint(longitude=row.lon, latitude=row.lat),
            road=(
                RoadInfo(name=row.nombre_via, highway=row.highway_osm)
                if row.id_via is not None
                else None
            ),
            reporter_name=row.nombre_autor,
            created_at=row.fecha_creacion,
            confirmations=int(row.confirmaciones),
            evaluation=_evaluation(row),
            history=[
                AdminHistoryEntry(
                    previous_status=(
                        ReportStatus(entry.estado_anterior) if entry.estado_anterior else None
                    ),
                    status=ReportStatus(entry.estado_nuevo),
                    changed_at=entry.fecha_cambio,
                    note=entry.observacion,
                    changed_by_name=entry.nombre_usuario,
                )
                for entry in history
            ],
        )


def _evaluation(row: Any) -> EvaluationBreakdown | None:
    if row.id_evaluacion is None:
        return None
    service = None
    if row.id_servicio is not None and row.distancia_servicio_m is not None:
        service = NearestService(
            name=row.nombre_servicio,
            service_type=str(row.tipo_servicio),
            distance_m=row.distancia_servicio_m,
        )
    return EvaluationBreakdown(
        severity_score=row.s_severidad,
        flow_score=row.f_flujo,
        proximity_score=row.p_proximidad,
        urgency_score=row.u_utilidad,
        w_severity=row.w_severidad,
        w_flow=row.w_flujo,
        w_proximity=row.w_proximidad,
        config_id=row.id_config,
        service=service,
        calculated_at=row.fecha_calculo,
    )
