"""El log de cada petición no lleva datos personales (guía 7.2 y 15).

Solo método, ruta, estado y duración: ni la cadena de consulta (puede traer un correo o
coordenadas), ni la IP del cliente, ni cabeceras como Authorization.
"""

import logging

import pytest
from fastapi.testclient import TestClient

from app.main import API_V1_PREFIX

SECRET_QUERY = "correo=persona%40ejemplo.co&lat=1.2136&lon=-77.2811"


def test_request_log_has_no_query_ip_or_token(
    client: TestClient, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.INFO, logger="app.http"):
        client.get(
            f"{API_V1_PREFIX}/privacy-policy?{SECRET_QUERY}",
            headers={"Authorization": "Bearer token-secreto"},
        )

    records = [r for r in caplog.records if r.name == "app.http"]
    assert len(records) == 1
    logged = repr(records[0].__dict__)
    assert records[0].http["path"] == f"{API_V1_PREFIX}/privacy-policy"  # type: ignore[attr-defined]
    for leaked in ("persona", "ejemplo.co", "1.2136", "-77.2811", "token-secreto", "testclient"):
        assert leaked not in logged
