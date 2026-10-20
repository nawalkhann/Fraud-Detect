"""End-to-end plumbing check on a tiny file in the ULB layout. Says nothing about real accuracy."""


def test_train_runs_end_to_end(trained_ulb):
    root, _, res = trained_ulb
    report = (root / "reports" / "model_report_ulb.md").read_text()
    assert "train vs valid vs test" in report
    assert set(res["thresholds"]["lightgbm"]) == {"default_0.5", "max_accuracy", "max_f1", "min_cost"}
    assert (root / "models" / "ulb" / "lightgbm.joblib").exists()
    assert res["test_min_cost"]["total_cost"] <= res["no_model_cost"]
