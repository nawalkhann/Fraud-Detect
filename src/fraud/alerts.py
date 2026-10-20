"""Turn model scores into an alert queue an analyst can work top-down."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from fraud.config import REPO_ROOT
from fraud.cost import Costs, expected_loss
from fraud.features import FeatureBuilder

DISPLAY_COLUMNS = {
    "ieee": ["TransactionID", "event_time", "TransactionAmt", "ProductCD", "card4", "card6",
             "P_emaildomain", "DeviceType"],
    "ulb": ["TransactionID", "event_time", "TransactionAmt"],
}


def model_dir(dataset: str) -> Path:
    return Path(os.environ.get("FRAUD_MODEL_DIR") or REPO_ROOT / "models") / dataset


@dataclass
class Scorer:
    dataset: str
    model: object
    features: FeatureBuilder
    thresholds: dict

    @classmethod
    def load(cls, dataset: str, model_name: str = "lightgbm") -> "Scorer":
        d = model_dir(dataset)
        bundle = joblib.load(d / f"{model_name}.joblib")
        thresholds = json.loads((d / "thresholds.json").read_text())[model_name]
        return cls(dataset, bundle["model"], bundle["features"], thresholds)

    def score(self, raw: pd.DataFrame) -> np.ndarray:
        return self.model.predict_proba(self.features.transform(raw))[:, 1]

    def reasons(self, raw: pd.DataFrame, top: int = 3) -> list[list[dict]]:
        """Top features pushing each score up, from LightGBM's exact SHAP values (pred_contrib)."""
        X = self.features.transform(raw)
        contrib = self.model.predict(X, pred_contrib=True)[:, :-1]  # last column is the bias
        cols = np.array(self.features.columns_)
        out = []
        for i, row in enumerate(contrib):
            idx = np.argsort(-row)[:top]
            out.append([{"feature": str(cols[j]), "value": _jsonable(X.iloc[i, j]), "impact": round(float(row[j]), 4)}
                        for j in idx if row[j] > 0])
        return out


def _jsonable(v):
    if v is None or (isinstance(v, float) and np.isnan(v)) or v is pd.NA:
        return None
    return v.item() if hasattr(v, "item") else (v if isinstance(v, (int, float, str)) else str(v))


def build_queue(raw: pd.DataFrame, p: np.ndarray, threshold: float, costs: Costs, dataset: str) -> pd.DataFrame:
    """Flagged transactions ranked by expected loss (probability x what a miss would cost)."""
    cols = [c for c in DISPLAY_COLUMNS[dataset] if c in raw]
    q = raw[cols].copy()
    q["fraud_probability"] = p
    q["expected_loss"] = expected_loss(p, raw["TransactionAmt"].to_numpy(dtype=float), costs)
    if "isFraud" in raw:
        q["actual_fraud"] = raw["isFraud"].to_numpy()
    q = q[p >= threshold].sort_values("expected_loss", ascending=False)
    q.insert(0, "priority", np.arange(1, len(q) + 1))
    return q.reset_index(drop=True)
