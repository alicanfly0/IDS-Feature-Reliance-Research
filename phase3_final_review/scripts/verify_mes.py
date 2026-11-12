"""Independent read-only verification of the two-network MES-DNN adaptation (D-010), 10 ensemble fits.

Reloads both networks with the project's torch-free loaders, checks the input matrices against
networks.json, regenerates every partition (random and dup_aware, seeds 0-4) and its hash, rebuilds
the test labels and novel-vector masks, and recomputes all metrics from each fit's saved
test_proba.npz (ensemble and both base models) with an independent implementation, comparing them with
metrics.json. Trains nothing.

    python phase3_final_review/scripts/verify_mes.py
"""
from __future__ import annotations

import hashlib
import json
import math
import sys
from pathlib import Path

import numpy as np
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from src.experiments.mes_dnn import load_networks, partition, partition_record  # noqa: E402  (torch-free)

D = ROOT / "results/mes_dnn"
OUT = ROOT / "phase3_final_review/evidence/verification"


def m(y, p):
    pred = (p >= 0.5).astype(int)
    tp = int(((pred == 1) & (y == 1)).sum()); tn = int(((pred == 0) & (y == 0)).sum())
    fp = int(((pred == 1) & (y == 0)).sum()); fn = int(((pred == 0) & (y == 1)).sum())
    den = math.sqrt(float(tp + fp) * (tp + fn) * (tn + fp) * (tn + fn))
    out = {"n": len(y), "n_attack": int(y.sum()), "tp": tp, "tn": tn, "fp": fp, "fn": fn,
           "accuracy": (tp + tn) / len(y) if len(y) else float("nan"),
           "precision": tp / (tp + fp) if tp + fp else float("nan"), "recall": tp / (tp + fn) if tp + fn else float("nan"),
           "f1": 2 * tp / (2 * tp + fp + fn) if tp + fp + fn else float("nan"), "fpr": fp / (fp + tn) if fp + tn else float("nan"),
           "mcc": (tp * tn - fp * fn) / den if den else 0.0, "prob_finite": bool(np.isfinite(p).all())}
    if 0 < y.sum() < len(y):
        out["roc_auc"] = float(roc_auc_score(y, p))
    return out


def main() -> int:
    problems = []
    nets = load_networks()
    nrec = json.loads((D / "networks.json").read_text(encoding="utf-8"))
    sha = lambda a: hashlib.sha256(np.ascontiguousarray(a).tobytes()).hexdigest()
    net_check = {}
    for n, d in nets.items():
        net_check[n] = {"rows": len(d["y"]), "attack": int(d["y"].sum()), "unique_vectors": int(d["gid"].max() + 1),
                        "matrix_matches_networks_json": sha(d["X"]) == nrec[n]["matrix_sha256"],
                        "inputs": int(d["X"].shape[1]), "log1p_inputs_finite": bool(np.isfinite(d["X"]).all()),
                        "max_log1p_input": float(d["X"].max()), "raw_values_beyond_float32_max": d["beyond_float32"]}
        if not net_check[n]["matrix_matches_networks_json"] or not net_check[n]["log1p_inputs_finite"]:
            problems.append(f"{n}: input matrix differs from networks.json or is non-finite")
    fits = {}
    for mode in ("random", "dup_aware"):
        for seed in range(5):
            key = f"{mode}_seed{seed}"
            rec = json.loads((D / key / "metrics.json").read_text(encoding="utf-8"))
            z = np.load(D / key / "test_proba.npz")
            fit = {"partitions": {}, "test": {}, "environment_fingerprint": rec["environment_fingerprint"]}
            for n, d in nets.items():
                part = partition(mode, seed, d["y"], d["gid"])
                pr = partition_record(part, d["y"], d["gid"])
                if pr != rec["partitions"][n]:
                    problems.append(f"{key}/{n}: regenerated partition differs from metrics.json")
                fit["partitions"][n] = pr
                t = part == 3
                seen = np.zeros(d["gid"].max() + 1, dtype=bool)
                seen[d["gid"][part != 3]] = True
                novel = ~seen[d["gid"][t]]
                yt = d["y"][t]
                for model in ("ensemble", "base_N1_unsw", "base_N2_ton"):
                    p = z[f"{n}__{model}"]
                    for pop, mask in (("all", np.ones(len(yt), bool)), ("novel_vectors", novel)):
                        mm = m(yt[mask], p[mask])
                        saved = rec["test"][f"{n}/{model}"][pop]
                        ok = all(mm[k] == saved[k] for k in ("n", "tp", "tn", "fp", "fn")) and (
                            math.isnan(saved["mcc"]) or abs(mm["mcc"] - saved["mcc"]) < 1e-9)
                        if "roc_auc" in mm:
                            ok = ok and abs(mm["roc_auc"] - saved["roc_auc"]) < 1e-9
                        if not ok or not mm["prob_finite"]:
                            problems.append(f"{key}/{n}/{model}/{pop}: recomputed metrics differ or non-finite")
                        fit["test"][f"{n}/{model}/{pop}"] = {**mm, "matches_metrics_json": ok}
            fit["training"] = {"base_N1_final_val_loss": rec["base_N1_unsw"]["history"][-1].get("val_loss"),
                               "base_N2_final_val_loss": rec["base_N2_ton"]["history"][-1].get("val_loss"),
                               "meta_final_loss": rec["meta"]["history"][-1]["loss"], "meta_rows": rec["meta"]["rows"],
                               "epochs": len(rec["meta"]["history"])}
            fits[key] = fit
    res = {"experiment": "MES-DNN two-network adaptation (D-010)", "networks": net_check, "problems": problems, "fits": fits}
    (OUT / "verify_mes.json").write_text(json.dumps(res, indent=1, default=float) + "\n", encoding="utf-8")
    print(f"MES-DNN: {len(fits)} fits; problems: {len(problems)}")
    for p in problems:
        print("  PROBLEM", p)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
