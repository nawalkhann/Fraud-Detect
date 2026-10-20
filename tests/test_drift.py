import json

from fraud.alerts import model_dir
from fraud.data import load_split
from fraud.drift import check


def test_metadata_written(trained_ulb):
    meta = json.loads((model_dir("ulb") / "metadata.json").read_text())
    assert meta["dataset"] == "ulb" and 0 <= meta["test"]["pr_auc"] <= 1


def test_drift_flags_shifted_batch_only(trained_ulb):
    _, cfg, _ = trained_ulb
    batch = load_split(cfg, "train", dataset="ulb").sample(2000, random_state=1)
    assert not check("ulb", batch).query("check != 'mean_fraud_score_shift'")["alert"].any()
    shifted = batch.assign(TransactionAmt=batch["TransactionAmt"] * 5, V14=batch["V14"] + 3)
    res = check("ulb", shifted).set_index("check")
    assert res.loc["TransactionAmt", "alert"] and res.loc["V14", "alert"]
