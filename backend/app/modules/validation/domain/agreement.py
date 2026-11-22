"""Métricas de acuerdo entre el ranking del motor y el del panel de expertos (HU-09).

Dominio puro: recibe órdenes ya cargados y devuelve cifras; no toca base de datos.
Cada evaluador entrega un orden estricto 1..n (sin empates), por lo que la W de
Kendall no necesita corrección por empates.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Literal
from uuid import UUID

from scipy import stats

from app.modules.validation.domain.parameters import SIGNIFICANCE_ALPHA
from app.modules.validation.domain.zones import Concentration

_MIN_EVALUATORS_FOR_W = 2
_TWO_ZONES = 2
_NEIGHBOR_TOLERANCE = 1
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
    coefficient: float
    p_value: float


@dataclass(frozen=True)
class KendallW:
    w: float
    chi2: float
    p_value: float


@dataclass(frozen=True)
class ZoneAgreement:
    zone_id: int
    n_reports: int
    n_evaluators: int
    panel_order: Mapping[UUID, float]
    spearman: Correlation
    kendall: Correlation
    per_evaluator: Mapping[UUID, tuple[Correlation, Correlation]]
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


def _correlations(
    motor: Sequence[float], other: Sequence[float]
) -> tuple[Correlation, Correlation]:
    rho = stats.spearmanr(motor, other)
    tau = stats.kendalltau(motor, other)
    return (
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
    spearman, kendall = _correlations(motor, panel)
    gaps = [abs(m - p) for m, p in zip(motor, panel, strict=True)]
    scale = max(n - 1, 1)
    within_one = 100 * sum(g <= _NEIGHBOR_TOLERANCE for g in gaps) / n
    m_count = len(evaluator_lists)
    return ZoneAgreement(
        zone_id=ranking.zone_id,
        n_reports=n,
        n_evaluators=m_count,
        panel_order=dict(zip(report_ids, panel, strict=True)),
        spearman=spearman,
        kendall=kendall,
        per_evaluator={e: _correlations(motor, o) for e, o in evaluator_lists.items()},
        kendall_w=(
            _kendall_w(list(evaluator_lists.values()), n)
            if m_count >= _MIN_EVALUATORS_FOR_W
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
    if len(groups) == _TWO_ZONES:
        mw = stats.mannwhitneyu(groups[0], groups[1], alternative="two-sided")
        statistic, p_value = float(mw.statistic), float(mw.pvalue)
        return BetweenZones("mann_whitney", statistic, p_value, is_significant(p_value))
    try:
        kw = stats.kruskal(*groups)
    except ValueError:
        return NotComputable("Los desacuerdos de todas las zonas son idénticos")
    statistic, p_value = float(kw.statistic), float(kw.pvalue)
    return BetweenZones("kruskal_wallis", statistic, p_value, is_significant(p_value))
