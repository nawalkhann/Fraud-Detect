"""Drift check: compare a batch of recent transactions with the model's training reference.

    python -m fraud.drift --dataset ieee --batch path/to/recent.parquet

Exits with status 1 when any monitored feature has PSI above the alert level, or when the
batch's mean fraud score moves too far from training, so a scheduler or CI job can page someone.
"""
from __future__ import annotations

import argparse
import sys

import numpy as np
import pandas as pd

from fraud.alerts import Scorer, model_dir
from fraud.profile import DRIFT_FEATURES, ULB_DRIFT_FEATURES, psi

PSI_ALERT = 0.25
SCORE_SHIFT_ALERT = 0.5  # relative change in mean fraud probability


def check(dataset: str, batch: pd.DataFrame) -> pd.DataFrame:
    ref = pd.read_parquet(model_dir(dataset) / "reference.parquet")
    feats = ULB_DRIFT_FEATURES if dataset == "ulb" else DRIFT_FEATURES
    rows = [{"check": f, "value": psi(ref[f], batch[f]), "limit": PSI_ALERT}
            for f in feats if f in ref and f in batch]
    scorer = Scorer.load(dataset)
    ref_score, new_score = scorer.score(ref).mean(), scorer.score(batch).mean()
    rows.append({"check": "mean_fraud_score_shift", "value": abs(new_score / ref_score - 1),
                 "limit": SCORE_SHIFT_ALERT})
    out = pd.DataFrame(rows)
    out["alert"] = out["value"] > out["limit"]
    return out


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(prog="fraud.drift")
    ap.add_argument("--dataset", choices=["ieee", "ulb"], default="ieee")
    ap.add_argument("--batch", required=True, help="parquet or csv of recent transactions")
    args = ap.parse_args(argv)
    batch = pd.read_parquet(args.batch) if args.batch.endswith(".parquet") else pd.read_csv(args.batch)
    res = check(args.dataset, batch)
    print(res.to_string(index=False, float_format=lambda v: f"{v:.4f}"))
    sys.exit(1 if res["alert"].any() else 0)


if __name__ == "__main__":
    main()
