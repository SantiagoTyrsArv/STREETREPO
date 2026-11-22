from uuid import UUID, uuid4

import pytest
from scipy import stats

from app.modules.validation.domain.agreement import (
    BetweenZones,
    NotComputable,
    ZoneAgreement,
    ZoneRanking,
    between_zones,
    is_significant,
    zone_agreement,
)
from app.modules.validation.domain.zones import Concentration


def _ids(n: int) -> list[UUID]:
    return [uuid4() for _ in range(n)]


def _ranking(
    ids: list[UUID],
    motor: list[int],
    evaluators: list[list[int]],
    concentration: Concentration = Concentration.HIGH,
    zone_id: int = 1,
) -> ZoneRanking:
    return ZoneRanking(
        zone_id=zone_id,
        concentration=concentration,
        motor_order=dict(zip(ids, motor, strict=True)),
        evaluator_orders={uuid4(): dict(zip(ids, o, strict=True)) for o in evaluators},
    )


def _agreement(ranking: ZoneRanking) -> ZoneAgreement:
    result = zone_agreement(ranking)
    assert result is not None
    return result


def test_identical_orders_give_perfect_agreement() -> None:
    ids = _ids(5)
    result = _agreement(_ranking(ids, [1, 2, 3, 4, 5], [[1, 2, 3, 4, 5]]))
    assert result.spearman.coefficient == pytest.approx(1.0)
    assert result.kendall.coefficient == pytest.approx(1.0)
    assert result.within_one_pct == 100.0
    assert all(v == 0 for v in result.disagreement.values())
    assert result.n_reports == 5
    assert result.n_evaluators == 1


def test_reversed_order_gives_minus_one() -> None:
    ids = _ids(5)
    result = _agreement(_ranking(ids, [1, 2, 3, 4, 5], [[5, 4, 3, 2, 1]]))
    assert result.spearman.coefficient == pytest.approx(-1.0)
    assert result.kendall.coefficient == pytest.approx(-1.0)


def test_panel_order_averages_evaluators() -> None:
    ids = _ids(5)
    result = _agreement(_ranking(ids, [1, 2, 3, 4, 5], [[1, 2, 3, 4, 5], [2, 1, 3, 4, 5]]))
    expected = [1.5, 1.5, 3.0, 4.0, 5.0]
    for report_id, value in zip(ids, expected, strict=True):
        assert result.panel_order[report_id] == pytest.approx(value)


def test_kendall_w_perfect_agreement_is_one() -> None:
    ids = _ids(5)
    order = [1, 2, 3, 4, 5]
    result = _agreement(_ranking(ids, order, [order, order, order]))
    assert result.kendall_w is not None
    assert result.kendall_w.w == pytest.approx(1.0)
    assert result.kendall_w.chi2 == pytest.approx(3 * 4 * 1.0)


def test_kendall_w_needs_two_evaluators() -> None:
    ids = _ids(5)
    result = _agreement(_ranking(ids, [1, 2, 3, 4, 5], [[1, 2, 3, 4, 5]]))
    assert result.kendall_w is None


def test_within_one_counts_neighbors() -> None:
    ids = _ids(6)
    shifted = _agreement(_ranking(ids, [1, 2, 3, 4, 5, 6], [[2, 1, 4, 3, 6, 5]]))
    assert shifted.within_one_pct == 100.0
    far = _agreement(_ranking(ids, [1, 2, 3, 4, 5, 6], [[4, 2, 3, 1, 5, 6]]))
    assert far.within_one_pct == pytest.approx(100 * 4 / 6)


def test_per_evaluator_correlations() -> None:
    ids = _ids(5)
    result = _agreement(_ranking(ids, [1, 2, 3, 4, 5], [[1, 2, 3, 4, 5], [5, 4, 3, 2, 1]]))
    coefficients = sorted(s.coefficient for s, _ in result.per_evaluator.values())
    assert coefficients == pytest.approx([-1.0, 1.0])


def test_zone_without_orders_is_none() -> None:
    ids = _ids(5)
    assert zone_agreement(_ranking(ids, [1, 2, 3, 4, 5], [])) is None


def _agreements_for(
    disagreement_sets: list[list[int]],
) -> list[tuple[Concentration, ZoneAgreement]]:
    concentrations = [Concentration.HIGH, Concentration.LOW, Concentration.LOW]
    out = []
    for i, order in enumerate(disagreement_sets):
        ids = _ids(6)
        out.append(
            (
                concentrations[i],
                _agreement(_ranking(ids, [1, 2, 3, 4, 5, 6], [order], concentrations[i], i + 1)),
            )
        )
    return out


def test_two_zones_use_mann_whitney() -> None:
    pairs = _agreements_for([[1, 2, 3, 4, 5, 6], [6, 2, 3, 4, 5, 1]])
    result = between_zones(pairs)
    assert isinstance(result, BetweenZones)
    assert result.test == "mann_whitney"
    expected = stats.mannwhitneyu(
        list(pairs[0][1].disagreement.values()),
        list(pairs[1][1].disagreement.values()),
        alternative="two-sided",
    )
    assert result.statistic == pytest.approx(float(expected.statistic))
    assert result.p_value == pytest.approx(float(expected.pvalue))


def test_three_zones_use_kruskal_wallis() -> None:
    pairs = _agreements_for([[1, 2, 3, 4, 5, 6], [6, 2, 3, 4, 5, 1], [2, 1, 4, 3, 6, 5]])
    result = between_zones(pairs)
    assert isinstance(result, BetweenZones)
    assert result.test == "kruskal_wallis"
    expected = stats.kruskal(*[list(a.disagreement.values()) for _, a in pairs])
    assert result.statistic == pytest.approx(float(expected.statistic))
    assert result.p_value == pytest.approx(float(expected.pvalue))


def test_between_zones_requires_high_and_low() -> None:
    ids_a, ids_b = _ids(5), _ids(5)
    a = _agreement(_ranking(ids_a, [1, 2, 3, 4, 5], [[1, 2, 3, 4, 5]], zone_id=1))
    b = _agreement(_ranking(ids_b, [1, 2, 3, 4, 5], [[2, 1, 3, 4, 5]], zone_id=2))
    result = between_zones([(Concentration.HIGH, a), (Concentration.HIGH, b)])
    assert isinstance(result, NotComputable)
    assert "alta y una de baja" in result.reason


def test_significance_uses_alpha() -> None:
    assert is_significant(0.049) is True
    assert is_significant(0.05) is False
