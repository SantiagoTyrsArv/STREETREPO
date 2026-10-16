"""Adaptador de Overpass API: consulta OSM y traduce la respuesta al dominio.

Uso responsable (guía 3.1): se llama solo desde la carga OSM, nunca por cada
reporte; una consulta por tipo de dato, con ``User-Agent`` identificable.
"""

import logging
import time
from collections.abc import Callable, Mapping, Sequence
from typing import Any

import httpx

from app.modules.admin.application.import_osm_data import OsmSourceError
from app.modules.critical_services.domain.entities import OsmCriticalService
from app.modules.critical_services.domain.service_type import CriticalServiceType
from app.modules.roads.domain.classification import (
    SUPPORTED_HIGHWAY_TAGS,
    classify_highway,
    flow_factor,
)
from app.modules.roads.domain.entities import OsmRoad
from app.shared.domain.geo import BoundingBox, GeoPoint, InvalidGeometryError

logger = logging.getLogger(__name__)

# Etiqueta amenity de OSM -> tipo del diagrama ER.
AMENITY_TO_SERVICE_TYPE: Mapping[str, CriticalServiceType] = {
    "hospital": CriticalServiceType.HOSPITAL,
    "school": CriticalServiceType.SCHOOL,
}

MAX_NAME_LENGTH = 150  # VARCHAR(150) en via.nombre y servicio_critico.nombre
_QUERY_TIMEOUT_S = 90

# Reintentos: solo fallos transitorios (límite de uso o servidor saturado) y de red.
RETRYABLE_STATUS = frozenset({429, 502, 503, 504})
MAX_ATTEMPTS = 3
BASE_RETRY_DELAY_S = 10.0

type OsmElement = Mapping[str, Any]


def retry_delay(attempt: int, status_code: int | None) -> float | None:
    """Segundos de espera antes de reintentar una consulta fallida, o ``None`` para rendirse.

    ``attempt`` es el número del intento que acaba de fallar (1, 2, 3…).
    ``status_code`` es el estado HTTP recibido, o ``None`` si falló la red
    (sin conexión, timeout).
    """
    if attempt >= MAX_ATTEMPTS:
        return None
    if status_code is not None and status_code not in RETRYABLE_STATUS:
        return None
    # Espera exponencial (10 s, 20 s…): no insistir sobre un servidor saturado (guía 3.1).
    return BASE_RETRY_DELAY_S * 2.0 ** (attempt - 1)


class _RequestFailedError(Exception):
    def __init__(self, message: str, status_code: int | None) -> None:
        super().__init__(message)
        self.status_code = status_code


def _bbox(area: BoundingBox) -> str:
    return f"{area.south},{area.west},{area.north},{area.east}"


def build_roads_query(area: BoundingBox) -> str:
    tags = "|".join(sorted(SUPPORTED_HIGHWAY_TAGS))
    return (
        f"[out:json][timeout:{_QUERY_TIMEOUT_S}];"
        f'way["highway"~"^({tags})$"]({_bbox(area)});'
        "out tags geom;"
    )


def build_critical_services_query(area: BoundingBox) -> str:
    amenities = "|".join(sorted(AMENITY_TO_SERVICE_TYPE))
    selector = f'["amenity"~"^({amenities})$"]({_bbox(area)})'
    return (
        f"[out:json][timeout:{_QUERY_TIMEOUT_S}];(node{selector};way{selector};);out tags center;"
    )


def _name(tags: Mapping[str, str]) -> str | None:
    name = tags.get("name", "").strip()
    return name[:MAX_NAME_LENGTH] or None


def parse_road(element: OsmElement) -> OsmRoad | None:
    """Vía del dominio, o ``None`` si la etiqueta no se carga o la geometría no sirve."""
    tags: Mapping[str, str] = element.get("tags", {})
    highway_tag = tags.get("highway", "")
    road_class = classify_highway(highway_tag)
    if road_class is None:
        return None
    try:
        points = tuple(
            GeoPoint(longitude=float(node["lon"]), latitude=float(node["lat"]))
            for node in element.get("geometry", [])
        )
        return OsmRoad(
            osm_id=int(element["id"]),
            name=_name(tags),
            highway_tag=highway_tag,
            road_class=road_class,
            flow_factor=flow_factor(road_class),
            points=points,
        )
    except (InvalidGeometryError, KeyError, TypeError, ValueError):
        logger.warning("Vía OSM %s descartada por geometría inválida", element.get("id"))
        return None


def service_osm_id(element: OsmElement) -> int:
    """Nodos y vías de OSM comparten numeración: las vías se guardan con id negativo."""
    osm_id = int(element["id"])
    return -osm_id if element.get("type") == "way" else osm_id


def parse_critical_service(element: OsmElement) -> OsmCriticalService | None:
    tags: Mapping[str, str] = element.get("tags", {})
    service_type = AMENITY_TO_SERVICE_TYPE.get(tags.get("amenity", ""))
    if service_type is None:
        return None
    # Los nodos traen lat/lon; las vías (áreas), el centro calculado por Overpass.
    position: Mapping[str, Any] = element.get("center", element)
    try:
        location = GeoPoint(longitude=float(position["lon"]), latitude=float(position["lat"]))
        return OsmCriticalService(
            osm_id=service_osm_id(element),
            name=_name(tags),
            service_type=service_type,
            location=location,
        )
    except (InvalidGeometryError, KeyError, TypeError, ValueError):
        logger.warning("Servicio OSM %s descartado por ubicación inválida", element.get("id"))
        return None


class OverpassClient:
    """Implementa ``OsmDataSource`` sobre la API pública de Overpass."""

    def __init__(
        self, http: httpx.Client, url: str, sleep: Callable[[float], None] = time.sleep
    ) -> None:
        self._http = http
        self._url = url
        self._sleep = sleep

    def _post(self, query: str) -> httpx.Response:
        try:
            response = self._http.post(self._url, data={"data": query})
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            status_code = exc.response.status_code
            raise _RequestFailedError(f"Overpass respondió {status_code}", status_code) from exc
        except httpx.HTTPError as exc:
            raise _RequestFailedError("Sin respuesta de Overpass", None) from exc
        return response

    def _post_with_retries(self, query: str) -> httpx.Response:
        attempt = 1
        while True:
            try:
                return self._post(query)
            except _RequestFailedError as exc:
                delay = retry_delay(attempt, exc.status_code)
                if delay is None:
                    raise OsmSourceError(f"{exc}; intenta más tarde.") from exc
                logger.warning("%s; reintento %d en %.0f s", exc, attempt + 1, delay)
                self._sleep(delay)
                attempt += 1

    def _elements(self, query: str) -> list[OsmElement]:
        response = self._post_with_retries(query)
        try:
            payload = response.json()
        except ValueError as exc:
            raise OsmSourceError("Overpass devolvió una respuesta que no es JSON.") from exc
        elements = payload.get("elements") if isinstance(payload, dict) else None
        if not isinstance(elements, list):
            raise OsmSourceError("Respuesta de Overpass sin elementos.")
        return elements

    def fetch_roads(self, area: BoundingBox) -> Sequence[OsmRoad]:
        parsed = (parse_road(element) for element in self._elements(build_roads_query(area)))
        return [road for road in parsed if road is not None]

    def fetch_critical_services(self, area: BoundingBox) -> Sequence[OsmCriticalService]:
        query = build_critical_services_query(area)
        parsed = (parse_critical_service(element) for element in self._elements(query))
        return [service for service in parsed if service is not None]


def create_overpass_client(url: str, user_agent: str, timeout_s: float) -> OverpassClient:
    http = httpx.Client(
        headers={"User-Agent": user_agent},
        # El servidor puede tardar hasta el timeout de la consulta; se da un margen.
        timeout=httpx.Timeout(timeout_s, connect=10.0),
    )
    return OverpassClient(http, url)
