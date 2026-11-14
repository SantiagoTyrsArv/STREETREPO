import uuid
from collections.abc import Sequence

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.modules.reports.domain.my_reports import PublicReportView
from app.modules.reports.domain.public_location import PUBLIC_GRID_DEGREES
from app.modules.reports.domain.public_map import MapReport
from app.modules.reports.domain.severity import Severity
from app.modules.reports.domain.status import ReportStatus
from app.shared.domain.geo import BoundingBox, GeoPoint

# El área se compara con la ubicación **pública** (ajustada a la cuadrícula), no con la
# exacta: si se filtrara por la exacta, pidiendo rectángulos cada vez más pequeños se
# podría acotar la ubicación real de un reporte ajeno (propuesta 43). El primer filtro,
# con el rectángulo ampliado en una celda, solo descarta rápido lo que está lejos.
_IN_AREA = text(
    """
    WITH area AS (
        SELECT ST_MakeEnvelope(:oeste, :sur, :este, :norte, 4326) AS geom
    ),
    visibles AS (
        SELECT r.id_reporte, r.id_usuario, r.estado, r.severidad, r.id_via,
               r.fecha_creacion, ST_SnapToGrid(r.ubicacion, :rejilla) AS publica
        FROM reporte AS r, area
        WHERE r.ubicacion && ST_Expand(area.geom, :rejilla)
          AND (CAST(:estado AS text) IS NULL OR r.estado = CAST(:estado AS estado_reporte))
    )
    SELECT v.id_reporte, v.estado, v.severidad, v.id_via, vi.nombre AS nombre_via,
           v.fecha_creacion, v.id_usuario = :viewer AS es_mio,
           ST_X(v.publica) AS lon_publica, ST_Y(v.publica) AS lat_publica,
           (SELECT count(*) FROM confirmacion AS cf
            WHERE cf.id_reporte = v.id_reporte) AS confirmaciones,
           EXISTS (SELECT 1 FROM confirmacion AS cf
                   WHERE cf.id_reporte = v.id_reporte AND cf.id_usuario = :viewer)
               AS confirmado_por_mi
    FROM visibles AS v
    CROSS JOIN area
    LEFT JOIN via AS vi ON vi.id_via = v.id_via
    WHERE ST_Intersects(v.publica, area.geom)
    ORDER BY v.fecha_creacion DESC, v.id_reporte
    LIMIT :limite
    """
)


class SqlPublicReportsReader:
    """Implementa ``PublicReportsReader`` con PostGIS local."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def list_in_area(
        self,
        area: BoundingBox,
        status: ReportStatus | None,
        limit: int,
        viewer_id: uuid.UUID,
    ) -> Sequence[MapReport]:
        rows = self._session.execute(
            _IN_AREA,
            {
                "oeste": area.west,
                "sur": area.south,
                "este": area.east,
                "norte": area.north,
                "rejilla": PUBLIC_GRID_DEGREES,
                "estado": None if status is None else status.value,
                "viewer": viewer_id,
                "limite": limit,
            },
        ).all()
        return [
            MapReport(
                public=PublicReportView(
                    id=row.id_reporte,
                    location=GeoPoint(longitude=row.lon_publica, latitude=row.lat_publica),
                    status=ReportStatus(row.estado),
                    severity=Severity(row.severidad),
                    confirmations=int(row.confirmaciones),
                    road_id=row.id_via,
                    road_name=row.nombre_via,
                    created_at=row.fecha_creacion,
                ),
                is_mine=bool(row.es_mio),
                confirmed_by_me=bool(row.confirmado_por_mi),
            )
            for row in rows
        ]
