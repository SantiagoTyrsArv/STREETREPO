"""Rechazo por Content-Length antes de leer el cuerpo (decisión 46d)."""

from fastapi.testclient import TestClient

from app.core.body_size_limit import MULTIPART_OVERHEAD_BYTES, REPORT_REQUEST_MAX_BYTES
from app.main import API_V1_PREFIX
from app.modules.reports.domain.photos import MAX_PHOTO_BYTES
from tests.conftest import PANEL_ORIGIN

REPORTS = f"{API_V1_PREFIX}/reports"


def test_the_report_limit_is_the_photo_limit_plus_the_form_fields() -> None:
    assert REPORT_REQUEST_MAX_BYTES == MAX_PHOTO_BYTES + MULTIPART_OVERHEAD_BYTES


def test_a_report_larger_than_the_limit_is_rejected_before_reading_it(client: TestClient) -> None:
    # Si el cuerpo llegara a FastAPI, este formulario inválido daría 400 al leerlo. El 413
    # prueba que se rechazó antes, solo por la cabecera.
    response = client.post(
        REPORTS,
        content=b"x" * (REPORT_REQUEST_MAX_BYTES + 1),
        headers={"Content-Type": "multipart/form-data; boundary=x", "Origin": PANEL_ORIGIN},
    )

    assert response.status_code == 413
    assert response.json()["code"] == "PHOTO_TOO_LARGE"
    assert response.json()["details"] == {"field": "photo", "max_bytes": MAX_PHOTO_BYTES}
    # Pasa por CORS y por las cabeceras de seguridad como cualquier otro error.
    assert response.headers["access-control-allow-origin"] == PANEL_ORIGIN
    assert response.headers["X-Content-Type-Options"] == "nosniff"


def test_a_report_within_the_limit_reaches_the_route(client: TestClient) -> None:
    response = client.post(
        REPORTS,
        content=b"x" * 1024,
        headers={"Content-Type": "multipart/form-data; boundary=x"},
    )

    # FastAPI sí lo leyó (y lo rechazó por ser un formulario inválido).
    assert response.status_code == 400
    assert response.json()["code"] == "HTTP_ERROR"


def test_other_routes_are_not_limited_by_the_report_size(client: TestClient) -> None:
    response = client.post(
        f"{API_V1_PREFIX}/auth/login",
        content=b"x" * (REPORT_REQUEST_MAX_BYTES + 1),
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code != 413


def test_an_invalid_content_length_is_400(client: TestClient) -> None:
    response = client.post(REPORTS, headers={"Content-Length": "mucho"})

    assert response.status_code == 400
    assert response.json()["code"] == "INVALID_CONTENT_LENGTH"
