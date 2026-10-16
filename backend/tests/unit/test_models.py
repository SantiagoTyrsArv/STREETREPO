"""Los modelos ORM reflejan el diagrama ER sin necesitar base de datos."""

from sqlalchemy import CheckConstraint, Table, UniqueConstraint

import app.models  # noqa: F401  - registra los modelos
from app.core.database import Base
from app.modules.reports.domain.severity import Severity
from app.modules.reports.domain.status import ReportStatus
from app.modules.roads.domain.road_class import RoadClass
from app.modules.users.domain.deletion_request import DeletionRequestStatus
from app.modules.users.domain.role import UserRole


def _table(name: str) -> Table:
    return Base.metadata.tables[name]


def test_all_er_entities_are_mapped() -> None:
    assert set(Base.metadata.tables) == {
        "usuario",
        "reporte",
        "confirmacion",
        "evidencia",
        "historial_estado",
        "configuracion_pesos",
        "evaluacion_prioridad",
        "servicio_critico",
        "via",
        "zona",
        "token_refresco",
        "solicitud_supresion",
    }


def test_enum_values_match_er_diagram() -> None:
    assert [s.value for s in ReportStatus] == ["registrado", "evaluado", "priorizado", "reparado"]
    assert [r.value for r in UserRole] == ["ciudadano", "administrador"]
    assert [c.value for c in RoadClass] == ["primaria", "secundaria", "terciaria", "residencial"]
    assert [d.value for d in DeletionRequestStatus] == ["pendiente", "atendida"]


def test_severity_codes_fit_check_constraint() -> None:
    assert [s.value for s in Severity] == [1, 2, 3]


def test_confirmation_has_unique_user_report_pair() -> None:
    uniques = {
        tuple(sorted(c.name for c in constraint.columns))
        for constraint in _table("confirmacion").constraints
        if isinstance(constraint, UniqueConstraint)
    }

    assert ("id_reporte", "id_usuario") in uniques


def test_weights_have_sum_and_range_checks() -> None:
    checks = {
        constraint.name
        for constraint in _table("configuracion_pesos").constraints
        if isinstance(constraint, CheckConstraint)
    }

    assert {"ck_configuracion_pesos_suma", "ck_configuracion_pesos_rango"} <= checks


def test_road_is_optional_in_report_for_unmatched_locations() -> None:
    # Sin vía a 30 m el reporte se guarda igual y se marca "Revisar vía" (guía 2.2).
    assert _table("reporte").c.id_via.nullable


def test_spatial_columns_use_wgs84() -> None:
    for table, column in [
        ("reporte", "ubicacion"),
        ("servicio_critico", "ubicacion"),
        ("via", "geom"),
        ("zona", "geom"),
    ]:
        assert _table(table).c[column].type.srid == 4326  # type: ignore[attr-defined]
