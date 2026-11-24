"""Toda ruta administrativa o de evaluación exige su rol en el servidor (guía 7.1 y 15).

Recorre las rutas de la aplicación en vez de una lista escrita a mano: una ruta nueva bajo
``/admin`` o ``/evaluation`` que olvide el rol hace fallar esta prueba.
"""

from collections.abc import Callable, Iterator
from typing import Any

import pytest
from fastapi.dependencies.models import Dependant
from fastapi.routing import APIRoute, iter_route_contexts

from app.main import API_V1_PREFIX, create_app
from app.modules.auth.presentation.dependencies import require_admin, require_evaluator

ROLE_BY_PREFIX: dict[str, Callable[..., Any]] = {
    f"{API_V1_PREFIX}/admin": require_admin,
    f"{API_V1_PREFIX}/evaluation": require_evaluator,
}


def _calls(dependant: Dependant) -> Iterator[Callable[..., Any] | None]:
    for sub in dependant.dependencies:
        yield sub.call
        yield from _calls(sub)


def _api_routes() -> Iterator[tuple[str, str, APIRoute]]:
    # FastAPI 0.165 anida los routers incluidos; iter_route_contexts da la ruta completa.
    for context in iter_route_contexts(create_app().routes):
        if isinstance(context.route, APIRoute):
            yield context.path, ",".join(sorted(context.methods or ())), context.route


def _protected_routes() -> list[tuple[str, str, Callable[..., Any]]]:
    return [
        (path, methods, role)
        for path, methods, _ in _api_routes()
        for prefix, role in ROLE_BY_PREFIX.items()
        if path.startswith(prefix)
    ]


PROTECTED = _protected_routes()


def test_there_are_protected_routes_to_check() -> None:
    # Si los prefijos cambian, la prueba de abajo no debe pasar en vacío.
    assert len([r for r in PROTECTED if r[2] is require_admin]) >= 15
    assert len([r for r in PROTECTED if r[2] is require_evaluator]) >= 4


@pytest.mark.parametrize(("path", "methods", "role"), PROTECTED, ids=str)
def test_route_requires_its_role(path: str, methods: str, role: Callable[..., Any]) -> None:
    route = next(r for p, m, r in _api_routes() if (p, m) == (path, methods))

    assert role in set(_calls(route.dependant)), f"{methods} {path} no exige {role.__name__}"
