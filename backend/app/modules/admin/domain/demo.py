"""Datos de demostración del panel (decisión 76): qué los identifica y qué puertos usan.

No son datos de campo. Todo cuelga de dos cuentas de un dominio reservado, así que se
reconocen y se borran enteros sin tocar los reportes reales.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from types import MappingProxyType
from typing import Final, Protocol

from app.modules.reports.domain.severity import Severity
from app.modules.roads.domain.road_class import RoadClass
from app.shared.domain.geo import BoundingBox, GeoPoint

# ``.invalid`` está reservado (RFC 2606): el registro público rechaza esos correos, así
# que solo ``seed-demo`` puede crear cuentas en este dominio.
DEMO_EMAIL_DOMAIN: Final = "demo.invalid"
DEMO_CITIZEN_EMAIL: Final = f"ciudadano@{DEMO_EMAIL_DOMAIN}"
DEMO_ADMIN_EMAIL: Final = f"funcionario@{DEMO_EMAIL_DOMAIN}"
DEMO_CITIZEN_NAME: Final = "Ciudadano de demostración"
DEMO_ADMIN_NAME: Final = "Funcionario de demostración"
# No es un hash Argon2: ninguna contraseña coincide con él, nadie inicia sesión con
# estas cuentas.
DEMO_CREDENTIAL_MARKER: Final = "!demo"

DEMO_DESCRIPTION: Final = "Reporte de demostración. No es un dato de campo."
DEMO_PRIORITIZED_NOTE: Final = "Demostración: priorizado para intervención."
DEMO_REPAIRED_NOTE: Final = "Demostración: daño reparado."

# Reparto de los puntos: jerarquías viales, cercanía a servicios críticos y sin vía.
DEMO_ROAD_QUOTAS: Final = MappingProxyType(
    {
        RoadClass.PRIMARY: 8,
        RoadClass.SECONDARY: 8,
        RoadClass.TERTIARY: 6,
        RoadClass.RESIDENTIAL: 6,
    }
)
DEMO_NEAR_SERVICE_COUNT: Final = 2
DEMO_OFF_ROAD_COUNT: Final = 2
DEMO_REPORT_COUNT: Final = 32
DEMO_PRIORITIZED_COUNT: Final = 8
DEMO_REPAIRED_COUNT: Final = 4


class NotEnoughOsmDataError(Exception):
    """No hay vías o servicios críticos suficientes para repartir los puntos."""


@dataclass(frozen=True, slots=True)
class DemoPoint:
    location: GeoPoint
    severity: Severity


@dataclass(frozen=True, slots=True)
class DemoRemoval:
    reports: int
    users: int
    # Para borrar los archivos después de confirmar la transacción.
    photo_keys: Sequence[str]


class DemoPointSource(Protocol):
    def pick(self, area: BoundingBox) -> Sequence[DemoPoint]:
        """Puntos dentro del área, siempre los mismos con los mismos datos de OSM; puede
        devolver menos de ``DEMO_REPORT_COUNT`` si los datos no alcanzan."""
        ...


class DemoDataStore(Protocol):
    def delete_all(self) -> DemoRemoval:
        """Borra los reportes de las cuentas de demostración (con su evidencia, historial,
        evaluaciones y confirmaciones) y las cuentas. No confirma la transacción."""
        ...
