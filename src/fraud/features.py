"""Feature engineering, fitted on the train split only so valid/test never leak into it."""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

ID_COLUMNS = ["TransactionID", "isFraud", "TransactionDT", "event_time", "day", "hour"]
FREQ_COLUMNS = ["card1", "card2", "card3", "card5", "addr1", "addr2", "P_emaildomain", "R_emaildomain", "uid"]
UID_AGG_COLUMNS = ["TransactionAmt", "dist1", "C13", "D15"]


def _base_features(df: pd.DataFrame, dataset: str) -> pd.DataFrame:
    out = df.copy()
    if "day" not in out:  # raw API payloads only carry TransactionDT
        out["day"] = out["TransactionDT"] // 86_400
    amt = out["TransactionAmt"].astype(float)
    out["amt_log"] = np.log1p(amt)
    out["amt_cents"] = (amt - np.floor(amt)).round(2)
    out["hour_of_day"] = (out["TransactionDT"] // 3600 % 24).astype(np.int8)
    if dataset == "ieee":
        out["weekday"] = (out["TransactionDT"] // 86_400 % 7).astype(np.int8)
        # D1 is "days since card first seen"; day - D1 is a stable card start date. Together with
        # card1 and addr1 it approximates a customer id, the strongest signal in this data.
        if {"D1", "card1", "addr1"} <= set(out.columns):
            out["D1n"] = out["day"] - out["D1"]
            out["uid"] = (out["card1"].astype(str) + "_" + out["addr1"].astype(str) + "_"
                          + out["D1n"].astype(str)).astype("category")
    return out


@dataclass
class FeatureBuilder:
    """Fit on train, then transform any split. Unseen values get frequency 0 / NaN aggregates."""
    dataset: str = "ieee"
    freq_: dict[str, pd.Series] = field(default_factory=dict)
    uid_aggs_: pd.DataFrame | None = None
    categories_: dict[str, pd.Index] = field(default_factory=dict)
    columns_: list[str] = field(default_factory=list)

    def fit(self, train: pd.DataFrame) -> "FeatureBuilder":
        df = _base_features(train, self.dataset)
        for col in FREQ_COLUMNS:
            if col in df:
                self.freq_[col] = df[col].astype("string").value_counts(dropna=False)
        if "uid" in df:
            cols = [c for c in UID_AGG_COLUMNS if c in df]
            self.uid_aggs_ = df.groupby("uid", observed=True)[cols].agg(["mean", "std"])
            self.uid_aggs_.columns = [f"uid_{c}_{s}" for c, s in self.uid_aggs_.columns]
        for col in df.columns:
            if isinstance(df[col].dtype, pd.CategoricalDtype) and col != "uid":
                self.categories_[col] = df[col].cat.categories
        self.columns_ = list(self._transform(df).columns)
        return self

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        # reindex so payloads with missing optional columns (e.g. no identity data) still score
        return self._transform(_base_features(df, self.dataset)).reindex(columns=self.columns_)

    def _transform(self, df: pd.DataFrame) -> pd.DataFrame:
        for col, counts in self.freq_.items():
            if col not in df:
                df[col] = pd.NA
            df[f"{col}_freq"] = df[col].astype("string").map(counts).fillna(0).astype(np.float32)
        if self.uid_aggs_ is not None and "uid" in df:
            df = df.join(self.uid_aggs_, on="uid")
            df["amt_vs_uid_mean"] = df["TransactionAmt"] / df["uid_TransactionAmt_mean"]
        for col, cats in self.categories_.items():
            values = df[col].astype(object) if col in df else [None] * len(df)
            df[col] = pd.Categorical(values, categories=cats)
        return df.drop(columns=[c for c in ID_COLUMNS + ["uid", "D1n"] if c in df])


def label(df: pd.DataFrame) -> np.ndarray:
    return df["isFraud"].to_numpy(dtype=np.int8)
