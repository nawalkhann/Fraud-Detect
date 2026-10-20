"""End-to-end plumbing check on a tiny file in the ULB layout. Says nothing about real accuracy."""
import numpy as np
import pandas as pd

from fraud.config import load_config
from fraud.train import run
from fraud.ulb import prepare


def test_train_runs_end_to_end(tmp_path, monkeypatch):
    rng = np.random.default_rng(0)
    n = 6000
    y = (rng.random(n) < 0.03).astype(int)
    raw = pd.DataFrame({"Time": np.sort(rng.uniform(0, 172_792, n)).round()})
    for i in range(1, 29):
        raw[f"V{i}"] = rng.normal(size=n) + y * (1.5 if i in (4, 14) else 0)
    raw["Amount"] = rng.gamma(2, 40, n).round(2)
    raw["Class"] = y
    (tmp_path / "raw").mkdir()
    raw.to_csv(tmp_path / "raw" / "creditcard.csv", index=False)
    monkeypatch.setenv("FRAUD_DATA_DIR", str(tmp_path))

    cfg = load_config()
    prepare(cfg)
    res = run(cfg, "ulb", out_root=tmp_path)
    report = (tmp_path / "reports" / "model_report_ulb.md").read_text()
    assert "train vs valid vs test" in report
    assert set(res["thresholds"]["lightgbm"]) == {"default_0.5", "max_accuracy", "max_f1", "min_cost"}
    assert (tmp_path / "models" / "ulb" / "lightgbm.joblib").exists()
    assert res["test_min_cost"]["total_cost"] <= res["no_model_cost"]
