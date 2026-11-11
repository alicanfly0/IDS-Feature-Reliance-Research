"""Two-network MES-DNN adaptation (Wardana et al. 2026, D-010). An adaptation, not a reproduction.

Networks: N1 = NF-UNSW-NB15-v2 (all flows); N2 = the fixed NF-ToN-IoT-v2 subsample (src/data/netflow.py).
Per network the rows are split, as the paper's proportions, into four DISJOINT partitions:
base training 63 % (70 % x 90 %), meta sample 7 % (70 % x 10 %), validation 3 % (30 % x 10 %) and
final test 27 % (30 % x 90 %). Two split modes, each with seeds 0-4 (10 ensemble fits):
  random     stratified random rows (the paper's scheme);
  dup_aware  rows grouped by their exact 39-input vector; each group goes to ONE partition
             (stratified by the group's majority label), so no test vector was seen in training.
Model (paper Tables 6-7, Algorithm 1): per network a base DNN 39-9-7-5-3-1 (ReLU, sigmoid output)
trained on its own base partition; both bases frozen; meta-model Dense(10, ReLU) -> Dense(1, sigmoid)
on the concatenated base outputs, trained on the union of both networks' meta samples
(scenario 1: all networks integrated). Adam, binary cross-entropy, batch 1000, 10 epochs.
Adaptation choices (paper silent): inputs pass through a fixed elementwise log1p (no fitted parameters),
because NF-ToN-IoT-v2 holds *_SECOND_BYTES values up to ~1e257 that overflow float32; each base then
standardises with mean/std from its own base partition; Keras defaults (Glorot init, Adam lr 1e-3,
eps 1e-7); validation is monitored only.

  python -m src.experiments.mes_dnn run [--modes random dup_aware] [--seeds 0 1 2 3 4]
  python -m src.experiments.mes_dnn summary
"""
from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd

from src.data import netflow
from src.data.manifest import ROOT

OUT = ROOT / "results/mes_dnn"
PARTS = ("base", "meta", "val", "test")
FRACTIONS = {"base": 0.63, "meta": 0.07, "val": 0.03, "test": 0.27}
HP = dict(hidden=[9, 7, 5, 3], meta_hidden=10, lr=1e-3, batch_size=1000, epochs=10, threshold=0.5)
PARTITIONER = {"random": "stratified rows", "dup_aware": "v2 balanced largest-first group assignment"}
NETWORKS = {"N1_unsw": netflow.load_unsw, "N2_ton": netflow.load_ton}


def _sha(a) -> str:
    return hashlib.sha256(np.ascontiguousarray(a).tobytes()).hexdigest()


# ------------------------------------------------------------------ partitions
def group_ids(X: pd.DataFrame) -> np.ndarray:
    """Exact identity of the 39-input vector (no hashing)."""
    return X.groupby(list(X.columns), sort=False).ngroup().to_numpy()


def partition(mode: str, seed: int, y: np.ndarray, gid: np.ndarray) -> np.ndarray:
    """0 base, 1 meta, 2 val, 3 test for every row."""
    rng = np.random.default_rng(seed)
    edges = np.cumsum([FRACTIONS[p] for p in PARTS])
    out = np.empty(len(y), dtype=np.int8)
    if mode == "random":
        for cls in (0, 1):
            rows = rng.permutation(np.flatnonzero(y == cls))
            cut = np.round(edges * len(rows)).astype(int)
            for k, (a, b) in enumerate(zip(np.r_[0, cut[:-1]], cut)):
                out[rows[a:b]] = k
        return out
    if mode != "dup_aware":
        raise ValueError(mode)
    g = pd.DataFrame({"g": gid, "y": y}).groupby("g")["y"].agg(["size", "mean"])
    g_label = (g["mean"] >= 0.5).astype(int).to_numpy()
    sizes = g["size"].to_numpy()
    frac = np.array([FRACTIONS[p] for p in PARTS])
    assign = np.empty(len(g), dtype=np.int8)
    for cls in (0, 1):
        # v2 (balanced): groups in descending size (random order among equal sizes), each to the
        # partition with the largest remaining row deficit for this class. v1 placed groups by a
        # random cumulative order, which let giant groups (NF-ToN-IoT-v2: one vector x 422,766
        # rows) fill a partition with one class; superseded, see results/mes_dnn/superseded/.
        gs = rng.permutation(np.flatnonzero(g_label == cls))
        gs = gs[np.argsort(-sizes[gs], kind="stable")]
        deficit = frac * sizes[gs].sum()
        for k in gs:
            j = int(np.argmax(deficit))
            assign[k] = j
            deficit[j] -= sizes[k]
    return assign[gid]


def partition_record(part: np.ndarray, y: np.ndarray, gid: np.ndarray) -> dict:
    seen = np.zeros(gid.max() + 1, dtype=bool)
    seen[gid[part != 3]] = True
    test = part == 3
    novel = test & ~seen[gid]
    return {"rows": {p: int((part == k).sum()) for k, p in enumerate(PARTS)},
            "attack_rows": {p: int(((part == k) & (y == 1)).sum()) for k, p in enumerate(PARTS)},
            "test_rows_with_vector_seen_in_base_meta_val": int((test & seen[gid]).sum()),
            "test_rows_novel": int(novel.sum()), "partition_sha256": _sha(part)}


# ------------------------------------------------------------------ models
def _models():
    import torch
    from torch import nn

    class Base(nn.Module):
        def __init__(self, mean, std):
            super().__init__()
            self.register_buffer("mean", torch.tensor(mean, dtype=torch.float32))
            self.register_buffer("std", torch.tensor(std, dtype=torch.float32))
            dims = [len(mean)] + HP["hidden"]
            layers = []
            for a, b in zip(dims[:-1], dims[1:]):
                layers += [nn.Linear(a, b), nn.ReLU()]
            self.body = nn.Sequential(*layers, nn.Linear(dims[-1], 1))
            for m in self.modules():
                if isinstance(m, nn.Linear):
                    nn.init.xavier_uniform_(m.weight)
                    nn.init.zeros_(m.bias)

        def logits(self, x):
            return self.body((x - self.mean) / self.std).squeeze(1)

        def forward(self, x):
            return torch.sigmoid(self.logits(x))

    class Meta(nn.Module):
        def __init__(self, bases):
            super().__init__()
            self.bases = nn.ModuleList(bases)
            for p in self.bases.parameters():
                p.requires_grad_(False)                       # Algorithm 1: base layers frozen
            self.head = nn.Sequential(nn.Linear(len(bases), HP["meta_hidden"]), nn.ReLU(),
                                      nn.Linear(HP["meta_hidden"], 1))
            for m in self.head.modules():
                if isinstance(m, nn.Linear):
                    nn.init.xavier_uniform_(m.weight)
                    nn.init.zeros_(m.bias)

        def logits(self, x):
            z = torch.stack([b(x) for b in self.bases], dim=1)   # concatenated base sigmoid outputs
            return self.head(z).squeeze(1)

        def forward(self, x):
            return torch.sigmoid(self.logits(x))

    return Base, Meta


def _fit(model, X, y, seed, Xv=None, yv=None, log=print, tag=""):
    import torch
    params = [p for p in model.parameters() if p.requires_grad]
    opt = torch.optim.Adam(params, lr=HP["lr"], betas=(0.9, 0.999), eps=1e-7)
    bce = torch.nn.functional.binary_cross_entropy_with_logits
    Xt, yt = torch.tensor(X, dtype=torch.float32), torch.tensor(y, dtype=torch.float32)
    gen = torch.Generator().manual_seed(seed)
    hist = []
    for epoch in range(HP["epochs"]):
        model.train()
        if hasattr(model, "bases"):
            model.bases.eval()
        perm = torch.randperm(len(yt), generator=gen)
        tot, nb = 0.0, 0
        for s in range(0, len(perm), HP["batch_size"]):
            b = perm[s:s + HP["batch_size"]]
            loss = bce(model.logits(Xt[b]), yt[b])
            opt.zero_grad(set_to_none=True)
            loss.backward()
            opt.step()
            tot += float(loss); nb += 1
        h = {"epoch": epoch + 1, "loss": tot / nb}
        if Xv is not None:
            model.eval()
            with torch.no_grad():
                h["val_loss"] = float(bce(_logits(model, Xv), torch.tensor(yv, dtype=torch.float32)))
        hist.append(h)
        log(f"    {tag} epoch {epoch + 1:2d} " + " ".join(f"{k} {v:.5f}" for k, v in h.items() if k != "epoch"))
    model.eval()
    return hist


def _logits(model, X):
    import torch
    with torch.no_grad():
        t = torch.tensor(X, dtype=torch.float32)
        return torch.cat([model.logits(t[s:s + 65536]) for s in range(0, len(t), 65536)])


def predict(model, X) -> np.ndarray:
    import torch
    return torch.sigmoid(_logits(model, X)).numpy().astype(np.float64)


def metrics(y: np.ndarray, p: np.ndarray, thr: float = HP["threshold"]) -> dict:
    from sklearn.metrics import average_precision_score, matthews_corrcoef, roc_auc_score
    pred = (p >= thr).astype(int)
    tp = int(((pred == 1) & (y == 1)).sum()); tn = int(((pred == 0) & (y == 0)).sum())
    fp = int(((pred == 1) & (y == 0)).sum()); fn = int(((pred == 0) & (y == 1)).sum())
    div = lambda a, b: float(a / b) if b else float("nan")
    out = {"n": int(len(y)), "n_attack": int(y.sum()), "tp": tp, "tn": tn, "fp": fp, "fn": fn,
           "accuracy": div(tp + tn, len(y)), "precision": div(tp, tp + fp), "recall": div(tp, tp + fn),
           "f1": div(2 * tp, 2 * tp + fp + fn), "fpr": div(fp, fp + tn), "specificity": div(tn, tn + fp),
           "mcc": float(matthews_corrcoef(y, pred)) if len(y) else float("nan")}
    out["balanced_accuracy"] = (out["recall"] + out["specificity"]) / 2
    if 0 < y.sum() < len(y):
        out["roc_auc"] = float(roc_auc_score(y, p))
        out["pr_auc"] = float(average_precision_score(y, p))
    return out


# ------------------------------------------------------------------ experiment
def load_networks() -> dict:
    cols = netflow.inputs()
    nets = {}
    for name, fn in NETWORKS.items():
        df = fn()
        X = df[cols]
        raw = X.to_numpy(np.float64)
        if (raw < 0).any() or not np.isfinite(raw).all():
            raise RuntimeError(f"{name}: negative or non-finite inputs; log1p transform not valid")
        big = {c: int(n) for c, n in zip(cols, (raw > np.finfo(np.float32).max).sum(axis=0)) if n}
        nets[name] = {"X": np.log1p(raw), "y": df["Label"].to_numpy(np.int64), "gid": group_ids(X),
                      "beyond_float32": big}
        del df
    return nets


def network_record(nets: dict) -> dict:
    rec = {}
    for name, d in nets.items():
        g = pd.DataFrame({"g": d["gid"], "y": d["y"]}).groupby("g")["y"].nunique()
        rec[name] = {"rows": int(len(d["y"])), "attack": int(d["y"].sum()), "unique_vectors": int(d["gid"].max() + 1),
                     "duplicate_rows": int(len(d["y"]) - d["gid"].max() - 1),
                     "label_conflict_vectors": int((g > 1).sum()), "matrix_sha256": _sha(d["X"]),
                     "input_transform": "log1p", "raw_values_beyond_float32_max": d["beyond_float32"]}
    keys = {n: set(pd.util.hash_pandas_object(pd.DataFrame(d["X"]), index=False).to_numpy().tolist())
            for n, d in nets.items()}
    a, b = list(keys)
    rec["shared_vectors_between_networks_hash64"] = len(keys[a] & keys[b])
    return rec


def run_one(nets: dict, mode: str, seed: int, log=print) -> dict:
    import torch

    from src.env import set_seeds
    Base, Meta = _models()
    parts = {n: partition(mode, seed, d["y"], d["gid"]) for n, d in nets.items()}
    bases, info = [], {"partitions": {n: partition_record(parts[n], d["y"], d["gid"]) for n, d in nets.items()}}
    for i, (n, d) in enumerate(nets.items()):
        set_seeds(seed * 100 + i)
        base_rows = parts[n] == 0
        mean = d["X"][base_rows].mean(axis=0)
        std = d["X"][base_rows].std(axis=0)
        std = np.where(std == 0, 1.0, std)
        model = Base(mean, std)
        t0 = time.time()
        hist = _fit(model, d["X"][base_rows], d["y"][base_rows], seed * 100 + i,
                    d["X"][parts[n] == 2], d["y"][parts[n] == 2], log, f"{mode} s{seed} base {n}")
        info[f"base_{n}"] = {"history": hist, "seconds": round(time.time() - t0, 1)}
        bases.append(model)
    set_seeds(seed * 100 + 99)
    meta = Meta(bases)
    Xm = np.vstack([d["X"][parts[n] == 1] for n, d in nets.items()])
    ym = np.concatenate([d["y"][parts[n] == 1] for n, d in nets.items()])
    info["meta"] = {"history": _fit(meta, Xm, ym, seed * 100 + 99, log=log, tag=f"{mode} s{seed} meta"),
                    "rows": int(len(ym))}
    test, proba = {}, {}
    for n, d in nets.items():
        t = parts[n] == 3
        seen = np.zeros(d["gid"].max() + 1, dtype=bool)
        seen[d["gid"][parts[n] != 3]] = True
        novel = ~seen[d["gid"][t]]
        yt = d["y"][t]
        for name, model in [("ensemble", meta)] + [(f"base_{m}", b) for m, b in zip(nets, bases)]:
            p = predict(model, d["X"][t])
            proba[f"{n}/{name}"] = p
            test[f"{n}/{name}"] = {"all": metrics(yt, p), "novel_vectors": metrics(yt[novel], p[novel])}
    info["test"] = test
    return info, {"meta": meta, "proba": proba}


def cmd_run(modes: list, seeds: list) -> int:
    import torch

    from src.env import fingerprint, snapshot
    torch.use_deterministic_algorithms(True)
    t0 = time.time()
    nets = load_networks()
    print(f"loaded networks in {time.time() - t0:.0f}s")
    OUT.mkdir(parents=True, exist_ok=True)
    rec_path = OUT / "networks.json"
    nrec = network_record(nets)
    if rec_path.is_file():
        old = json.loads(rec_path.read_text(encoding="utf-8"))
        if {n: v["matrix_sha256"] for n, v in old.items() if isinstance(v, dict)} != \
                {n: v["matrix_sha256"] for n, v in nrec.items() if isinstance(v, dict)}:
            raise RuntimeError("network data differ from the recorded networks.json")
    rec_path.write_text(json.dumps(nrec, indent=2) + "\n", encoding="utf-8")
    for mode in modes:
        for seed in seeds:
            rdir = OUT / f"{mode}_seed{seed}"
            if (rdir / "metrics.json").is_file():
                print(f"{mode} seed {seed}: already complete, skipped")
                continue
            snap = snapshot(seed)
            snap["device"] = "cpu"
            info, art = run_one(nets, mode, seed)
            rdir.mkdir(parents=True, exist_ok=True)
            torch.save(art["meta"].state_dict(), rdir / "ensemble.pt")
            np.savez_compressed(rdir / "test_proba.npz", **{k.replace("/", "__"): v for k, v in art["proba"].items()})
            out = {"mode": mode, "seed": seed, "partitioner": PARTITIONER[mode], "hyperparameters": HP, "fractions": FRACTIONS, **info,
                   "environment": snap, "environment_fingerprint": fingerprint(snap)}
            (rdir / "metrics.json").write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
            line = " | ".join(f"{k.split('/')[0]} MCC {v['all']['mcc']:.4f} novel {v['novel_vectors']['mcc']:.4f}"
                              for k, v in info["test"].items() if k.endswith("/ensemble"))
            print(f"{mode} seed {seed}: {line}")
    return 0


def cmd_summary() -> int:
    rows = []
    for f in sorted(OUT.glob("*_seed*/metrics.json")):
        r = json.loads(f.read_text(encoding="utf-8"))
        for key, pops in r["test"].items():
            net, model = key.split("/")
            for pop, m in pops.items():
                rows.append({"mode": r["mode"], "seed": r["seed"], "network": net, "model": model, "population": pop,
                             **{k: m.get(k) for k in ("n", "fp", "fn", "accuracy", "precision", "recall", "f1",
                                                      "fpr", "mcc", "roc_auc")}})
    if not rows:
        print("no completed fits")
        return 1
    df = pd.DataFrame(rows)
    keys = ["mode", "network", "model", "population"]
    agg = df.drop(columns="seed").groupby(keys).agg(["mean", "std"])
    out = {"per_fit": rows, "aggregate": [
        {**dict(zip(keys, idx)), **{f"{c}_{s}": float(agg.loc[idx, (c, s)]) for c, s in agg.columns}} for idx in agg.index]}
    (OUT / "summary.json").write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    with pd.option_context("display.width", 220, "display.max_rows", 100):
        print(df[df.model == "ensemble"].groupby(["mode", "network", "population"])[["n", "accuracy", "f1", "mcc", "fpr"]].mean())
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("command", choices=("run", "summary"))
    p.add_argument("--modes", nargs="+", default=["random", "dup_aware"])
    p.add_argument("--seeds", type=int, nargs="+", default=[0, 1, 2, 3, 4])
    a = p.parse_args(argv)
    return cmd_run(a.modes, a.seeds) if a.command == "run" else cmd_summary()


if __name__ == "__main__":
    raise SystemExit(main())
