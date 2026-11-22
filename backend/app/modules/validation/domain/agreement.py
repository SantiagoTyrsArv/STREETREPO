"""Métricas de acuerdo entre el ranking del motor y el del panel de expertos (HU-09).

Dominio puro: recibe órdenes ya cargados y devuelve cifras; no toca base de datos.
Cada evaluador entrega un orden estricto 1..n (sin empates), por lo que la W de
Kendall no necesita corrección por empates.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from math import isnan
from typing import Literal
from uuid import UUID

from scipy import stats

from app.modules.validation.domain.parameters import SIGNIFICANCE_ALPHA
from app.modules.validation.domain.zones import Concentration

_MIN_EVALUATORS_FOR_W = 2
_TWO_ZONES = 2
_MIN_POINTS_FOR_CORRELATION = 2
_NEIGHBOR_TOLERANCE = 1
_IDENTICAL_REASON = "Los desacuerdos de todas las zonas son idénticos"
_NO_ORDERS_REASON = "Se necesita al menos una zona de alta y una de baja concentración con órdenes"


@dataclass(frozen=True)
class ZoneRanking:
    """Órdenes de una zona: el del motor y el de cada evaluador que envió (1 = más urgente)."""

    zone_id: int
    concentration: Concentration
    motor_order: Mapping[UUID, int]
    evaluator_orders: Mapping[UUID, Mapping[UUID, int]]


@dataclass(frozen=True)
class Correlation:
    """Coeficiente de correlación de rangos y su valor p bilateral."""

    coefficient: float
    p_value: float


@dataclass(frozen=True)
class KendallW:
    """Concordancia entre evaluadores: W de Kendall, chi² y su valor p."""

    w: float
    chi2: float
    p_value: float


@dataclass(frozen=True)
class EvaluatorAgreement:
    """Correlaciones de un evaluador con el motor; None si no son definibles."""

    spearman: Correlation | None
    kendall: Correlation | None


@dataclass(frozen=True)
class ZoneAgreement:
    zone_id: int
    n_reports: int
    n_evaluators: int
    panel_order: Mapping[UUID, float]
    spearman: Correlation | None
    kendall: Correlation | None
    per_evaluator: Mapping[UUID, EvaluatorAgreement]
    kendall_w: KendallW | None
    within_one_pct: float
    disagreement: Mapping[UUID, float]


@dataclass(frozen=True)
class BetweenZones:
    test: Literal["mann_whitney", "kruskal_wallis"]
    statistic: float
    p_value: float
    significant: bool


@dataclass(frozen=True)
class NotComputable:
    reason: str


def is_significant(p_value: float) -> bool:
    """Significativo si el valor p es estrictamente menor que alfa."""
    return p_value < SIGNIFICANCE_ALPHA


def _is_constant(values: Sequence[float]) -> bool:
    return len(set(values)) <= 1


def _correlations(motor: Sequence[float], other: Sequence[float]) -> EvaluatorAgreement:
    """Spearman y Kendall; None si la correlación no está definida (entrada constante)."""
    if len(motor) < _MIN_POINTS_FOR_CORRELATION or _is_constant(motor) or _is_constant(other):
        return EvaluatorAgreement(None, None)
    rho = stats.spearmanr(motor, other)
    tau = stats.kendalltau(motor, other)
    return EvaluatorAgreement(
        Correlation(float(rho.statistic), float(rho.pvalue)),
        Correlation(float(tau.statistic), float(tau.pvalue)),
    )


def _kendall_w(orders: Sequence[Sequence[int]], n: int) -> KendallW:
    m = len(orders)
    sums = [sum(order[i] for order in orders) for i in range(n)]
    mean_sum = sum(sums) / n
    s = sum((value - mean_sum) ** 2 for value in sums)
    w = 12 * s / (m**2 * (n**3 - n))
    chi2 = m * (n - 1) * w
    return KendallW(w, chi2, float(stats.chi2.sf(chi2, n - 1)))


def zone_agreement(ranking: ZoneRanking) -> ZoneAgreement | None:
    """Acuerdo de una zona; None si ningún evaluador envió su orden."""
    if not ranking.evaluator_orders:
        return None
    report_ids = list(ranking.motor_order)
    for evaluator, orders in ranking.evaluator_orders.items():
        if set(orders) != set(ranking.motor_order):
            msg = f"El orden del evaluador {evaluator} no cubre exactamente los reportes de la zona"
            raise ValueError(msg)
    n = len(report_ids)
    motor = [ranking.motor_order[r] for r in report_ids]
    evaluator_lists = {
        evaluator: [orders[r] for r in report_ids]
        for evaluator, orders in ranking.evaluator_orders.items()
    }
    mean_positions = [
        sum(order[i] for order in evaluator_lists.values()) / len(evaluator_lists) for i in range(n)
    ]
    panel = [float(v) for v in stats.rankdata(mean_positions, method="average")]
    overall = _correlations(motor, panel)
    gaps = [abs(m - p) for m, p in zip(motor, panel, strict=True)]
    scale = max(n - 1, 1)
    within_one = 100 * sum(g <= _NEIGHBOR_TOLERANCE for g in gaps) / n
    m_count = len(evaluator_lists)
    return ZoneAgreement(
        zone_id=ranking.zone_id,
        n_reports=n,
        n_evaluators=m_count,
        panel_order=dict(zip(report_ids, panel, strict=True)),
        spearman=overall.spearman,
        kendall=overall.kendall,
        per_evaluator={e: _correlations(motor, o) for e, o in evaluator_lists.items()},
        kendall_w=(
            _kendall_w(list(evaluator_lists.values()), n)
            if m_count >= _MIN_EVALUATORS_FOR_W and n >= _MIN_POINTS_FOR_CORRELATION
            else None
        ),
        within_one_pct=within_one,
        disagreement=dict(zip(report_ids, (g / scale for g in gaps), strict=True)),
    )


def between_zones(
    agreements: Sequence[tuple[Concentration, ZoneAgreement]],
) -> BetweenZones | NotComputable:
    """Compara el desacuerdo entre zonas: Mann-Whitney con dos, Kruskal-Wallis con tres."""
    concentrations = {c for c, _ in agreements}
    if concentrations != {Concentration.HIGH, Concentration.LOW}:
        return NotComputable(_NO_ORDERS_REASON)
    groups = [list(a.disagreement.values()) for _, a in agreements]
    if _is_constant([v for group in groups for v in group]):
        return NotComputable(_IDENTICAL_REASON)
    test, statistic, p_value = _compare_groups(groups)
    if isnan(p_value):
        return NotComputable(_IDENTICAL_REASON)
    return BetweenZones(test, statistic, p_value, is_significant(p_value))


def _compare_groups(
    groups: Sequence[Sequence[float]],
) -> tuple[Literal["mann_whitney", "kruskal_wallis"], float, float]:
    if len(groups) == _TWO_ZONES:
        mw = stats.mannwhitneyu(groups[0], groups[1], alternative="two-sided")
        return "mann_whitney", float(mw.statistic), float(mw.pvalue)
    kw = stats.kruskal(*groups)
    return "kruskal_wallis", float(kw.statistic), float(kw.pvalue)
