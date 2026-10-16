from dataclasses import dataclass

from app.modules.critical_services.domain.service_type import CriticalServiceType
from app.shared.domain.geo import GeoPoint


@dataclass(frozen=True, slots=True)
class OsmCriticalService:
    """Servicio crítico (hospital, escuela) obtenido de OpenStreetMap."""

    osm_id: int
    name: str | None
    service_type: CriticalServiceType
    location: GeoPoint


@dataclass(frozen=True, slots=True)
class NearestCriticalService:
    """Servicio crítico más cercano a un punto, dentro del radio de proximidad."""

    service_id: int
    name: str | None
    service_type: CriticalServiceType
    distance_m: float
