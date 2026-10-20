import numpy as np

from fraud.cost import Costs, best_threshold, cost_curve, outcome

COSTS = Costs(fn_amount_multiplier=1.0, chargeback_fee=15.0, review_cost=5.0, friction_cost=2.0)


def test_outcome_arithmetic():
    y = np.array([1, 1, 0, 0])
    flag = np.array([1, 0, 1, 0])
    amt = np.array([100.0, 50.0, 20.0, 10.0])
    o = outcome(y, flag, amt, COSTS)
    assert (o["tp"], o["fp"], o["fn"], o["tn"]) == (1, 1, 1, 1)
    # 2 alerts * 5 review + 1 false alarm * 2 friction + missed (50 + 15)
    assert o["total_cost"] == 2 * 5 + 2 + 65


def test_cost_curve_matches_bruteforce():
    rng = np.random.default_rng(0)
    y = (rng.random(2000) < 0.05).astype(int)
    p = np.clip(rng.random(2000) * 0.3 + y * 0.4, 0, 1)
    amt = rng.gamma(2, 50, 2000)
    curve = cost_curve(y, p, amt, COSTS, thresholds=np.array([0.0, 0.2, 0.35, 0.5, 1.01]))
    for _, row in curve.iterrows():
        assert np.isclose(row.total_cost, outcome(y, p >= row.threshold, amt, COSTS)["total_cost"])


def test_cheap_reviews_lower_the_threshold():
    rng = np.random.default_rng(1)
    y = (rng.random(5000) < 0.03).astype(int)
    p = np.clip(rng.beta(1, 8, 5000) + y * rng.beta(4, 2, 5000), 0, 1)
    amt = rng.gamma(2, 80, 5000)
    cheap = best_threshold(y, p, amt, Costs(review_cost=1.0))
    pricey = best_threshold(y, p, amt, Costs(review_cost=50.0))
    assert cheap < pricey
