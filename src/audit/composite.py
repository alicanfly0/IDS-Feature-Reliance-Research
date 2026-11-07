"""The trained AE-XGBoost baseline as ONE function of the original (raw) CICFlowMeter features.

    raw features (78) -> saved train-only preprocessing -> saved AE encoder (40 latent) -> saved XGBoost

Built only from a completed run's saved artifacts (preprocessor.json, checkpoints/ae_best.pt,
xgb_model.json, effective_config.json); nothing is refitted or retrained. Explaining this
function attributes the actual model to original features (decision log D-002), instead of
relabelling latent dimensions.

precision="float32" reproduces the saved run outputs. Its CPU matrix products round differently
with batch size (latent differences ~1e-6), which can move a row across an XGBoost split, so the
same row can get a different margin depending on which rows it is batched with. SHAP evaluates
the function on arbitrary batches, so explanations use precision="float64": the same trained
weights evaluated in double precision, which is batch-invariant (decision log D-019).
"""
from __future__ import annotations

import copy
import json
from pathlib import Path

import numpy as np
import torch

from src.models import autoencoder as ae
from src.models import xgb as xgbm


class CompositeModel:
    def __init__(self, run_dir: Path, raw_columns: list[str], batch: int = 65536, precision: str = "float32"):
        run_dir = Path(run_dir)
        if not (run_dir / "DONE").is_file():
            raise RuntimeError(f"{run_dir.name} is not a completed run")
        pre = json.loads((run_dir / "preprocessor.json").read_text(encoding="utf-8"))
        cfg = json.loads((run_dir / "effective_config.json").read_text(encoding="utf-8"))
        if pre["categories"]:
            raise NotImplementedError("composite model supports numeric-only inputs (D-008 scope)")
        if pre["clip_to_train_range"]:
            raise NotImplementedError("clipping not reproduced here")
        expected_raw = set(pre["numeric_cols"]) | set(pre["dropped_constant_on_train"])
        if set(raw_columns) != expected_raw:
            raise ValueError("raw columns do not match the run's preprocessing (numeric + constant-on-train)")
        self.run_dir, self.raw_columns, self.batch = run_dir, list(raw_columns), batch
        self.model_columns = list(pre["numeric_cols"])
        self.index = np.array([self.raw_columns.index(c) for c in self.model_columns])
        self.median = np.array([pre["medians"][c] for c in self.model_columns], dtype=np.float64)
        self.lo = np.array([pre["mins"][c] for c in self.model_columns], dtype=np.float64)
        span = np.array([pre["maxs"][c] for c in self.model_columns], dtype=np.float64) - self.lo
        self.span = np.where(span != 0, span, 1.0)
        self.ae = ae.build(len(self.model_columns), cfg["ae"])
        self.ae.load_state_dict(torch.load(run_dir / "checkpoints" / "ae_best.pt", map_location="cpu", weights_only=True))
        self.ae.eval()
        if precision not in ("float32", "float64"):
            raise ValueError("precision must be float32 or float64")
        self.precision = precision
        self.encoder = self.ae.encoder if precision == "float32" else copy.deepcopy(self.ae.encoder).double()
        self.xgb = xgbm.load(run_dir / "xgb_model.json")
        self.provenance = {"run": run_dir.name, "precision": precision, **json.loads((run_dir / "identity.json").read_text(encoding="utf-8"))}

    def transform(self, raw: np.ndarray) -> np.ndarray:
        """Same mapping as TrainOnlyPreprocessor.transform with the saved train statistics."""
        x = np.asarray(raw, dtype=np.float64)[:, self.index]
        x = np.where(np.isfinite(x), x, np.nan)
        x = np.where(np.isnan(x), self.median, x)
        return ((x - self.lo) / self.span).astype(np.float32)

    @torch.no_grad()
    def latent(self, raw: np.ndarray) -> np.ndarray:
        x = self.transform(raw)
        if self.precision == "float64":
            x = x.astype(np.float64)
        out = [self.encoder(torch.from_numpy(x[i:i + self.batch])).numpy().astype(np.float32)
               for i in range(0, len(x), self.batch)]
        return np.concatenate(out) if out else np.zeros((0, self.ae.encoder[-2].out_features), np.float32)

    def margin(self, raw: np.ndarray) -> np.ndarray:
        """Log-odds of DDoS (XGBoost margin, early-stopped tree count)."""
        return self.xgb.predict(self.latent(raw), output_margin=True).astype(np.float64)

    def proba(self, raw: np.ndarray) -> np.ndarray:
        return 1.0 / (1.0 + np.exp(-self.margin(raw)))
