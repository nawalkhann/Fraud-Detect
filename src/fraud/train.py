"""Train, tune the threshold on valid, and report errors on train / valid / test.

    python -m fraud.train --dataset ieee
    python -m fraud.train --dataset ulb

Writes models/<dataset>/{lightgbm,logistic}.joblib, reports/model_report_<dataset>.md and
reports/cost_curve_<dataset>.csv.
"""
from __future__ import annotations

import argparse
import json
import subprocess
from dataclasses import asdict
from datetime import datetime, timezone

import joblib
import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (accuracy_score, average_precision_score, brier_score_loss, f1_score,
                             log_loss, precision_score, recall_score, roc_auc_score)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from fraud.config import REPO_ROOT, load_config
from fraud.cost import Costs, best_threshold, cost_curve, outcome
from fraud.data import load_split
from fraud.features import FeatureBuilder, label

SPLITS = ("train", "valid", "test")
LGB_PARAMS = {
    "ieee": dict(n_estimators=3000, learning_rate=0.03, num_leaves=256, max_depth=-1, min_child_samples=100,
                 subsample=0.8, subsample_freq=1, colsample_bytree=0.4, reg_lambda=1.0),
    "ulb": dict(n_estimators=2000, learning_rate=0.02, num_leaves=31, min_child_samples=50,
                subsample=0.8, subsample_freq=1, colsample_bytree=0.8, reg_lambda=1.0),
}


def fit_lightgbm(X_tr, y_tr, X_va, y_va, dataset: str, seed: int = 42) -> lgb.LGBMClassifier:
    # No class re-weighting: we want calibrated probabilities, because the threshold and the
    # alert queue both use p * dollars. Imbalance is handled by the cost-based threshold instead.
    model = lgb.LGBMClassifier(objective="binary", random_state=seed, n_jobs=-1, verbose=-1,
                               **LGB_PARAMS[dataset])
    model.fit(X_tr, y_tr, eval_set=[(X_va, y_va)], eval_metric="average_precision",
              callbacks=[lgb.early_stopping(200, first_metric_only=True, verbose=False)])
    return model


def fit_logistic(X_tr, y_tr) -> Pipeline:
    num = [c for c in X_tr.columns if pd.api.types.is_numeric_dtype(X_tr[c])]
    pre = ColumnTransformer([("num", Pipeline([("impute", SimpleImputer(strategy="median", add_indicator=True)),
                                                ("scale", StandardScaler())]), num)])
    model = Pipeline([("pre", pre), ("clf", LogisticRegression(C=0.1, max_iter=2000))])
    return model.fit(X_tr, y_tr)


def ranking_metrics(y, p) -> dict:
    return {"roc_auc": roc_auc_score(y, p), "pr_auc": average_precision_score(y, p),
            "brier": brier_score_loss(y, p), "log_loss": log_loss(y, np.clip(p, 1e-7, 1 - 1e-7))}


def threshold_metrics(y, p, amount, t, costs: Costs) -> dict:
    flag = p >= t
    return {"threshold": t, "accuracy": accuracy_score(y, flag),
            "precision": precision_score(y, flag, zero_division=0), "recall": recall_score(y, flag),
            "f1": f1_score(y, flag, zero_division=0), **outcome(y, flag, amount, costs)}


def pick_thresholds(y, p, amount, costs: Costs) -> dict[str, float]:
    """All policies are chosen on the validation split, then applied unchanged to test."""
    grid = np.unique(np.quantile(p, np.linspace(0, 1, 2001)))
    acc = [accuracy_score(y, p >= t) for t in grid]
    f1 = [f1_score(y, p >= t, zero_division=0) for t in grid]
    return {"default_0.5": 0.5, "max_accuracy": float(grid[int(np.argmax(acc))]),
            "max_f1": float(grid[int(np.argmax(f1))]), "min_cost": best_threshold(y, p, amount, costs)}


def _fmt(df: pd.DataFrame) -> str:
    return df.to_markdown(floatfmt=",.4f")


def write_metadata(out_dir, dataset, train_raw, rank, best, no_model, costs: Costs) -> None:
    """Minimal model registry entry: what was trained, on what, and how well it did."""
    try:
        sha = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=REPO_ROOT,
                             capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        sha = "unknown"
    meta = {
        "dataset": dataset,
        "trained_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "git_sha": sha,
        "train_rows": len(train_raw),
        "train_fraud_rate": float(train_raw["isFraud"].mean()),
        "costs": asdict(costs),
        "test": {"pr_auc": float(rank.loc[("lightgbm", "test"), "pr_auc"]),
                 "roc_auc": float(rank.loc[("lightgbm", "test"), "roc_auc"]),
                 "total_cost": float(best.total_cost), "no_model_cost": float(no_model),
                 "recall": float(best.recall), "precision": float(best.precision)},
    }
    (out_dir / "metadata.json").write_text(json.dumps(meta, indent=2))
    # reference sample of training traffic, used by fraud.drift to spot shifts in live data
    train_raw.sample(min(len(train_raw), 50_000), random_state=0).to_parquet(out_dir / "reference.parquet", index=False)


def run(cfg: dict, dataset: str, out_root=REPO_ROOT) -> dict:
    costs = Costs.from_config(cfg)
    raw = {s: load_split(cfg, s, dataset=dataset) for s in SPLITS}
    fb = FeatureBuilder(dataset).fit(raw["train"])
    X = {s: fb.transform(raw[s]) for s in SPLITS}
    y = {s: label(raw[s]) for s in SPLITS}
    amt = {s: raw[s]["TransactionAmt"].to_numpy(dtype=float) for s in SPLITS}

    models = {"lightgbm": fit_lightgbm(X["train"], y["train"], X["valid"], y["valid"], dataset),
              "logistic": fit_logistic(X["train"], y["train"])}
    proba = {m: {s: mdl.predict_proba(X[s])[:, 1] for s in SPLITS} for m, mdl in models.items()}

    out_dir = out_root / "models" / dataset
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, mdl in models.items():
        joblib.dump({"model": mdl, "features": fb}, out_dir / f"{name}.joblib")

    rank_rows, thr_rows, chosen = [], [], {}
    for m in models:
        for s in SPLITS:
            rank_rows.append({"model": m, "split": s, **ranking_metrics(y[s], proba[m][s])})
        chosen[m] = pick_thresholds(y["valid"], proba[m]["valid"], amt["valid"], costs)
        for policy, t in chosen[m].items():
            thr_rows.append({"model": m, "policy": policy,
                             **threshold_metrics(y["test"], proba[m]["test"], amt["test"], t, costs)})
    rank = pd.DataFrame(rank_rows).set_index(["model", "split"])
    thr = pd.DataFrame(thr_rows).set_index(["model", "policy"])

    no_model = outcome(y["test"], np.zeros_like(y["test"]), amt["test"], costs)["total_cost"]
    best = thr.loc[("lightgbm", "min_cost")]
    curve = cost_curve(y["test"], proba["lightgbm"]["test"], amt["test"], costs)
    (out_root / "reports").mkdir(parents=True, exist_ok=True)
    curve.to_csv(out_root / "reports" / f"cost_curve_{dataset}.csv", index=False)

    importance = (pd.Series(models["lightgbm"].booster_.feature_importance("gain"), index=fb.columns_)
                  .sort_values(ascending=False).head(15).rename("gain").to_frame())

    lines = [
        f"# Model report: {dataset}", "",
        f"Costs: missed fraud = amount x {costs.fn_amount_multiplier} + ${costs.chargeback_fee:.0f} chargeback; "
        f"every alert = ${costs.review_cost:.0f} review; false alarm friction = ${costs.friction_cost:.0f}.",
        f"Test set: {len(y['test']):,} transactions, {int(y['test'].sum()):,} frauds "
        f"(${amt['test'][y['test'] == 1].sum():,.0f}). Thresholds are chosen on valid and applied unchanged to test.", "",
        "## Headline (LightGBM, cost-optimal threshold, test split)",
        f"- Total cost **${best.total_cost:,.0f}** vs **${no_model:,.0f}** with no model "
        f"({1 - best.total_cost / no_model:.1%} saved).",
        f"- Catches {best.recall:.1%} of frauds ({best.tp:,} of {best.tp + best.fn:,}), "
        f"{best.fraud_dollars_caught / max(best.fraud_dollars_caught + best.fraud_dollars_missed, 1):.1%} of fraud dollars, "
        f"with {best.alerts:,} alerts ({best.precision:.1%} of alerts are fraud).",
        f"- Best LightGBM iteration: {models['lightgbm'].best_iteration_}.", "",
        "## Ranking quality and overfitting check (train vs valid vs test)",
        "PR-AUC is the main metric under heavy imbalance. A large train-test gap means overfitting.", "",
        _fmt(rank), "",
        "## Error at each threshold policy (test split)",
        "`max_accuracy` shows why accuracy misleads: it barely flags anything.", "",
        _fmt(thr[["threshold", "accuracy", "precision", "recall", "f1", "alerts", "tp", "fp", "fn",
                  "fraud_dollars_missed", "total_cost"]]), "",
        "## Top features (LightGBM gain)", "", _fmt(importance), "",
    ]
    report = out_root / "reports" / f"model_report_{dataset}.md"
    report.write_text("\n".join(lines))
    (out_dir / "thresholds.json").write_text(json.dumps(chosen, indent=2))
    write_metadata(out_dir, dataset, raw["train"], rank, best, no_model, costs)
    return {"report": str(report), "thresholds": chosen, "test_min_cost": best.to_dict(), "no_model_cost": no_model}


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(prog="fraud.train")
    ap.add_argument("--dataset", choices=["ieee", "ulb"], default="ieee")
    ap.add_argument("--config")
    args = ap.parse_args(argv)
    res = run(load_config(args.config), args.dataset)
    print(f"wrote {res['report']}")


if __name__ == "__main__":
    main()
