from pathlib import Path

import numpy as np
from fastapi.testclient import TestClient

from fraud.alerts import Scorer, build_queue
from fraud.cost import Costs
from fraud.data import load_split

APP = Path(__file__).resolve().parents[1] / "app" / "dashboard.py"


def test_queue_is_ranked_by_expected_loss(trained_ulb):
    _, cfg, _ = trained_ulb
    scorer = Scorer.load("ulb")
    test = load_split(cfg, "test", dataset="ulb")
    p = scorer.score(test)
    q = build_queue(test, p, scorer.thresholds["min_cost"], Costs(), "ulb")
    assert len(q) == (p >= scorer.thresholds["min_cost"]).sum()
    assert q["expected_loss"].is_monotonic_decreasing
    assert q["priority"].tolist() == list(range(1, len(q) + 1))
    reasons = scorer.reasons(test.head(3))
    assert all(r["impact"] > 0 for rs in reasons for r in rs)


def test_api_scores_raw_transactions(trained_ulb):
    _, cfg, _ = trained_ulb
    import os
    os.environ["FRAUD_DATASET"] = "ulb"
    from fraud import api
    api.scorer.cache_clear()
    client = TestClient(api.app)
    assert client.get("/health").json()["dataset"] == "ulb"

    rows = load_split(cfg, "test", dataset="ulb").head(5)
    payload = rows.drop(columns=["isFraud", "event_time", "hour", "day"]).to_dict(orient="records")
    body = client.post("/score", json={"transactions": payload}).json()
    assert len(body["results"]) == 5
    assert all(0 <= r["fraud_probability"] <= 1 for r in body["results"])
    assert client.post("/score", json={"transactions": [{"V1": 1.0}]}).status_code == 422


def test_dashboard_renders(trained_ulb):
    from streamlit.testing.v1 import AppTest
    at = AppTest.from_file(str(APP), default_timeout=120).run()
    assert not at.exception, at.exception
    assert any("Fraud alert queue" in t.value for t in at.title)
    assert len(at.metric) == 5
