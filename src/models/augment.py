"""Latent-space Gaussian augmentation (Nezhadsistani et al. 2026, §3.3, Eq. 4). Training data only.

Paper: for a minority-class *attack* sample with latent z = E(x), x~ = D(z + eps),
eps ~ N(0, sigma^2), keeping only x~ "with acceptably low reconstruction error";
XGBoost is then trained on latent codes of real plus synthetic samples (§3.4).
The paper does not give sigma, the number of synthetic samples or the acceptance
threshold; the choices below are labelled adaptations (decision log D-017):
  - sigma is a fraction of the per-dimension std of the class's training latents;
  - enough samples are generated to balance the classes;
  - a sample is kept if its reconstruction error is within the given quantile of the
    real training samples' errors of that class;
  - the synthetic sample's latent code is E(x~), i.e. it goes through the same encoder.
"""
from __future__ import annotations

import numpy as np
import torch

from src.models.autoencoder import AutoEncoder


def plan(y_train: np.ndarray, positive: int = 1) -> dict:
    """Paper rule: augment only when the attack (positive) class is the minority."""
    n_pos, n_neg = int((y_train == positive).sum()), int((y_train != positive).sum())
    if n_pos >= n_neg:
        return {"applicable": False, "n_new": 0,
                "reason": f"attack class is not the minority in training data ({n_pos} attack vs {n_neg} benign)"}
    return {"applicable": True, "n_new": n_neg - n_pos, "reason": "attack class is the minority; balance to 1:1"}


@torch.no_grad()
def _errors(model: AutoEncoder, x: torch.Tensor) -> torch.Tensor:
    return torch.mean((model(x) - x) ** 2, dim=1)


@torch.no_grad()
def generate(model: AutoEncoder, x_class: np.ndarray, n_new: int, sigma_scale: float, keep_quantile: float,
             device: str, seed: int) -> tuple[np.ndarray, dict]:
    """Synthetic latent codes for one class. `x_class` must be preprocessed TRAINING rows of that class."""
    model.eval().to(device)
    gen = torch.Generator(device="cpu").manual_seed(seed)
    x = torch.from_numpy(np.ascontiguousarray(x_class, dtype=np.float32)).to(device)
    z = model.encoder(x)
    threshold = torch.quantile(_errors(model, x).cpu(), keep_quantile).item()
    sigma = (z.std(dim=0) * sigma_scale).cpu()
    base = torch.randint(len(z), (n_new,), generator=gen)
    noise = torch.randn((n_new, z.shape[1]), generator=gen) * sigma
    x_new = model.decoder(z[base.to(device)] + noise.to(device))
    keep = (_errors(model, x_new) <= threshold).cpu().numpy()
    z_new = model.encoder(x_new).cpu().numpy()[keep]
    return z_new, {"requested": n_new, "kept": int(keep.sum()), "error_threshold": threshold,
                   "sigma_scale": sigma_scale, "keep_quantile": keep_quantile}
