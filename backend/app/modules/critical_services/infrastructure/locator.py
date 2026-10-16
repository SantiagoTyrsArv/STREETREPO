from sqlalchemy import text
from sqlalchemy.orm import Session

from app.modules.critical_services.domain.entities import NearestCriticalService
from app.modules.critical_services.domain.service_type import CriticalServiceType
from app.shared.domain.geo import GeoPoint

# Mismo patrón que el map-matching: filtro con índice geography, orden por distancia
# exacta y desempate por id para un resultado determinista.
_NEAREST_SERVICE = text(
    """
    WITH punto AS (
        SELECT ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography AS geog
    )
    SELECT s.id_servicio, s.nombre, s.tipo,
           ST_Distance(s.ubicacion::geography, punto.geog) AS distancia_m
    FROM servicio_critico AS s, punto
    WHERE ST_DWithin(s.ubicacion::geography, punto.geog, :radio_m)
    ORDER BY distancia_m, s.id_servicio
    LIMIT 1
    """
)


class PostgisCriticalServiceLocator:
    """Implementa ``CriticalServiceLocator`` sobre PostGIS."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def find_nearest(self, point: GeoPoint, max_distance_m: float) -> NearestCriticalService | None:
        row = self._session.execute(
            _NEAREST_SERVICE,
            {"lon": point.longitude, "lat": point.latitude, "radio_m": max_distance_m},
        ).one_or_none()
        if row is None:
            return None
        return NearestCriticalService(
            service_id=row.id_servicio,
            name=row.nombre,
            service_type=CriticalServiceType(row.tipo),
            distance_m=float(row.distancia_m),
        )
