"""ULB credit card fraud data (real European card transactions, PCA-anonymised).

Mapped onto the same column names as IEEE-CIS so the modelling, cost and
dashboard code treats both datasets the same way.

    python -m fraud.ulb download             # needs KAGGLE_USERNAME / KAGGLE_KEY
    python -m fraud.ulb download --csv PATH  # or a creditcard.csv you already have
    python -m fraud.ulb prepare
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

from fraud.config import Paths, data_paths, load_config
from fraud.data import time_split

CSV_FILE = "creditcard.csv"


def download(paths: Paths, dataset: str, csv_path: Path | None = None) -> Path:
    paths.ensure()
    target = paths.raw / CSV_FILE
    if target.exists():
        return target
    if csv_path is not None:
        shutil.copyfile(csv_path, target)
        return target
    subprocess.run(["kaggle", "datasets", "download", "-d", dataset, "-p", str(paths.raw)], check=True)
    with zipfile.ZipFile(paths.raw / f"{dataset.split('/')[-1]}.zip") as zf:
        with zf.open(CSV_FILE) as src, open(target, "wb") as dst:
            shutil.copyfileobj(src, dst)
    return target


def load(paths: Paths, reference_date: str) -> pd.DataFrame:
    raw = pd.read_csv(paths.raw / CSV_FILE)
    df = raw.rename(columns={"Class": "isFraud", "Amount": "TransactionAmt", "Time": "TransactionDT"})
    df.insert(0, "TransactionID", np.arange(len(df), dtype=np.int32))
    df = df.astype({c: np.float32 for c in df.columns if c.startswith("V")} | {"TransactionAmt": np.float32})
    df["isFraud"] = df["isFraud"].astype(np.int8)
    df["hour"] = (df["TransactionDT"] // 3600).astype(np.int16)
    df["day"] = (df["TransactionDT"] // 86_400).astype(np.int16)
    df["event_time"] = pd.Timestamp(reference_date) + pd.to_timedelta(df["TransactionDT"], unit="s")
    return df.sort_values("TransactionDT", kind="stable").reset_index(drop=True)


def prepare(cfg: dict) -> dict[str, pd.DataFrame]:
    paths = data_paths(cfg).ensure()
    u = cfg["ulb"]
    df = load(paths, u["reference_date"])
    s = u["split"]
    splits = time_split(df, s["train_end_hour"], s["valid_end_hour"], s.get("gap_hours", 0), column="hour")
    out = paths.processed / "ulb"
    out.mkdir(parents=True, exist_ok=True)
    for name, part in splits.items():
        part.to_parquet(out / f"{name}.parquet", index=False)
    return splits


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(prog="fraud.ulb")
    ap.add_argument("command", choices=["download", "prepare"])
    ap.add_argument("--config")
    ap.add_argument("--csv", type=Path, help="use an already downloaded creditcard.csv")
    args = ap.parse_args(argv)
    cfg = load_config(args.config)
    if args.command == "download":
        download(data_paths(cfg), cfg["ulb"]["kaggle_dataset"], args.csv)
    else:
        for name, part in prepare(cfg).items():
            print(f"{name:5s} rows={len(part):>7,d} frauds={int(part['isFraud'].sum()):>4d} "
                  f"fraud_rate={part['isFraud'].mean():.4f} hours=[{part['hour'].min()}, {part['hour'].max()}]")


if __name__ == "__main__":
    main()
