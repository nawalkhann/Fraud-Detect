from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = REPO_ROOT / "configs" / "default.yaml"


@dataclass(frozen=True)
class Paths:
    root: Path

    @property
    def raw(self) -> Path:
        return self.root / "raw"

    @property
    def interim(self) -> Path:
        return self.root / "interim"

    @property
    def processed(self) -> Path:
        return self.root / "processed"

    def ensure(self) -> "Paths":
        for p in (self.raw, self.interim, self.processed):
            p.mkdir(parents=True, exist_ok=True)
        return self


def load_config(path: str | Path | None = None) -> dict:
    with open(path or DEFAULT_CONFIG) as f:
        return yaml.safe_load(f)


def data_paths(cfg: dict) -> Paths:
    root = os.environ.get("FRAUD_DATA_DIR") or cfg["data"]["dir"]
    root = Path(root)
    if not root.is_absolute():
        root = REPO_ROOT / root
    return Paths(root)
