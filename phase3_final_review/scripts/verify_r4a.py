"""Independent read-only verification of R4a (D-024): R4a-ii (70 fits) and R4a-i (110 r1 models).

Inputs (all committed or packaged records; the 70 R4a run folders stay on the Colab VM / Drive):
  results/r4a/aggregate_r4a.json, stats_r4a.json, r4a_i_scores.json
  results/protocol/r4a/eval_population_r4a_v1.json
  phase3_final_review/evidence/verification/r4a_predictions_colab_check.json
     (read-only recomputation from the 70 predictions_test.csv.gz on the Colab VM, 2026-11-12;
      JSON SHA-256 130da7c0ef0f617cf263115caa97bbd15eb8da15fa0e88f5cbdfa79be8321d4b)
Re-derives confusion-based metrics, the paired contrasts, exact sign-flip p, Holm (family 3) and the
Bonferroni-consistent intervals (1 - 0.05/3 difference, 1 - 2*0.05/3 TOST) with an independent
implementation and compares every value with the committed records.

    python phase3_final_review/scripts/verify_r4a.py
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from src.experiments.matrix_3b import load_matrix  # noqa: E402
from verify_r1 import holm, sign_flip, tint  # noqa: E402

OUT = ROOT / "phase3_final_review/evidence/verification"


def derived(fp, fn, npos, nneg):
    tp, tn = npos - fn, nneg - fp
    n = npos + nneg
    prec = tp / (tp + fp) if tp + fp else float("nan")
    rec = tp / npos
    den = math.sqrt(float(tp + fp) * (tp + fn) * (tn + fp) * (tn + fn))
    return {"tp": tp, "tn": tn, "fp": fp, "fn": fn, "n": n, "errors": fp + fn, "error_rate": (fp + fn) / n,
            "accuracy": (tp + tn) / n, "precision": prec, "recall": rec,
            "f1": 2 * prec * rec / (prec + rec) if prec + rec else 0.0, "fpr": fp / nneg, "fnr": fn / npos,
            "balanced_error_rate": (fp / nneg + fn / npos) / 2, "mcc": (tp * tn - fp * fn) / den if den else 0.0}


def main() -> int:
    problems = []
    matrix = load_matrix(design="r4a")
    pop = json.loads((ROOT / matrix["population_file"]).read_text(encoding="utf-8"))["family_common_model_visible"]
    agg = json.loads((ROOT / "results/r4a/aggregate_r4a.json").read_text(encoding="utf-8"))
    st = json.loads((ROOT / "results/r4a/stats_r4a.json").read_text(encoding="utf-8"))
    chk = json.loads((OUT / "r4a_predictions_colab_check.json").read_text(encoding="utf-8"))
    npos, nneg = pop["test_kept_ddos"], pop["test_kept_benign"]
    if agg["population_test_sha256"] != pop["test_kept_source_rows_sha256"]:
        problems.append("aggregate population hash differs from the frozen population record")
    runs = {}
    by_dir = {k: v for k, v in chk.items()}
    for e in matrix["entries"]:
        a = agg["runs"].get(e["id"])
        if a is None:
            problems.append(f"{e['id']}: missing from aggregate"); continue
        c = by_dir.get(a["run"])
        d = derived(a["fp"], a["fn"], npos, nneg)
        rec = {"id": e["id"], "kind": e["kind"], "group": e["group"], "seed": e["model_seed"], "run": a["run"],
               "n_dropped": len(e["drop"]), "metrics": d, "log_loss": a["log_loss"]}
        ok = (a["n"] == npos + nneg and a["errors"] == a["fp"] + a["fn"] and abs(a["error_rate"] - d["error_rate"]) < 1e-15
              and abs(a["mcc"] - d["mcc"]) < 1e-12)
        if not ok:
            problems.append(f"{e['id']}: aggregate internally inconsistent")
        if c is None:
            problems.append(f"{e['id']}: run {a['run']} not in the Colab prediction check")
        else:
            rec["colab_check"] = c
            rec["metrics"]["auroc"] = c["auroc"]
            same = (c["rows_ok"] and c["finite"] and c["ypred_ok"] and c["n"] == a["n"] and c["pos"] == npos
                    and c["fp"] == a["fp"] and c["fn"] == a["fn"] and c["seed"] == e["model_seed"] and c["dev"] == "cuda")
            rec["predictions_match_aggregate"] = same
            if not same:
                problems.append(f"{e['id']}: Colab recomputation differs from aggregate")
            rec["ae_hit_epoch_cap"] = c["ae_run"] >= 100
        runs[e["id"]] = rec
    if len(chk) != 70 or len({v["fp_env"] for v in chk.values()}) != 1 or len({v["dev"] for v in chk.values()}) != 1:
        problems.append("Colab check: not exactly 70 runs in one environment")
    full = {e["model_seed"]: e["id"] for e in matrix["entries"] if e["kind"] == "full"}
    seeds = sorted(full)
    out, pvals, cache = {}, {}, {}
    for g in sorted({e["group"] for e in matrix["entries"] if e["group"]}):
        gid = {e["model_seed"]: e["id"] for e in matrix["entries"] if e["kind"] == "group" and e["group"] == g}
        cid = {e["model_seed"]: e["id"] for e in matrix["entries"] if e["kind"] == "control" and e["group"] == g}
        for ep in ("error_rate", "mcc", "log_loss"):
            val = (lambda r: runs[r]["log_loss"]) if ep == "log_loss" else (lambda r, ep=ep: runs[r]["metrics"][ep])
            dg = np.array([val(gid[s]) - val(full[s]) for s in seeds])
            dc = np.array([val(cid[s]) - val(full[s]) for s in seeds])
            dd = dg - dc
            sf = sign_flip(dd)
            ref = st["r4a_ii"]["groups"][g]["endpoints"][ep]
            same = np.allclose(dd, ref["d"], atol=1e-14) and abs(sf["p"] - ref["sign_flip"]["p"]) < 1e-12
            if not same:
                problems.append(f"R4a-ii {g}/{ep}: recomputed contrast differs from stats_r4a.json")
            r = {"delta_group": dg.tolist(), "delta_control": dc.tolist(), "d": dd.tolist(), "mean_d": float(dd.mean()),
                 "sd_d": float(dd.std(ddof=1)), "sign_flip": sf, "matches_stats_r4a": bool(same)}
            if ep == "error_rate":
                r["interval_98_33_difference"] = tint(dd, 1 - 0.05 / 3)
                r["interval_96_67_tost"] = tint(dd, 1 - 2 * 0.05 / 3)
                r["interval_95_t_sensitivity"] = tint(dd, 0.95)
                if not np.allclose(r["interval_98_33_difference"], ref["reading"]["interval_difference"], atol=1e-14):
                    problems.append(f"R4a-ii {g}: interval differs from stats_r4a.json")
                r["errors_group"] = [runs[gid[s]]["metrics"]["errors"] for s in seeds]
                r["errors_control"] = [runs[cid[s]]["metrics"]["errors"] for s in seeds]
                pvals[f"{g}/error_rate"] = sf["p"]
            out[f"{g}/{ep}"] = r
    for k, v in holm(pvals).items():
        out[k]["p_holm"] = v["p_holm"]; out[k]["holm_reject"] = v["reject"]
        if abs(v["p_holm"] - st["r4a_ii"]["holm"][k]["p_holm"]) > 1e-12:
            problems.append(f"Holm {k} differs")
    # R4a-i: internal consistency of the 110 scores
    sc = json.loads((ROOT / "results/r4a/r4a_i_scores.json").read_text(encoding="utf-8"))
    r1m = load_matrix()
    r1_runs = json.loads((ROOT / "results/milestone3b/aggregate_r1.json").read_text(encoding="utf-8"))["runs"]
    i_out = {}
    for e in r1m["entries"]:
        r = sc["runs"][e["id"]]
        d = derived(r["fp"], r["fn"], sc["n_ddos"], sc["n"] - sc["n_ddos"])
        ok = (r["n"] == sc["n"] and r["run"] == r1_runs[e["id"]]["run"] and abs(r["ddos_recall"] - d["recall"]) < 1e-12
              and abs(r["benign_fpr"] - d["fpr"]) < 1e-12 and abs(r["error_rate"] - d["error_rate"]) < 1e-12
              and abs(r["mcc"] - d["mcc"]) < 1e-12 and r["numerical_sensitivity"]["threshold_crossings"] == 0)
        if not ok:
            problems.append(f"R4a-i {e['id']}: internally inconsistent or scored a different run")
        i_out[e["id"]] = {"kind": e["kind"], "group": e["group"], "seed": e["model_seed"], **d, "log_loss": r["log_loss"]}
    if sc["n"] != npos + nneg or sc["n_ddos"] != npos:
        problems.append("R4a-i population size differs from the R4a-ii population")
    res = {"experiment": "R4a (D-024)", "population": {"test_rows": npos + nneg, "ddos": npos, "benign": nneg,
           "sha256": pop["test_kept_source_rows_sha256"]}, "problems": problems, "statistics_r4a_ii": out,
           "runs_r4a_ii": runs, "r4a_i": i_out}
    (OUT / "verify_r4a.json").write_text(json.dumps(res, indent=1) + "\n", encoding="utf-8")
    print(f"R4a-ii runs {len(runs)}, R4a-i models {len(i_out)}; problems: {len(problems)}")
    for p in problems:
        print("  PROBLEM", p)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
