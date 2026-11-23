import warnings
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
    coefficients = sorted(
        e.spearman.coefficient for e in result.per_evaluator.values() if e.spearman
    )
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


def test_constant_panel_gives_none_without_warnings() -> None:
    ids = _ids(5)
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        result = _agreement(_ranking(ids, [1, 2, 3, 4, 5], [[1, 2, 3, 4, 5], [5, 4, 3, 2, 1]]))
    assert result.spearman is None
    assert result.kendall is None
    assert all(v == 3.0 for v in result.panel_order.values())
    assert all(e.spearman and e.kendall for e in result.per_evaluator.values())


def test_two_reports_are_computable() -> None:
    ids = _ids(2)
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        result = _agreement(_ranking(ids, [1, 2], [[1, 2], [1, 2]]))
    assert result.spearman is not None
    assert result.spearman.coefficient == pytest.approx(1.0)
    assert result.kendall_w is not None


def test_single_report_has_no_correlation() -> None:
    ids = _ids(1)
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        result = _agreement(_ranking(ids, [1], [[1], [1]]))
    assert result.spearman is None
    assert result.kendall_w is None
    assert result.disagreement[ids[0]] == 0.0


def test_matches_scipy_on_shuffled_orders() -> None:
    ids = _ids(8)
    order = [3, 7, 1, 8, 2, 5, 4, 6]
    result = _agreement(_ranking(ids, list(range(1, 9)), [order]))
    rho = stats.spearmanr(list(range(1, 9)), order)
    tau = stats.kendalltau(list(range(1, 9)), order)
    assert result.spearman is not None
    assert result.kendall is not None
    assert result.spearman.coefficient == pytest.approx(float(rho.statistic))
    assert result.spearman.p_value == pytest.approx(float(rho.pvalue))
    assert result.kendall.coefficient == pytest.approx(float(tau.statistic))
    assert result.kendall.p_value == pytest.approx(float(tau.pvalue))
    (only,) = result.per_evaluator.values()
    assert only.spearman == result.spearman
    assert only.kendall == result.kendall


def test_kendall_w_partial_agreement_hand_computed() -> None:
    # m=3, n=4. Rangos: [1,2,3,4], [1,3,2,4], [2,1,3,4] -> sumas 4,6,8,12; media 7.5
    # S = 12.25 + 2.25 + 0.25 + 20.25 = 35; W = 12*35 / (9*(64-4)) = 420/540
    ids = _ids(4)
    result = _agreement(_ranking(ids, [1, 2, 3, 4], [[1, 2, 3, 4], [1, 3, 2, 4], [2, 1, 3, 4]]))
    assert result.kendall_w is not None
    w = 420 / 540
    assert result.kendall_w.w == pytest.approx(w)
    assert result.kendall_w.chi2 == pytest.approx(3 * 3 * w)
    assert result.kendall_w.p_value == pytest.approx(float(stats.chi2.sf(9 * w, 3)))


def test_evaluator_order_must_cover_zone_reports() -> None:
    ids = _ids(5)
    ranking = _ranking(ids, [1, 2, 3, 4, 5], [[1, 2, 3, 4, 5]])
    bad = ZoneRanking(
        zone_id=1,
        concentration=Concentration.HIGH,
        motor_order=ranking.motor_order,
        evaluator_orders={uuid4(): {ids[0]: 1, uuid4(): 2}},
    )
    with pytest.raises(ValueError, match="no cubre"):
        zone_agreement(bad)


def test_identical_disagreements_are_not_computable_for_both_tests() -> None:
    perfect = [[1, 2, 3, 4, 5, 6]] * 3
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        two = between_zones(_agreements_for(perfect[:2]))
        three = between_zones(_agreements_for(perfect))
    assert isinstance(two, NotComputable)
    assert isinstance(three, NotComputable)
