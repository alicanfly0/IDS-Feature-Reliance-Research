"""Compare the D-021 cap-200 sensitivity fits with the primary capped fits (r1 group D, seeds 0 and 5).

Sensitivity analysis only: the primary r1 statistics are unchanged. The group-D contrasts are
recomputed with the cap-200 values substituted for the two capped primary fits (error rate and
Monday FPR), then the 10-test Holm family is re-applied with every other p-value unchanged.

    python phase3_final_review/scripts/d021_compare.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from verify_r1 import holm, sign_flip, tint  # noqa: E402

V = ROOT / "phase3_final_review/evidence/verification"
SESOI = 0.001


def main() -> int:
    r1 = json.loads((V / "verify_r1.json").read_text(encoding="utf-8"))
    sens = json.loads((V / "d021_sensitivity.json").read_text(encoding="utf-8"))["runs"]
    st = json.loads((ROOT / "results/milestone3b/stats_r1.json").read_text(encoding="utf-8"))
    runs = r1["runs"]
    out = {"rule": "D-021 (approved 2026-11-11): AE cap 100, cap-200 sensitivity where the cap is hit",
           "applies_to": "r1 (approved with the r1 grid). D-024 (R4a) does not extend D-021; the 17 capped R4a fits are a declared limitation.",
           "fits": {}, "endpoints": {}}
    for s in (0, 5):
        p = runs[f"r1_D_s{s}"]
        c = sens[f"r1_D_s{s}_cap200"]
        out["fits"][f"r1_D_s{s}"] = {
            "primary": {"run": p["run"], "ae_best_epoch": p["ae"]["best_epoch"], "ae_epochs_run": p["ae"]["epochs_run"],
                        "errors": p["metrics"]["errors"], "fp": p["metrics"]["fp"], "fn": p["metrics"]["fn"],
                        "mcc": p["metrics"]["mcc"], "monday_fp": p["monday"]["fp"], "monday_fpr": p["monday"]["fpr"]},
            "cap200": {"run": c["run"], "ae_best_epoch": c["autoencoder"]["best_epoch"], "ae_epochs_run": c["autoencoder"]["epochs_run"],
                       "stopped": c["autoencoder"]["stopped"], "errors": c["test"]["errors"], "fp": c["test"]["fp"], "fn": c["test"]["fn"],
                       "mcc": c["test"]["mcc"], "monday_fp": c["monday"]["false_positives"], "monday_fpr": c["monday"]["fpr"],
                       "git_commit": c["git_commit"], "environment_fingerprint": c["environment_fingerprint"]}}
    seeds = list(range(10))
    pvals = {k: v["p"] for k, v in st["holm"].items()}
    for ep in ("error_rate", "fpr"):
        prim = st["groups"]["D_metadata_hypothesis"]["endpoints"][ep]
        dg = np.array(prim["delta_group"], float)
        dc = np.array(prim["delta_control"], float)
        dg_s = dg.copy()
        for s in (0, 5):
            full = runs[f"r1_full_s{s}"]
            new = sens[f"r1_D_s{s}_cap200"]["test"]["error_rate"] if ep == "error_rate" else sens[f"r1_D_s{s}_cap200"]["monday"]["fpr"]
            base = full["metrics"]["error_rate"] if ep == "error_rate" else full["monday"]["fpr"]
            dg_s[s] = new - base
        d_p, d_s = dg - dc, dg_s - dc
        sf = sign_flip(d_s)
        pv = dict(pvals)
        pv[f"D_metadata_hypothesis/{ep}"] = sf["p"]
        out["endpoints"][ep] = {"primary": {"mean_d": float(d_p.mean()), "p_exact": prim["sign_flip"]["p"],
                                            "p_holm": st["holm"][f"D_metadata_hypothesis/{ep}"]["p_holm"],
                                            "interval_99_5": prim["reading"]["interval_difference"], "reading": prim["reading"]["reading"]},
                                "cap200_sensitivity": {"d": d_s.tolist(), "mean_d": float(d_s.mean()), "p_exact": sf["p"],
                                                       "n_nonzero": sf["n_nonzero"], "_holm": None,
                                                       "interval_99_5": tint(d_s, 1 - 0.05 / 10), "interval_99_tost": tint(d_s, 1 - 0.1 / 10)}}
        out["endpoints"][ep]["_pv"] = pv
    # Holm with BOTH D endpoints replaced at once (the sensitivity family)
    pv = dict(pvals)
    for ep in ("error_rate", "fpr"):
        pv[f"D_metadata_hypothesis/{ep}"] = out["endpoints"][ep]["cap200_sensitivity"]["p_exact"]
        del out["endpoints"][ep]["_pv"]
    h = holm(pv)
    for ep in ("error_rate", "fpr"):
        cs = out["endpoints"][ep]["cap200_sensitivity"]
        k = f"D_metadata_hypothesis/{ep}"
        cs["p_holm"], cs["holm_reject"] = h[k]["p_holm"], h[k]["reject"]
        del cs["_holm"]
        lo, hi = cs["interval_99_5"]
        elo, ehi = cs["interval_99_tost"]
        cs["reading"] = ("practically relevant difference" if h[k]["reject"] and (lo > SESOI or hi < -SESOI) else
                         "difference (below SESOI or interval overlaps it)" if h[k]["reject"] else
                         "practical equivalence at the SESOI" if -SESOI < elo and ehi < SESOI else "inconclusive")
    out["other_holm_decisions_changed"] = sorted(k for k in h if not k.startswith("D_metadata") and h[k]["reject"] != st["holm"][k]["reject"])
    (V / "d021_comparison.json").write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(out, indent=1)[:4000])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
