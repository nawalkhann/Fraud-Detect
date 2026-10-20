import numpy as np
import pandas as pd
import pytest

from fraud.config import Paths
from fraud.data import add_time_columns, load_joined, time_split
from fraud.profile import build_report, psi


@pytest.fixture
def raw_dir(tmp_path):
    """Tiny files with the IEEE-CIS column layout, for testing the plumbing only."""
    rng = np.random.default_rng(0)
    n = 400
    tx = pd.DataFrame({
        "TransactionID": np.arange(3_000_000, 3_000_000 + n),
        "isFraud": (rng.random(n) < 0.05).astype(int),
        "TransactionDT": np.sort(rng.integers(86_400, 182 * 86_400, n)),
        "TransactionAmt": rng.gamma(2, 50, n).round(2),
        "ProductCD": rng.choice(list("WCHRS"), n),
        "card1": rng.integers(1000, 18000, n),
        "card4": rng.choice(["visa", "mastercard", None], n),
        "C1": rng.integers(0, 5, n).astype(float),
        "D1": np.where(rng.random(n) < 0.3, np.nan, rng.integers(0, 500, n)),
        "V1": np.where(rng.random(n) < 0.5, np.nan, 1.0),
    })
    idn = pd.DataFrame({
        "TransactionID": tx["TransactionID"].iloc[::4].values,
        "id_01": -5.0, "DeviceType": "desktop",
    })
    paths = Paths(tmp_path).ensure()
    tx.to_csv(paths.raw / "train_transaction.csv", index=False)
    idn.to_csv(paths.raw / "train_identity.csv", index=False)
    return paths


def test_join_keeps_every_transaction(raw_dir):
    df = load_joined(raw_dir)
    assert len(df) == 400
    assert df["has_identity"].sum() == 100
    assert df["TransactionAmt"].dtype == np.float32
    assert str(df["ProductCD"].dtype) == "category"


def test_time_split_is_ordered_and_disjoint(raw_dir):
    df = add_time_columns(load_joined(raw_dir), "2017-12-01")
    s = time_split(df, 120, 152, gap_days=3)
    assert s["train"]["day"].max() < 120
    assert s["valid"]["day"].min() >= 123 and s["valid"]["day"].max() < 152
    assert s["test"]["day"].min() >= 152
    ids = [set(p["TransactionID"]) for p in s.values()]
    assert not (ids[0] & ids[1] or ids[0] & ids[2] or ids[1] & ids[2])


def test_time_split_rejects_bad_config(raw_dir):
    df = add_time_columns(load_joined(raw_dir), "2017-12-01")
    with pytest.raises(ValueError):
        time_split(df, 150, 120)


def test_psi_detects_shift():
    rng = np.random.default_rng(1)
    a = pd.Series(rng.normal(0, 1, 5000))
    assert psi(a, pd.Series(rng.normal(0, 1, 5000))) < 0.05
    assert psi(a, pd.Series(rng.normal(1.5, 1, 5000))) > 0.25


def test_report_builds(raw_dir):
    df = add_time_columns(load_joined(raw_dir), "2017-12-01")
    report = build_report(time_split(df, 120, 152))
    assert "IEEE-CIS" in report and "Drift" in report
