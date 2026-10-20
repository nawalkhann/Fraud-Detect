import numpy as np
import pandas as pd
import pytest


def write_tiny_ulb(raw_dir, n=6000, seed=0):
    """Tiny file in the creditcard.csv layout with a planted signal, for plumbing tests only."""
    rng = np.random.default_rng(seed)
    y = (rng.random(n) < 0.03).astype(int)
    raw = pd.DataFrame({"Time": np.sort(rng.uniform(0, 172_792, n)).round()})
    for i in range(1, 29):
        raw[f"V{i}"] = rng.normal(size=n) + y * (1.5 if i in (4, 14) else 0)
    raw["Amount"] = rng.gamma(2, 40, n).round(2)
    raw["Class"] = y
    raw_dir.mkdir(parents=True, exist_ok=True)
    raw.to_csv(raw_dir / "creditcard.csv", index=False)


@pytest.fixture(scope="session")
def trained_ulb(tmp_path_factory):
    """Prepare + train once on the tiny ULB file; point data and model dirs at it."""
    from fraud.config import load_config
    from fraud.train import run
    from fraud.ulb import prepare

    root = tmp_path_factory.mktemp("ulb")
    write_tiny_ulb(root / "raw")
    mp = pytest.MonkeyPatch()
    mp.setenv("FRAUD_DATA_DIR", str(root))
    mp.setenv("FRAUD_MODEL_DIR", str(root / "models"))
    cfg = load_config()
    prepare(cfg)
    result = run(cfg, "ulb", out_root=root)
    yield root, cfg, result
    mp.undo()
