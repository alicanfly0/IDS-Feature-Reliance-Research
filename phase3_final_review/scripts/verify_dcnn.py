"""Independent read-only verification of the DCNN + self-attention adaptation (D-009), 5 seeds.

Rebuilds the official UNSW-NB15 Normal/DoS test labels and both duplicate-filtered masks from the
manifest-verified CSVs (torch-free code path), checks them against the frozen selection.json hashes,
recomputes every metric from each seed's saved test_proba.npy with an independent implementation and
compares with the committed metrics.json / summary.json. The LightGBM+SHAP feature selection itself is
not re-run (shap imports numba, which this laptop's application-control policy blocks); its ranking is
checked for internal consistency instead (cumulative share at K = 22, 95 % rule count).

    python phase3_final_review/scripts/verify_dcnn.py
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
from src.experiments.dcnn_fang import duplicate_population, prepare  # noqa: E402  (torch-free functions)

D = ROOT / "results/dcnn_fang"
OUT = ROOT / "phase3_final_review/evidence/verification"


def m(y, p):
    pred = (p >= 0.5).astype(int)
    tp = int(((pred == 1) & (y == 1)).sum()); tn = int(((pred == 0) & (y == 0)).sum())
    fp = int(((pred == 1) & (y == 0)).sum()); fn = int(((pred == 0) & (y == 1)).sum())
    den = math.sqrt(float(tp + fp) * (tp + fn) * (tn + fp) * (tn + fn))
    prec, rec = tp / (tp + fp), tp / (tp + fn)
    return {"n": len(y), "n_dos": int(y.sum()), "tp": tp, "tn": tn, "fp": fp, "fn": fn, "errors": fp + fn,
            "accuracy": (tp + tn) / len(y), "dos_precision": prec, "dos_recall": rec, "dos_f1": 2 * prec * rec / (prec + rec),
            "fpr": fp / (fp + tn), "fnr": fn / (fn + tp), "mcc": (tp * tn - fp * fn) / den, "roc_auc": float(roc_auc_score(y, p)),
            "prob_finite": bool(np.isfinite(p).all())}


def main() -> int:
    problems = []
    sel = json.loads((D / "selection.json").read_text(encoding="utf-8"))
    d = prepare()
    sha = lambda a: hashlib.sha256(np.ascontiguousarray(a).tobytes()).hexdigest()
    rows = {"train": len(d["ytr"]), "test": len(d["yte"]), "train_dos": int(d["ytr"].sum()), "test_dos": int(d["yte"].sum())}
    if rows != sel["rows"]:
        problems.append(f"row counts {rows} differ from selection.json {sel['rows']}")
    if sha(d["Xtr"]) != sel["train_matrix_sha256"]:
        problems.append("training matrix hash differs from selection.json")
    imp = np.array([r["mean_abs_shap"] for r in sel["ranking"]])
    cum = np.cumsum(imp) / imp.sum()
    rank_check = {"cumulative_share_at_22": float(cum[21]), "rule95_count": int(np.searchsorted(cum, 0.95) + 1),
                  "cumulative_share_at_30": float(cum[29]), "n_ranked": len(imp),
                  "top22_equals_selected": [r["feature"] for r in sel["ranking"][:22]] == sel["selected"]}
    if abs(rank_check["cumulative_share_at_22"] - sel["cumulative_share_at_k"]) > 1e-12 or rank_check["rule95_count"] != sel["rule95_count"] \
            or not rank_check["top22_equals_selected"]:
        problems.append("selection ranking internally inconsistent")
    pops = duplicate_population(d, sel["selected_index"])
    masks = {"official": np.ones(len(d["yte"]), bool)}
    for k, v in pops.items():
        if v["kept_mask_sha256"] != sel["test_populations"][k]["kept_mask_sha256"]:
            problems.append(f"{k}: duplicate mask differs from the frozen record")
        masks[f"dedup_{k}"] = v["_mask"]
    seeds = {}
    for s in range(5):
        p = np.load(D / f"seed{s}" / "test_proba.npy")
        rec = json.loads((D / f"seed{s}" / "metrics.json").read_text(encoding="utf-8"))
        if hashlib.sha256(p.tobytes()).hexdigest() != rec["test_proba_sha256"]:
            problems.append(f"seed{s}: test_proba.npy hash differs from metrics.json")
        seeds[s] = {"training": {k: rec["training"][k] for k in ("epochs_run", "best_epoch", "best_val_loss", "train_seconds", "fit_rows", "val_rows")},
                    "early_stopped": rec["training"]["epochs_run"] < rec["identity"]["hyperparameters"]["epochs"],
                    "environment_fingerprint": rec["environment_fingerprint"], "code_commit": rec["identity"]["code_commit"]}
        for pop, mk in masks.items():
            mm = m(d["yte"][mk], p[mk])
            saved = rec["test"][pop]
            ok = all(mm[k] == saved[k] for k in ("n", "tp", "tn", "fp", "fn")) and abs(mm["mcc"] - saved["mcc"]) < 1e-12 \
                and abs(mm["roc_auc"] - saved["roc_auc"]) < 1e-12
            if not ok:
                problems.append(f"seed{s}/{pop}: recomputed metrics differ from metrics.json")
            seeds[s][pop] = {**mm, "matches_metrics_json": ok}
    # cross-population row-level facts
    fn_official = [seeds[s]["official"]["fn"] for s in range(5)]
    fn_dedup = [seeds[s]["dedup_model_visible"]["fn"] for s in range(5)]
    excluded_dos = (~masks["dedup_model_visible"]) & (d["yte"] == 1)
    det_excl = [int((np.load(D / f"seed{s}" / "test_proba.npy")[excluded_dos] >= 0.5).sum()) for s in range(5)]
    facts = {"fn_official": fn_official, "fn_dedup_model_visible": fn_dedup, "excluded_dos_rows": int(excluded_dos.sum()),
             "excluded_dos_detected_per_seed": det_excl,
             "fp_share_of_errors_official": [seeds[s]["official"]["fp"] / seeds[s]["official"]["errors"] for s in range(5)]}
    res = {"experiment": "DCNN+SA (D-009) on UNSW-NB15 Normal vs DoS", "rows": rows, "selection_check": rank_check,
           "populations": {k: {kk: vv for kk, vv in v.items() if kk != "_mask"} for k, v in pops.items()},
           "problems": problems, "facts": facts, "seeds": seeds}
    (OUT / "verify_dcnn.json").write_text(json.dumps(res, indent=1, default=float) + "\n", encoding="utf-8")
    print(f"DCNN: 5 seeds x 3 populations; problems: {len(problems)}")
    for p in problems:
        print("  PROBLEM", p)
    print(json.dumps(facts))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
