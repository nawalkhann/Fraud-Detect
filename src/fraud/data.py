"""Download, join and out-of-time split of the IEEE-CIS labelled data.

    python -m fraud.data download            # needs KAGGLE_USERNAME / KAGGLE_KEY
    python -m fraud.data download --zip PATH # or use a zip you downloaded yourself
    python -m fraud.data prepare             # join + clean + split -> parquet
"""
from __future__ import annotations

import argparse
import subprocess
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

from fraud.config import Paths, data_paths, load_config

TRANSACTION_FILE = "train_transaction.csv"
IDENTITY_FILE = "train_identity.csv"
SECONDS_PER_DAY = 86_400


# --------------------------------------------------------------------------- download

def download(paths: Paths, competition: str, zip_path: Path | None = None) -> None:
    paths.ensure()
    if zip_path is None:
        zip_path = paths.raw / f"{competition}.zip"
        if not zip_path.exists():
            # The Kaggle CLI reads KAGGLE_USERNAME / KAGGLE_KEY from the env.
            # The account must have joined the competition to accept its rules.
            subprocess.run(
                ["kaggle", "competitions", "download", "-c", competition, "-p", str(paths.raw)],
                check=True,
            )
    with zipfile.ZipFile(zip_path) as zf:
        wanted = [n for n in zf.namelist() if Path(n).name in (TRANSACTION_FILE, IDENTITY_FILE)]
        missing = {TRANSACTION_FILE, IDENTITY_FILE} - {Path(n).name for n in wanted}
        if missing:
            raise FileNotFoundError(f"{zip_path} is missing {sorted(missing)}")
        for name in wanted:
            target = paths.raw / Path(name).name
            if not target.exists():
                with zf.open(name) as src, open(target, "wb") as dst:
                    while chunk := src.read(1 << 24):
                        dst.write(chunk)


# --------------------------------------------------------------------------- load + join

def _downcast(df: pd.DataFrame) -> pd.DataFrame:
    """Halve memory: float64 -> float32, ints to the smallest type, strings -> category."""
    for col in df.columns:
        s = df[col]
        if pd.api.types.is_float_dtype(s):
            df[col] = s.astype(np.float32)
        elif pd.api.types.is_integer_dtype(s):
            df[col] = pd.to_numeric(s, downcast="integer")
        elif s.dtype == object or pd.api.types.is_string_dtype(s):
            df[col] = s.astype("category")
    return df


def load_joined(paths: Paths) -> pd.DataFrame:
    tx = pd.read_csv(paths.raw / TRANSACTION_FILE)
    idn = pd.read_csv(paths.raw / IDENTITY_FILE)
    # Identity rows exist for only a subset of transactions; keep every transaction.
    df = tx.merge(idn, on="TransactionID", how="left", validate="one_to_one")
    df["has_identity"] = df["TransactionID"].isin(idn["TransactionID"]).astype(np.int8)
    return _downcast(df)


def add_time_columns(df: pd.DataFrame, reference_date: str) -> pd.DataFrame:
    df["day"] = (df["TransactionDT"] // SECONDS_PER_DAY).astype(np.int16)
    df["event_time"] = pd.Timestamp(reference_date) + pd.to_timedelta(df["TransactionDT"], unit="s")
    return df.sort_values("TransactionDT", kind="stable").reset_index(drop=True)


# --------------------------------------------------------------------------- split

def time_split(df: pd.DataFrame, train_end_day: int, valid_end_day: int, gap_days: int = 0,
               column: str = "day") -> dict[str, pd.DataFrame]:
    """Out-of-time split so the model is always scored on transactions after the ones it learned from.

    `column` is the time unit to cut on: "day" for IEEE-CIS, "hour" for the 2-day ULB set.
    """
    if not 0 < train_end_day + gap_days < valid_end_day:
        raise ValueError("need 0 < train_end_day + gap_days < valid_end_day")
    day = df[column]
    splits = {
        "train": df[day < train_end_day],
        "valid": df[(day >= train_end_day + gap_days) & (day < valid_end_day)],
        "test": df[day >= valid_end_day],
    }
    for name, part in splits.items():
        if part.empty:
            raise ValueError(f"{name} split is empty; check split days in the config")
    return {k: v.reset_index(drop=True) for k, v in splits.items()}


def prepare(cfg: dict) -> dict[str, pd.DataFrame]:
    paths = data_paths(cfg).ensure()
    df = add_time_columns(load_joined(paths), cfg["data"]["reference_date"])
    df.to_parquet(paths.interim / "train_joined.parquet", index=False)
    s = cfg["split"]
    splits = time_split(df, s["train_end_day"], s["valid_end_day"], s.get("gap_days", 0))
    for name, part in splits.items():
        part.to_parquet(paths.processed / f"{name}.parquet", index=False)
    return splits


def load_split(cfg: dict, name: str, columns: list[str] | None = None, dataset: str = "ieee") -> pd.DataFrame:
    base = data_paths(cfg).processed
    if dataset != "ieee":
        base = base / dataset
    return pd.read_parquet(base / f"{name}.parquet", columns=columns)


# --------------------------------------------------------------------------- CLI

def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(prog="fraud.data")
    ap.add_argument("command", choices=["download", "prepare"])
    ap.add_argument("--config")
    ap.add_argument("--zip", type=Path, help="use an already downloaded competition zip")
    args = ap.parse_args(argv)
    cfg = load_config(args.config)
    if args.command == "download":
        download(data_paths(cfg), cfg["data"]["kaggle_competition"], args.zip)
    else:
        for name, part in prepare(cfg).items():
            print(f"{name:5s} rows={len(part):>7,d} fraud_rate={part['isFraud'].mean():.4f} "
                  f"days=[{part['day'].min()}, {part['day'].max()}]")


if __name__ == "__main__":
    main()
