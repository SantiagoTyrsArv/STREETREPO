"""Ficha comparativa y archivos de revisión en CSV (objetivo 4, sección 8 del diseño)."""

import csv
import io
import uuid
from datetime import UTC, datetime
from decimal import Decimal

from app.modules.reports.domain.status import ReportStatus
from app.modules.validation.application.round_results import RoundResultsService
from app.modules.validation.domain.results import (
    ReviewReport,
    ReviewWarning,
    RoundData,
    RoundResults,
    WarningCandidate,
    ZoneRoundData,
)
from app.modules.validation.domain.warnings import WarningDecision
from app.modules.validation.domain.zones import Concentration
from app.modules.validation.presentation.csv_export import (
    avisos_csv,
    export_filename,
    ficha_csv,
    reportes_csv,
    resumen_csv,
)
from tests.unit.test_validation_results import (
    EVA_1,
    EVA_2,
    HIGH,
    LOW,
    NOW,
    ROUND_ID,
    FakeReader,
    _summary,
    _zone,
)

BOM = b"\xef\xbb\xbf"


def _results(*zones: ZoneRoundData) -> RoundResults:
    data = RoundData(
        summary=_summary(),
        zones=list(zones or (HIGH, LOW)),
        evaluator_numbers={EVA_1: 1, EVA_2: 2},
    )
    return RoundResultsService(FakeReader(data)).results(ROUND_ID)


def _rows(content: bytes) -> list[dict[str, str]]:
    assert content.startswith(BOM)
    return list(csv.DictReader(io.StringIO(content[len(BOM) :].decode("utf-8"))))


def test_the_ficha_has_one_row_per_report_with_the_study_columns() -> None:
    content = ficha_csv(_results())

    rows = _rows(content)
    header = content[len(BOM) :].decode("utf-8").splitlines()[0].split(",")
    assert header == [
        "id_reporte",
        "zona",
        "concentracion",
        "puntaje_u",
        "orden_motor",
        "orden_panel",
        "desacuerdo",
        "coincide_pm1",
        "orden_evaluador_1",
        "orden_evaluador_2",
    ]
    assert len(rows) == 10
    first = rows[0]
    assert (first["zona"], first["concentracion"], first["puntaje_u"]) == ("Zona 1", "alta", "9")
    assert (first["orden_motor"], first["orden_evaluador_1"], first["orden_evaluador_2"]) == (
        "1",
        "1",
        "2",
    )
    # Posiciones medias 1,5 y 1,5 → rango promedio 1.5, con punto decimal.
    assert first["orden_panel"] == "1.5"
    assert first["desacuerdo"] == "0.125"
    assert first["coincide_pm1"] == "1"


def test_a_zone_without_orders_leaves_the_panel_columns_empty() -> None:
    rows = _rows(ficha_csv(_results(HIGH, _zone(2, Concentration.LOW, {}))))

    silent = [row for row in rows if row["zona"] == "Zona 2"]
    assert len(silent) == 5
    assert {row["orden_panel"] for row in silent} == {""}
    assert {row["orden_evaluador_1"] for row in silent} == {""}


def test_the_summary_has_one_row_per_zone_and_the_test_between_zones() -> None:
    rows = _rows(resumen_csv(_results()))

    assert [row["zona"] for row in rows] == ["Zona 1", "Zona 2", "entre_zonas"]
    high = rows[0]
    assert (high["n_reportes"], high["evaluadores"]) == ("5", "2")
    assert "." in high["rho"]
    assert "," not in high["rho"]
    assert (high["reportes_zona"], high["avisos"], high["avisos_sin_decision"]) == ("7", "4", "1")
    between = rows[2]
    assert between["prueba"] == "mann_whitney"
    assert between["significativo"] in {"si", "no"}


def test_the_summary_says_why_the_test_between_zones_was_not_computed() -> None:
    rows = _rows(resumen_csv(_results(HIGH, _zone(2, Concentration.LOW, {}))))

    assert rows[1]["evaluadores"] == "0"
    assert rows[1]["rho"] == ""
    assert rows[2]["prueba"] == "no_calculable"
    assert rows[2]["observacion"] != ""


def test_the_review_of_reports_links_to_the_photo() -> None:
    report_id = uuid.uuid4()
    rows = _rows(
        reportes_csv(
            [
                ReviewReport(
                    report_id=report_id,
                    zone_name="Centro",
                    created_at=datetime(2026, 11, 1, 15, 30, tzinfo=UTC),
                    road_name=None,
                    status=ReportStatus.EVALUATED,
                    confirmations=2,
                )
            ]
        )
    )

    assert rows == [
        {
            "id_reporte": str(report_id),
            "zona": "Centro",
            "fecha_creacion": "2026-11-01T15:30:00+00:00",
            "via": "",
            "estado": "evaluado",
            "confirmaciones": "2",
            "foto": f"/api/v1/reports/{report_id}/photo",
        }
    ]


def test_the_review_of_warnings_lists_candidates_and_reports_pending_as_undecided() -> None:
    first, second, resulting = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    warning = ReviewWarning(
        warning_id=uuid.uuid4(),
        zone_name="Centro",
        shown_at=NOW,
        decision=WarningDecision.PENDING,
        resulting_report_id=None,
        candidates=[
            WarningCandidate(first, Decimal("3.40")),
            WarningCandidate(second, Decimal("12.50")),
        ],
    )
    created = ReviewWarning(
        warning_id=uuid.uuid4(),
        zone_name="Centro",
        shown_at=NOW,
        decision=WarningDecision.CREATED_ANYWAY,
        resulting_report_id=resulting,
        candidates=[],
    )

    rows = _rows(avisos_csv([warning, created]))

    assert rows[0]["decision"] == "sin_decision"
    assert rows[0]["candidatos"] == f"{first}:3.40;{second}:12.50"
    assert rows[0]["id_reporte_resultante"] == ""
    assert (rows[1]["decision"], rows[1]["id_reporte_resultante"]) == (
        "creo_igual",
        str(resulting),
    )


def test_no_file_carries_evaluator_identities() -> None:
    results = _results()

    text = b"".join([ficha_csv(results), resumen_csv(results)]).decode("utf-8")

    assert "@" not in text
    assert str(EVA_1) not in text
    assert str(EVA_2) not in text


def test_the_file_name_is_a_slug_of_the_round_name() -> None:
    assert export_filename("Piloto 1 — Pasto", "ficha") == "ronda-piloto-1-pasto-ficha.csv"
    assert export_filename("Ñuñoa: árbol", "avisos") == "ronda-nunoa-arbol-avisos.csv"
    assert export_filename("¿¡!?", "resumen") == "ronda-resumen.csv"


def test_text_that_a_spreadsheet_would_run_as_a_formula_is_neutralized() -> None:
    # Los nombres de vía vienen de OSM: un «=HYPERLINK(...)» no debe ejecutarse al abrir el CSV.
    report_id = uuid.uuid4()
    rows = _rows(
        reportes_csv(
            [
                ReviewReport(
                    report_id=report_id,
                    zone_name="+Zona",
                    created_at=NOW,
                    road_name='=HYPERLINK("http://example.invalid")',
                    status=ReportStatus.EVALUATED,
                    confirmations=0,
                )
            ]
        )
    )

    assert rows[0]["via"] == '\'=HYPERLINK("http://example.invalid")'
    assert rows[0]["zona"] == "'+Zona"


def test_negative_numbers_are_not_treated_as_formulas() -> None:
    rows = _rows(resumen_csv(_results()))

    # Zona 2 invierte el orden del motor: rho negativo, sin apóstrofo delante.
    assert rows[1]["rho"].startswith("-")
