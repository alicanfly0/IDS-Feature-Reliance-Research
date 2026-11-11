"""Attribution pilots for the DCNN (D-009) and MES-DNN (D-010) adaptations. Descriptive only.

SHAP GradientExplainer (expected gradients) on each trained model; global ranking by mean |SHAP|.
Reported: per-seed rankings, the cross-seed rank stability (mean pairwise Spearman rho, top-5
overlap), and, for the DCNN, agreement with the LightGBM selector ranking. NO artifact-reliance
(ARR) classification: no artifact registry exists for UNSW-NB15 or NetFlow-v2 (D-012/D-013).

Samples (fixed, numpy default_rng(0)): background 500 training rows; explained 1,000 test rows,
half attack and half benign (DCNN: from the duplicate-filtered test population; MES-DNN: from
each network's test partition).

  python -m src.audit.attribution_pilot dcnn
  python -m src.audit.attribution_pilot mes
"""
from __future__ import annotations

import argparse
import itertools
import json

import numpy as np

from src.data.manifest import ROOT

N_BG, N_EXPLAIN = 500, 1000
OUT = ROOT / "results/attribution_pilot"


def _balanced(y: np.ndarray, rows: np.ndarray, n: int, rng) -> np.ndarray:
    pos, neg = rows[y[rows] == 1], rows[y[rows] == 0]
    k = min(n // 2, len(pos), len(neg))
    return np.sort(np.r_[rng.choice(pos, k, replace=False), rng.choice(neg, k, replace=False)])


def _shap(model, bg: np.ndarray, X: np.ndarray, seed: int) -> np.ndarray:
    import shap
    import torch
    torch.manual_seed(seed)
    model.eval()
    ex = shap.GradientExplainer(model_wrap(model), torch.tensor(bg, dtype=torch.float32))
    sv = ex.shap_values(torch.tensor(X, dtype=torch.float32), rseed=seed)
    sv = np.asarray(sv)
    return sv.reshape(len(X), -1) if sv.ndim > 2 else sv


def model_wrap(model):
    import torch

    class W(torch.nn.Module):            # GradientExplainer needs a 2-D output
        def __init__(self, m):
            super().__init__()
            self.m = m

        def forward(self, x):
            return self.m(x).unsqueeze(1)
    return W(model).eval()


def stability(rankings: dict, names: list) -> dict:
    from scipy.stats import spearmanr
    imps = {k: np.array([v[n] for n in names]) for k, v in rankings.items()}
    pairs = list(itertools.combinations(imps, 2))
    rho = [spearmanr(imps[a], imps[b]).statistic for a, b in pairs]
    top5 = {k: set(np.array(names)[np.argsort(-v)[:5]]) for k, v in imps.items()}
    ov = [len(top5[a] & top5[b]) / 5 for a, b in pairs]
    return {"pairs": len(pairs), "mean_spearman": float(np.mean(rho)), "min_spearman": float(np.min(rho)),
            "mean_top5_overlap": float(np.mean(ov)), "top5_by_run": {k: sorted(v) for k, v in top5.items()}}


def run_dcnn() -> dict:
    import torch

    from src.experiments import dcnn_fang as F
    from src.models.dcnn import DCNNSA
    sel = json.loads((F.OUT / "selection.json").read_text(encoding="utf-8"))
    d = F.prepare()
    pop = F.duplicate_population(d, sel["selected_index"])["model_visible"]["_mask"]
    Xtr, Xte = d["Xtr"][:, sel["selected_index"]], d["Xte"][:, sel["selected_index"]]
    rng = np.random.default_rng(0)
    bg = Xtr[np.sort(rng.choice(len(Xtr), N_BG, replace=False))]
    rows = _balanced(d["yte"], np.flatnonzero(pop), N_EXPLAIN, rng)
    names = sel["selected"]
    rankings = {}
    for f in sorted(F.OUT.glob("seed*/model.pt")):
        seed = int(f.parent.name[4:])
        m = DCNNSA(len(names))
        m.load_state_dict(torch.load(f, weights_only=True))
        sv = _shap(m, bg, Xte[rows], seed)
        rankings[f"seed{seed}"] = dict(zip(names, np.abs(sv).mean(axis=0).tolist()))
    lgbm = {r["feature"]: r["mean_abs_shap"] for r in sel["ranking"] if r["feature"] in names}
    from scipy.stats import spearmanr
    vs = {k: float(spearmanr([v[n] for n in names], [lgbm[n] for n in names]).statistic) for k, v in rankings.items()}
    return {"model": "DCNN+SA (D-009)", "explainer": "shap.GradientExplainer", "background_rows": N_BG,
            "explained_rows": int(len(rows)), "explained_population": "duplicate-filtered test (model-visible)",
            "rankings": rankings, "stability": stability(rankings, names), "spearman_vs_lightgbm_selector": vs,
            "arr": "not computed: no artifact registry for UNSW-NB15"}


def run_mes() -> dict:
    import torch

    from src.data import netflow
    from src.experiments import mes_dnn as M
    nets = M.load_networks()
    names = netflow.inputs()
    Base, Meta = M._models()
    rankings = {}
    for f in sorted(M.OUT.glob("*_seed*/ensemble.pt")):
        rec = json.loads((f.parent / "metrics.json").read_text(encoding="utf-8"))
        state = torch.load(f, weights_only=True)
        bases = [Base(np.zeros(len(names)), np.ones(len(names))) for _ in nets]
        meta = Meta(bases)
        meta.load_state_dict(state)
        for i, (n, d) in enumerate(nets.items()):
            part = M.partition(rec["mode"], rec["seed"], d["y"], d["gid"])
            rng = np.random.default_rng(0)
            base_rows = np.flatnonzero(part == 0)
            bg = d["X"][np.sort(rng.choice(base_rows, N_BG, replace=False))]
            rows = _balanced(d["y"], np.flatnonzero(part == 3), N_EXPLAIN, rng)
            sv = _shap(meta, bg, d["X"][rows], rec["seed"])
            rankings[f"{rec['mode']}_seed{rec['seed']}/{n}"] = dict(zip(names, np.abs(sv).mean(axis=0).tolist()))
    groups = {}
    for key in {k.split("_seed")[0] + "/" + k.split("/")[1] for k in rankings}:
        mode, net = key.split("/")
        sub = {k: v for k, v in rankings.items() if k.startswith(mode + "_seed") and k.endswith("/" + net)}
        groups[key] = stability(sub, names)
    return {"model": "MES-DNN ensemble (D-010)", "explainer": "shap.GradientExplainer (inputs in log1p space)",
            "background_rows": N_BG, "explained_rows_per_network": N_EXPLAIN, "rankings": rankings,
            "stability_by_mode_and_network": groups, "arr": "not computed: no artifact registry for NetFlow-v2"}


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("which", choices=("dcnn", "mes"))
    a = p.parse_args(argv)
    rec = run_dcnn() if a.which == "dcnn" else run_mes()
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f"{a.which}.json"
    path.write_text(json.dumps(rec, indent=2) + "\n", encoding="utf-8")
    st = rec.get("stability") or rec["stability_by_mode_and_network"]
    print(f"wrote {path.relative_to(ROOT)}")
    print(json.dumps(st, indent=1)[:2000])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
