"""CSV de la ficha comparativa y de la revisión manual (objetivo 4, sección 8 del diseño).

Decimales con punto, para el análisis; UTF-8 con BOM, para que la hoja de cálculo lea bien
las tildes. Los evaluadores solo aparecen como ``orden_evaluador_k`` (Ley 1581): ni nombre,
ni correo, ni id.
"""

import csv
import io
import re
import unicodedata
import uuid
from collections.abc import Iterable, Mapping, Sequence
from decimal import Decimal
from typing import Final

from app.modules.validation.domain.agreement import (
    NEIGHBOR_TOLERANCE,
    BetweenZones,
    Correlation,
    ZoneAgreement,
)
from app.modules.validation.domain.results import (
    ReviewReport,
    ReviewWarning,
    RoundResults,
    ZoneResult,
)
from app.modules.validation.domain.warnings import WarningDecision

BOM: Final = "﻿"
# Ruta de la API (no URL completa): el archivo no depende del dominio donde se despliega.
PHOTO_PATH: Final = "/api/v1/reports/{report_id}/photo"
BETWEEN_ZONES_ROW: Final = "entre_zonas"
NOT_COMPUTABLE: Final = "no_calculable"
_SIGNIFICANT_DIGITS: Final = 6
_DECISION_LABELS: Final = {
    WarningDecision.PENDING: "sin_decision",
    WarningDecision.CONFIRMED: WarningDecision.CONFIRMED.value,
    WarningDecision.CREATED_ANYWAY: WarningDecision.CREATED_ANYWAY.value,
}

_SUMMARY_COLUMNS: Final = (
    "zona",
    "concentracion",
    "n_reportes",
    "evaluadores",
    "rho",
    "p_rho",
    "tau",
    "p_tau",
    "w",
    "p_w",
    "coincidencia_pm1_pct",
    "reportes_zona",
    "reportes_con_confirmacion",
    "confirmaciones",
    "avisos",
    "avisos_confirmo",
    "avisos_creo_igual",
    "avisos_sin_decision",
    "prueba",
    "estadistico",
    "p",
    "significativo",
    "observacion",
)


def _number(value: float | Decimal | None) -> str:
    """Punto decimal y sin ceros sobrantes; vacío si no hay valor."""
    if value is None:
        return ""
    if isinstance(value, Decimal):
        return format(value.normalize(), "f")
    return format(value, f".{_SIGNIFICANT_DIGITS}g")


def _encode(header: Sequence[str], rows: Iterable[Sequence[object]]) -> bytes:
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(header)
    writer.writerows(rows)
    return (BOM + buffer.getvalue()).encode("utf-8")


def _evaluator_count(results: RoundResults) -> int:
    return max(results.evaluator_numbers.values(), default=0)


def _ficha_rows(result: ZoneResult, numbers: Mapping[uuid.UUID, int], k: int) -> list[list[str]]:
    zone, agreement = result.zone, result.agreement
    rows = []
    for entry in zone.entries:
        evaluator_columns = [""] * k
        for evaluator, orders in zone.evaluator_orders.items():
            evaluator_columns[numbers[evaluator] - 1] = str(orders[entry.report_id])
        panel = agreement.panel_order[entry.report_id] if agreement else None
        rows.append(
            [
                str(entry.report_id),
                zone.name,
                zone.concentration.value,
                _number(entry.urgency_score),
                str(entry.motor_order),
                _number(panel),
                _number(agreement.disagreement[entry.report_id]) if agreement else "",
                ""
                if panel is None
                else str(int(abs(entry.motor_order - panel) <= NEIGHBOR_TOLERANCE)),
                *evaluator_columns,
            ]
        )
    return rows


def ficha_csv(results: RoundResults) -> bytes:
    """Una fila por reporte de la ronda: orden del motor, del panel y de cada evaluador."""
    k = _evaluator_count(results)
    header = [
        "id_reporte",
        "zona",
        "concentracion",
        "puntaje_u",
        "orden_motor",
        "orden_panel",
        "desacuerdo",
        "coincide_pm1",
        *(f"orden_evaluador_{i}" for i in range(1, k + 1)),
    ]
    numbers = dict(results.evaluator_numbers)
    return _encode(header, (row for zone in results.zones for row in _ficha_rows(zone, numbers, k)))


def _correlation(value: Correlation | None) -> list[str]:
    return ["", ""] if value is None else [_number(value.coefficient), _number(value.p_value)]


def _agreement_columns(agreement: ZoneAgreement | None) -> list[str]:
    if agreement is None:
        return ["0", *[""] * 7]
    w = agreement.kendall_w
    return [
        str(agreement.n_evaluators),
        *_correlation(agreement.spearman),
        *_correlation(agreement.kendall),
        *(["", ""] if w is None else [_number(w.w), _number(w.p_value)]),
        _number(agreement.within_one_pct),
    ]


def _summary_row(result: ZoneResult) -> list[str]:
    dedup = result.dedup
    return [
        result.zone.name,
        result.zone.concentration.value,
        str(len(result.zone.entries)),
        *_agreement_columns(result.agreement),
        *(
            str(value)
            for value in (
                dedup.reports,
                dedup.reports_confirmed,
                dedup.confirmations,
                dedup.warnings_total,
                dedup.warnings_confirmed,
                dedup.warnings_created_anyway,
                dedup.warnings_pending,
            )
        ),
        *[""] * 5,
    ]


def _between_row(results: RoundResults) -> list[str]:
    empty = [""] * (len(_SUMMARY_COLUMNS) - 6)
    between = results.between
    if isinstance(between, BetweenZones):
        return [
            BETWEEN_ZONES_ROW,
            *empty,
            between.test,
            _number(between.statistic),
            _number(between.p_value),
            "si" if between.significant else "no",
            "",
        ]
    return [BETWEEN_ZONES_ROW, *empty, NOT_COMPUTABLE, "", "", "", between.reason]


def resumen_csv(results: RoundResults) -> bytes:
    """Una fila por zona (acuerdo y deduplicación) y una final con la prueba entre zonas."""
    rows = [_summary_row(zone) for zone in results.zones]
    rows.append(_between_row(results))
    return _encode(_SUMMARY_COLUMNS, rows)


def reportes_csv(reports: Sequence[ReviewReport]) -> bytes:
    """Reportes de las zonas para que el revisor marque los duplicados reales."""
    return _encode(
        ("id_reporte", "zona", "fecha_creacion", "via", "estado", "confirmaciones", "foto"),
        (
            (
                str(r.report_id),
                r.zone_name,
                r.created_at.isoformat(),
                r.road_name or "",
                r.status.value,
                str(r.confirmations),
                PHOTO_PATH.format(report_id=r.report_id),
            )
            for r in reports
        ),
    )


def avisos_csv(warnings: Sequence[ReviewWarning]) -> bytes:
    """Avisos de duplicado con sus candidatos (``id:distancia`` separados por ``;``)."""
    return _encode(
        ("id_aviso", "zona", "fecha", "decision", "id_reporte_resultante", "candidatos"),
        (
            (
                str(w.warning_id),
                w.zone_name,
                w.shown_at.isoformat(),
                _DECISION_LABELS[w.decision],
                "" if w.resulting_report_id is None else str(w.resulting_report_id),
                ";".join(f"{c.report_id}:{c.distance_m:.2f}" for c in w.candidates),
            )
            for w in warnings
        ),
    )


def export_filename(round_name: str, kind: str) -> str:
    """``ronda-<nombre>-<tipo>.csv`` en minúsculas ASCII, apto para cualquier sistema."""
    ascii_name = unicodedata.normalize("NFKD", round_name).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_name.lower()).strip("-")
    return f"ronda-{slug}-{kind}.csv" if slug else f"ronda-{kind}.csv"
