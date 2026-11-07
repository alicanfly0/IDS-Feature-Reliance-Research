"""XGBoost classifier on latent codes (Nezhadsistani et al. 2026, §3.4 and §4.2.2).

The paper grid-searched the Table 5 ranges but does not report the selected values or
the number of trees. We use one fixed configuration inside those ranges, chosen before
seeing any data, with the number of trees set by early stopping on the VALIDATION
partition only (decision log D-017). The test partition is never used for fitting.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import xgboost as xgb

PAPER_RANGES = {  # Table 5: (low, high)
    "learning_rate": (0.01, 0.30), "max_depth": (6, 6), "reg_alpha": (0, 10),
    "reg_lambda": (0, 100), "subsample": (0.5, 1.0), "colsample_bytree": (0.6, 1.0),
}


def check_within_paper_ranges(params: dict) -> list[str]:
    return [f"{k}={params[k]} outside paper range {lo}-{hi}"
            for k, (lo, hi) in PAPER_RANGES.items() if k in params and not lo <= params[k] <= hi]


def cuda_build() -> bool:
    return bool(xgb.build_info().get("USE_CUDA"))


def fit(z_train, y_train, z_val, y_val, params: dict, device: str, seed: int) -> xgb.XGBClassifier:
    if device == "cuda" and not cuda_build():
        raise RuntimeError("GPU requested but this XGBoost build has no CUDA support")
    model = xgb.XGBClassifier(
        objective="binary:logistic", eval_metric="logloss", tree_method="hist", device=device,
        random_state=seed, n_jobs=-1, **params,
    )
    model.fit(z_train, y_train, eval_set=[(z_val, y_val)], verbose=False)
    return model


def predict_positive(model: xgb.XGBClassifier, z: np.ndarray) -> np.ndarray:
    """Probability of class 1 (the positive class, DDoS), using the early-stopped tree count."""
    return model.predict_proba(z)[:, 1]


def save(model: xgb.XGBClassifier, path: Path) -> None:
    tmp = Path(path).with_name(Path(path).name + ".tmp.json")
    model.save_model(tmp)
    tmp.replace(path)


def load(path: Path) -> xgb.XGBClassifier:
    model = xgb.XGBClassifier()
    model.load_model(path)
    return model
