"""Business cost of a decision threshold.

Every alert is reviewed by an analyst (review_cost), whether it is fraud or not. A false alarm
also annoys a good customer (friction_cost). A missed fraud loses the amount
(times fn_amount_multiplier) plus a chargeback fee. Correctly ignored legit traffic costs 0.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class Costs:
    fn_amount_multiplier: float = 1.0
    chargeback_fee: float = 15.0
    review_cost: float = 5.0
    friction_cost: float = 0.0

    @classmethod
    def from_config(cls, cfg: dict) -> "Costs":
        return cls(**cfg["costs"])

    def miss_cost(self, amount: np.ndarray) -> np.ndarray:
        return amount * self.fn_amount_multiplier + self.chargeback_fee


def outcome(y: np.ndarray, flagged: np.ndarray, amount: np.ndarray, costs: Costs) -> dict:
    y, flagged = y.astype(bool), flagged.astype(bool)
    tp, fp = flagged & y, flagged & ~y
    fn, tn = ~flagged & y, ~flagged & ~y
    review = flagged.sum() * costs.review_cost
    friction = fp.sum() * costs.friction_cost
    missed = costs.miss_cost(amount[fn]).sum()
    return {
        "tp": int(tp.sum()), "fp": int(fp.sum()), "fn": int(fn.sum()), "tn": int(tn.sum()),
        "alerts": int(flagged.sum()),
        "fraud_dollars_caught": float(amount[tp].sum()),
        "fraud_dollars_missed": float(amount[fn].sum()),
        "review_cost": float(review), "friction_cost": float(friction), "missed_fraud_cost": float(missed),
        "total_cost": float(review + friction + missed),
    }


def cost_curve(y: np.ndarray, p: np.ndarray, amount: np.ndarray, costs: Costs,
               thresholds: np.ndarray | None = None) -> pd.DataFrame:
    """Total cost and confusion counts for each candidate threshold (vectorised via sorting)."""
    if thresholds is None:
        thresholds = np.unique(np.concatenate([np.linspace(0, 1, 1001), np.quantile(p, np.linspace(0, 1, 2001))]))
    y = y.astype(bool)
    order = np.argsort(-p, kind="stable")
    p_sorted, y_sorted, amt_sorted = p[order], y[order], amount[order]
    miss_sorted = costs.miss_cost(amt_sorted) * y_sorted
    # number flagged at threshold t = count of p >= t
    n_flag = np.searchsorted(-p_sorted, -thresholds, side="right")
    cum_tp = np.concatenate([[0], np.cumsum(y_sorted)])[n_flag]
    cum_miss_avoided = np.concatenate([[0], np.cumsum(miss_sorted)])[n_flag]
    fp = n_flag - cum_tp
    total_miss = miss_sorted.sum()
    total = n_flag * costs.review_cost + fp * costs.friction_cost + (total_miss - cum_miss_avoided)
    return pd.DataFrame({
        "threshold": thresholds, "alerts": n_flag, "tp": cum_tp, "fp": fp, "fn": y.sum() - cum_tp,
        "total_cost": total,
    })


def best_threshold(y: np.ndarray, p: np.ndarray, amount: np.ndarray, costs: Costs) -> float:
    curve = cost_curve(y, p, amount, costs)
    return float(curve.loc[curve["total_cost"].idxmin(), "threshold"])


def expected_loss(p: np.ndarray, amount: np.ndarray, costs: Costs) -> np.ndarray:
    """Expected cost of letting a transaction through; used to rank the alert queue."""
    return p * costs.miss_cost(amount)


def flag_by_expected_loss(p: np.ndarray, amount: np.ndarray, costs: Costs) -> np.ndarray:
    """Amount-aware rule: alert when letting it through costs more, in expectation, than reviewing it.

    Pass: p * (amount * multiplier + chargeback).  Alert: review + (1 - p) * friction.
    No parameter is tuned, so with calibrated probabilities it carries over to new data, and a
    $2,000 transaction gets an alert at a far lower probability than a $5 one.
    """
    return p * costs.miss_cost(amount) > costs.review_cost + (1 - p) * costs.friction_cost


def decide(p: np.ndarray, amount: np.ndarray, costs: Costs, policy: str, thresholds: dict) -> np.ndarray:
    if policy == "expected_loss":
        return flag_by_expected_loss(p, amount, costs)
    return p >= thresholds[policy]
