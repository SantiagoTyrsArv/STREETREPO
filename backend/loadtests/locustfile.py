"""Prueba de carga de la API con Locust (fase 8, decisión 68; metas de la guía 11).

Medidas del sistema en un equipo local con datos de demostración: no son resultados de
campo ni del capítulo 4. Se corre con ``infra/scripts/load-test.sh``, que levanta un stack
aparte, crea las cuentas de carga y las borra al terminar.

Variables de entorno:
- ``LOADTEST_PASSWORD``: contraseña de las cuentas ``carga-NNN@carga.example.com``.
- ``LOADTEST_ADMIN_EMAIL`` y ``LOADTEST_ADMIN_PASSWORD``: la cuenta de administrador.
"""

import io
import itertools
import os
import random
import uuid
from typing import Final

from locust import HttpUser, between, task
from PIL import Image

API: Final = "/api/v1"
# Centro de Pasto y una ventana parecida a la del mapa de la app (unos 2 km de lado).
CENTER_LON, CENTER_LAT = -77.2811, 1.2136
VIEW_HALF_DEG: Final = 0.01
# Puntos de los reportes nuevos: dentro del área de servicio, en el casco urbano.
POINT_LON = (-77.300, -77.262)
POINT_LAT = (1.195, 1.232)
SEVERITIES: Final = ("baja", "media", "alta")

_account_numbers = itertools.count(1)


def _photo() -> bytes:
    """Foto de 1600 por 1200 con ruido, unos 0,7 MB (como una del celular ya comprimida)."""
    rng = random.Random(68)  # noqa: S311 - píxeles de prueba, no criptográficos
    image = Image.frombytes("RGB", (400, 300), rng.randbytes(400 * 300 * 3))
    buffer = io.BytesIO()
    image.resize((1600, 1200)).save(buffer, format="JPEG", quality=80)
    return buffer.getvalue()


PHOTO: Final = _photo()


def _random_point() -> tuple[float, float]:
    return random.uniform(*POINT_LON), random.uniform(*POINT_LAT)  # noqa: S311 - no criptográfico


def _login(user: HttpUser, email: str, password: str) -> None:
    response = user.client.post(
        f"{API}/auth/login",
        json={"email": email, "password": password},
        name="/auth/login",
    )
    response.raise_for_status()
    user.client.headers["Authorization"] = f"Bearer {response.json()['access_token']}"


class CitizenUser(HttpUser):
    """Ciudadano con la app: mira el mapa, revisa duplicados y a veces reporta."""

    weight = 9
    wait_time = between(1, 3)

    def on_start(self) -> None:
        email = f"carga-{next(_account_numbers):03d}@carga.example.com"
        _login(self, email, os.environ["LOADTEST_PASSWORD"])

    @task(5)
    def map_area(self) -> None:
        lon = CENTER_LON + random.uniform(-0.01, 0.01)  # noqa: S311
        lat = CENTER_LAT + random.uniform(-0.01, 0.01)  # noqa: S311
        corners = (
            lon - VIEW_HALF_DEG,
            lat - VIEW_HALF_DEG,
            lon + VIEW_HALF_DEG,
            lat + VIEW_HALF_DEG,
        )
        bbox = ",".join(f"{value:.6f}" for value in corners)
        self.client.get(f"{API}/reports", params={"bbox": bbox}, name="/reports?bbox")

    @task(3)
    def nearby(self) -> None:
        lon, lat = _random_point()
        self.client.get(
            f"{API}/reports/nearby",
            params={"longitude": lon, "latitude": lat},
            name="/reports/nearby",
        )

    @task(1)
    def create_report(self) -> None:
        lon, lat = _random_point()
        self.client.post(
            f"{API}/reports",
            data={
                "longitude": str(lon),
                "latitude": str(lat),
                "severity": random.choice(SEVERITIES),  # noqa: S311
                "create_anyway": "true",
            },
            files={"photo": ("foto.jpg", PHOTO, "image/jpeg")},
            headers={"Idempotency-Key": str(uuid.uuid4())},
            name="POST /reports",
        )


class AdminUser(HttpUser):
    """Funcionario con el panel: ranking y mapa de calor."""

    weight = 1
    wait_time = between(2, 5)

    def on_start(self) -> None:
        _login(self, os.environ["LOADTEST_ADMIN_EMAIL"], os.environ["LOADTEST_ADMIN_PASSWORD"])

    @task(2)
    def ranking(self) -> None:
        self.client.get(f"{API}/admin/ranking", name="/admin/ranking")

    @task(1)
    def heatmap(self) -> None:
        self.client.get(f"{API}/admin/heatmap", name="/admin/heatmap")
