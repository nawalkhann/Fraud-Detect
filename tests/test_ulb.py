import numpy as np
import pandas as pd

from fraud.config import Paths
from fraud.data import time_split
from fraud.profile import build_report
from fraud.ulb import load


def test_ulb_maps_to_common_schema_and_splits_by_hour(tmp_path):
    """Tiny file in the creditcard.csv layout, for testing the plumbing only."""
    rng = np.random.default_rng(0)
    n = 500
    raw = pd.DataFrame({"Time": np.sort(rng.uniform(0, 172_792, n)).round()})
    for i in range(1, 29):
        raw[f"V{i}"] = rng.normal(size=n)
    raw["Amount"] = rng.gamma(2, 40, n).round(2)
    raw["Class"] = (rng.random(n) < 0.05).astype(int)
    paths = Paths(tmp_path).ensure()
    raw.to_csv(paths.raw / "creditcard.csv", index=False)

    df = load(paths, "2013-09-01")
    assert {"TransactionID", "isFraud", "TransactionAmt", "TransactionDT", "hour"} <= set(df.columns)
    assert df["hour"].max() <= 48

    s = time_split(df, 30, 39, column="hour")
    assert s["train"]["hour"].max() < 30 <= s["valid"]["hour"].min()
    assert s["valid"]["hour"].max() < 39 <= s["test"]["hour"].min()
    assert sum(len(p) for p in s.values()) == n

    report = build_report(s, "ulb")
    assert "ULB" in report and "6-hour block" in report
