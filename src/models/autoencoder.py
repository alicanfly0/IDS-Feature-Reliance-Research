"""Fully connected autoencoder (Nezhadsistani et al. 2026, §3.2 and §4.2.1) with resumable training.

Paper: encoder 120 -> 80 -> 40 latent, symmetric decoder, ReLU "in all layers", Adam
lr 0.001, batch 256, 50-100 epochs with early stopping, reconstruction squared error.
Here the input width is whatever the train-fitted preprocessing produces (D-003); the
hidden/latent widths, optimizer, learning rate and batch size follow the paper. Unstated
details (output activation, early-stopping patience, epoch cap) are config values,
recorded as adaptations in the decision log (D-017).
"""
from __future__ import annotations

import os
import random
import time
from pathlib import Path

import numpy as np
import torch
from torch import nn

ACTIVATIONS = {"relu": nn.ReLU, "linear": nn.Identity, "sigmoid": nn.Sigmoid}


class AutoEncoder(nn.Module):
    def __init__(self, input_dim: int, hidden: tuple[int, ...] = (80,), latent: int = 40,
                 activation: str = "relu", latent_activation: str = "relu", output_activation: str = "linear"):
        super().__init__()
        act = ACTIVATIONS[activation]
        widths = [input_dim, *hidden]
        enc: list[nn.Module] = []
        for a, b in zip(widths[:-1], widths[1:]):
            enc += [nn.Linear(a, b), act()]
        enc += [nn.Linear(widths[-1], latent), ACTIVATIONS[latent_activation]()]
        dec_widths = [latent, *reversed(hidden)]
        dec: list[nn.Module] = []
        for a, b in zip(dec_widths[:-1], dec_widths[1:]):
            dec += [nn.Linear(a, b), act()]
        dec += [nn.Linear(dec_widths[-1], input_dim), ACTIVATIONS[output_activation]()]
        self.encoder, self.decoder = nn.Sequential(*enc), nn.Sequential(*dec)

    def forward(self, x):
        return self.decoder(self.encoder(x))


def build(input_dim: int, cfg: dict) -> AutoEncoder:
    return AutoEncoder(input_dim, tuple(cfg["hidden"]), cfg["latent"], cfg["activation"],
                       cfg["latent_activation"], cfg["output_activation"])


def _atomic_save(obj, path: Path) -> None:
    tmp = path.with_name(path.name + ".tmp")
    torch.save(obj, tmp)
    os.replace(tmp, path)


def _rng_state() -> dict:
    state = {"python": random.getstate(), "numpy": np.random.get_state(), "torch": torch.get_rng_state()}
    if torch.cuda.is_available():
        state["cuda"] = torch.cuda.get_rng_state_all()
    return state


def _set_rng_state(state: dict) -> None:
    random.setstate(state["python"])
    np.random.set_state(state["numpy"])
    torch.set_rng_state(state["torch"])
    if "cuda" in state and torch.cuda.is_available():
        torch.cuda.set_rng_state_all(state["cuda"])


@torch.no_grad()
def reconstruction_mse(model: AutoEncoder, x: torch.Tensor, batch: int = 8192) -> float:
    model.eval()
    total = 0.0
    for i in range(0, len(x), batch):
        xb = x[i:i + batch]
        total += torch.sum((model(xb) - xb) ** 2).item()
    return total / x.numel()


def train(model: AutoEncoder, x_train: np.ndarray, x_val: np.ndarray, cfg: dict, device: str, seed: int,
          ckpt_dir: Path, log=print, max_batches_per_epoch: int | None = None) -> dict:
    """Train with validation early stopping; resumes from `ckpt_dir/ae_last.pt` if present.

    Batch order for epoch e comes from a generator seeded with (seed, e), so a resumed
    run sees exactly the batches an uninterrupted run would have seen.
    """
    ckpt_dir = Path(ckpt_dir)
    ckpt_dir.mkdir(parents=True, exist_ok=True)
    last, best_path = ckpt_dir / "ae_last.pt", ckpt_dir / "ae_best.pt"
    xt = torch.from_numpy(np.ascontiguousarray(x_train, dtype=np.float32)).to(device)
    xv = torch.from_numpy(np.ascontiguousarray(x_val, dtype=np.float32)).to(device)
    model.to(device)
    opt = torch.optim.Adam(model.parameters(), lr=cfg["lr"])
    state = {"epoch": 0, "best_val": float("inf"), "best_epoch": -1, "bad_epochs": 0, "history": [], "stopped": None}
    if last.is_file():
        ckpt = torch.load(last, map_location=device, weights_only=False)
        model.load_state_dict(ckpt["model"])
        opt.load_state_dict(ckpt["optimizer"])
        state = ckpt["state"]
        _set_rng_state(ckpt["rng"])
        log(f"resumed autoencoder from epoch {state['epoch']} (best val {state['best_val']:.6g} at epoch {state['best_epoch']})")
    if state["stopped"]:
        log(f"autoencoder already finished ({state['stopped']})")
    loss_fn = nn.MSELoss()
    n, bs = len(xt), cfg["batch_size"]
    while not state["stopped"]:
        epoch = state["epoch"]
        gen = torch.Generator().manual_seed(seed * 100_003 + epoch)
        order = torch.randperm(n, generator=gen).to(device)
        n_batches = (n + bs - 1) // bs
        if max_batches_per_epoch:
            n_batches = min(n_batches, max_batches_per_epoch)
        model.train()
        t0, running = time.perf_counter(), 0.0
        for b in range(n_batches):
            xb = xt[order[b * bs:(b + 1) * bs]]
            opt.zero_grad(set_to_none=True)
            loss = loss_fn(model(xb), xb)
            loss.backward()
            opt.step()
            running += loss.item()
        val = reconstruction_mse(model, xv)
        seconds = time.perf_counter() - t0
        state["history"].append({"epoch": epoch, "train_loss": running / n_batches, "val_mse": val, "seconds": round(seconds, 3)})
        improved = val < state["best_val"] - cfg["min_delta"]
        if improved:
            state.update(best_val=val, best_epoch=epoch, bad_epochs=0)
            _atomic_save(model.state_dict(), best_path)
        else:
            state["bad_epochs"] += 1
        state["epoch"] = epoch + 1
        if state["bad_epochs"] >= cfg["patience"]:
            state["stopped"] = f"early stopping at epoch {epoch} (patience {cfg['patience']})"
        elif state["epoch"] >= cfg["max_epochs"]:
            state["stopped"] = f"reached max_epochs {cfg['max_epochs']}"
        _atomic_save({"model": model.state_dict(), "optimizer": opt.state_dict(), "state": state,
                      "rng": _rng_state(), "seed": seed, "config": cfg}, last)
        log(f"epoch {epoch:3d}  train {running / n_batches:.6g}  val {val:.6g}  {seconds:.1f}s"
            + ("  *" if improved else ""))
    model.load_state_dict(torch.load(best_path, map_location=device, weights_only=True))
    return state


@torch.no_grad()
def encode(model: AutoEncoder, x: np.ndarray, device: str, batch: int = 8192) -> np.ndarray:
    model.eval().to(device)
    out = []
    for i in range(0, len(x), batch):
        xb = torch.from_numpy(np.ascontiguousarray(x[i:i + batch], dtype=np.float32)).to(device)
        out.append(model.encoder(xb).cpu().numpy())
    return np.concatenate(out) if out else np.zeros((0, model.encoder[-2].out_features), np.float32)
