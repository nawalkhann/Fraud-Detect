"""Data report for the prepared IEEE-CIS splits.

    python -m fraud.profile [--dataset ieee|ulb]   # writes reports/data_report_<dataset>.md
"""
from __future__ import annotations

import argparse

import numpy as np
import pandas as pd

from fraud.config import REPO_ROOT, load_config
from fraud.data import load_split

CATEGORICALS = ["ProductCD", "card4", "card6", "DeviceType", "P_emaildomain"]
DRIFT_FEATURES = ["TransactionAmt", "card1", "addr1", "dist1", "C1", "C13", "D1", "D15"]
COLUMN_GROUPS = {"C": "C", "D": "D", "M": "M", "V": "V", "id_": "id_"}


def psi(expected: pd.Series, actual: pd.Series, bins: int = 10) -> float:
    """Population stability index with quantile bins from `expected`; NaN gets its own bin."""
    edges = np.unique(np.nanquantile(expected.astype(float), np.linspace(0, 1, bins + 1)))
    if len(edges) < 3:
        return float("nan")
    edges[0], edges[-1] = -np.inf, np.inf

    def dist(s: pd.Series) -> np.ndarray:
        s = s.astype(float)
        counts = np.histogram(s.dropna(), bins=edges)[0]
        counts = np.append(counts, s.isna().sum())
        return np.clip(counts / max(len(s), 1), 1e-6, None)

    e, a = dist(expected), dist(actual)
    return float(np.sum((a - e) * np.log(a / e)))


def _md(df: pd.DataFrame, floatfmt: str = ".4f") -> str:
    # whole-number columns (counts, days, dollars) print without decimals
    whole = {c: "Int64" for c in df.columns
             if pd.api.types.is_numeric_dtype(df[c]) and df[c].notna().all() and (df[c] % 1 == 0).all()}
    return df.astype(whole).to_markdown(floatfmt=floatfmt)


TITLES = {"ieee": "IEEE-CIS (Vesta e-commerce)", "ulb": "ULB (European card transactions)"}
ULB_DRIFT_FEATURES = ["TransactionAmt", "V1", "V3", "V4", "V10", "V12", "V14", "V17"]


def build_report(splits: dict[str, pd.DataFrame], dataset: str = "ieee") -> str:
    df = pd.concat([p.assign(split=n) for n, p in splits.items()], ignore_index=True)
    y = df["isFraud"]
    unit = "hour" if dataset == "ulb" else "day"
    out: list[str] = [f"# {TITLES[dataset]} data report", ""]

    fraud_amt = df.loc[y == 1, "TransactionAmt"].sum()
    out += [
        "## Overview",
        f"- Transactions: {len(df):,} ({df.shape[1]} columns after the identity join)",
        f"- Period: {df['event_time'].min():%Y-%m-%d} to {df['event_time'].max():%Y-%m-%d} "
        f"(assumed reference date; TransactionDT is relative)",
        f"- Fraud: {int(y.sum()):,} transactions, rate {y.mean():.2%}, "
        f"${fraud_amt:,.0f} of ${df['TransactionAmt'].sum():,.0f} volume ({fraud_amt / df['TransactionAmt'].sum():.2%})",
    ]
    if "has_identity" in df:
        out.append(f"- With identity record: {df['has_identity'].mean():.1%} of transactions "
                   f"(fraud rate {y[df['has_identity'] == 1].mean():.2%} vs {y[df['has_identity'] == 0].mean():.2%} without)")
    out.append("")

    split_tbl = df.groupby("split", sort=False).agg(
        rows=("isFraud", "size"), frauds=("isFraud", "sum"), fraud_rate=("isFraud", "mean"),
        **{f"first_{unit}": (unit, "min"), f"last_{unit}": (unit, "max")},
        fraud_dollars=("TransactionAmt", lambda s: round(float(s[df.loc[s.index, "isFraud"] == 1].sum()))),
    )
    out += ["## Out-of-time splits", _md(split_tbl), ""]

    period = df[unit] // 6 * 6 if dataset == "ulb" else df["event_time"].dt.to_period("M")
    label = "6-hour block" if dataset == "ulb" else "month"
    over_time = df.groupby(period.rename(label)).agg(
        rows=("isFraud", "size"), frauds=("isFraud", "sum"), fraud_rate=("isFraud", "mean"))
    out += [f"## Fraud rate by {label}", _md(over_time), ""]

    amt = df.groupby("isFraud")["TransactionAmt"].describe(percentiles=[0.5, 0.95, 0.99])
    amt.index = amt.index.map({0: "legit", 1: "fraud"})
    out += ["## Transaction amount by class", _md(amt, ".2f"), ""]

    miss_rows = []
    for name, prefix in COLUMN_GROUPS.items():
        cols = [c for c in df.columns if c.startswith(prefix) and c[len(prefix):].isdigit()]
        if cols:
            m = df[cols].isna().mean()
            miss_rows.append({"group": name, "columns": len(cols), "mean_missing": m.mean(),
                              "cols_over_90pct_missing": int((m > 0.9).sum())})
    out += ["## Missing values by column group", _md(pd.DataFrame(miss_rows).set_index("group")), ""]

    out.append("## Fraud rate by category (top 8 by volume)")
    for col in [c for c in CATEGORICALS if c in df.columns]:
        g = df.groupby(df[col].astype("string").fillna("<missing>"))["isFraud"].agg(["size", "mean"])
        g = g.sort_values("size", ascending=False).head(8).rename(columns={"size": "rows", "mean": "fraud_rate"})
        out += [f"### {col}", _md(g), ""]

    drift = pd.DataFrame(
        [{"feature": f, "psi_train_vs_valid": psi(splits["train"][f], splits["valid"][f]),
          "psi_train_vs_test": psi(splits["train"][f], splits["test"][f])}
         for f in (ULB_DRIFT_FEATURES if dataset == "ulb" else DRIFT_FEATURES) if f in df.columns]).set_index("feature")
    out += ["## Drift (population stability index)",
            "PSI under 0.1 is stable, 0.1 to 0.25 is a moderate shift, over 0.25 is a large shift.",
            "", _md(drift), ""]
    return "\n".join(out)


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(prog="fraud.profile")
    ap.add_argument("--config")
    ap.add_argument("--dataset", choices=sorted(TITLES), default="ieee")
    args = ap.parse_args(argv)
    cfg = load_config(args.config)
    splits = {n: load_split(cfg, n, dataset=args.dataset) for n in ("train", "valid", "test")}
    path = REPO_ROOT / "reports" / f"data_report_{args.dataset}.md"
    path.parent.mkdir(exist_ok=True)
    path.write_text(build_report(splits, args.dataset))
    print(f"wrote {path}")


if __name__ == "__main__":
    main()
