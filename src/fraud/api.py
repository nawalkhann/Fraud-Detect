"""Real-time scoring service.

    uvicorn fraud.api:app --port 8000          # FRAUD_DATASET=ieee|ulb (default ieee)

POST /score with {"transactions": [{...raw columns...}]} returns a probability, the
cost-optimal decision, expected loss and the top reasons for each transaction.
"""
from __future__ import annotations

import os
from functools import lru_cache

import pandas as pd
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from fraud.alerts import Scorer
from fraud.config import load_config
from fraud.cost import Costs, expected_loss

app = FastAPI(title="Fraud scoring", version="0.1.0")


class ScoreRequest(BaseModel):
    transactions: list[dict] = Field(..., min_length=1, max_length=10_000)


@lru_cache(maxsize=1)
def scorer() -> Scorer:
    return Scorer.load(os.environ.get("FRAUD_DATASET", "ieee"))


@lru_cache(maxsize=1)
def costs() -> Costs:
    return Costs.from_config(load_config())


@app.get("/health")
def health() -> dict:
    s = scorer()
    return {"status": "ok", "dataset": s.dataset, "threshold": s.thresholds["min_cost"]}


@app.post("/score")
def score(req: ScoreRequest) -> dict:
    s = scorer()
    raw = pd.DataFrame(req.transactions)
    missing = {"TransactionDT", "TransactionAmt"} - set(raw.columns)
    if missing:
        raise HTTPException(422, f"missing required fields: {sorted(missing)}")
    for col, cats in s.features.categories_.items():
        if col in raw:
            raw[col] = pd.Categorical(raw[col], categories=cats)
    p = s.score(raw)
    t = s.thresholds["min_cost"]
    el = expected_loss(p, raw["TransactionAmt"].to_numpy(dtype=float), costs())
    reasons = s.reasons(raw)
    ids = raw["TransactionID"].tolist() if "TransactionID" in raw else list(range(len(raw)))
    return {"threshold": t, "results": [
        {"TransactionID": i, "fraud_probability": round(float(pi), 6), "alert": bool(pi >= t),
         "expected_loss": round(float(e), 2), "reasons": r}
        for i, pi, e, r in zip(ids, p, el, reasons)]}
