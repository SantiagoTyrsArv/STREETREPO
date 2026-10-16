from fastapi import FastAPI, status
from fastapi.testclient import TestClient
from pydantic import BaseModel

from app.core.errors import AppError, register_error_handlers


class _Payload(BaseModel):
    severity: int


def _app() -> FastAPI:
    app = FastAPI()
    register_error_handlers(app)

    @app.get("/app-error")
    def raise_app_error() -> None:
        raise AppError(
            "REPORT_DUPLICATE_NEARBY",
            "Ya existe un reporte cercano.",
            status.HTTP_409_CONFLICT,
            {"report_id": 7},
        )

    @app.get("/boom")
    def boom() -> None:
        raise RuntimeError("detalle interno secreto")

    @app.post("/validate")
    def validate(payload: _Payload) -> _Payload:
        return payload

    return app


client = TestClient(_app(), raise_server_exceptions=False)


def test_app_error_uses_uniform_format() -> None:
    response = client.get("/app-error")

    assert response.status_code == 409
    assert response.json() == {
        "code": "REPORT_DUPLICATE_NEARBY",
        "message": "Ya existe un reporte cercano.",
        "details": {"report_id": 7},
    }


def test_validation_error_lists_fields() -> None:
    response = client.post("/validate", json={"severity": "alta"})

    assert response.status_code == 422
    body = response.json()
    assert body["code"] == "VALIDATION_ERROR"
    assert body["details"]["fields"][0]["field"] == "severity"


def test_not_found_uses_uniform_format() -> None:
    response = client.get("/no-existe")

    assert response.status_code == 404
    assert response.json()["code"] == "NOT_FOUND"


def test_unhandled_error_hides_internal_details() -> None:
    response = client.get("/boom")

    assert response.status_code == 500
    assert response.json()["code"] == "INTERNAL_ERROR"
    assert "secreto" not in response.text
