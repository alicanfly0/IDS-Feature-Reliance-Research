"""Build the tidy Phase III CSVs from the verification outputs and committed records (no new results).

    python phase3_final_review/scripts/build_tables.py
Writes phase3_final_review/PHASE3_ALL_METRICS.csv and PHASE3_STATISTICAL_FINDINGS.csv.
Every row names the record it comes from. Populations are never pooled.
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import numpy as np
from scipy import stats

ROOT = Path(__file__).resolve().parents[2]
REV = ROOT / "phase3_final_review"
V = REV / "evidence/verification"
load = lambda p: json.loads(Path(p).read_text(encoding="utf-8"))

POP_R1 = "CICIDS2017 Fri DDoS family-common test (33,038 rows; 19,233 DDoS)"
POP_MON = "CICIDS2017 Monday benign, training-twin-excluded (494,940 rows; benign only)"
POP_R4A = "Engelen corrected Fri DDoS window, family-common test (22,049 rows; 14,168 DDoS)"
METRICS = ("accuracy", "precision", "recall", "f1", "mcc", "auroc", "log_loss", "error_rate", "fpr", "fnr",
           "balanced_error_rate", "tp", "tn", "fp", "fn", "errors")


def view(kind, group):
    return "full" if kind == "full" else f"{kind}:{group}"


def main() -> int:
    rows = []
    add = lambda **k: rows.append(k)
    r1 = load(V / "verify_r1.json")
    for rid, r in r1["runs"].items():
        for mname in METRICS:
            add(experiment="AE-XGBoost r1 main (design D)", dataset="CICIDS2017 original", model="AE-XGBoost",
                view=view(r["kind"], r["group"]), run_id=rid, seed=r["seed"], population=POP_R1, metric=mname,
                value=r["metrics"][mname], source="phase3_final_review/evidence/verification/verify_r1.json <- results/runs/r1_store/runs/" + r["run"] + "/predictions_test.csv.gz")
        for mname, val in (("monday_false_positives", r["monday"]["fp"]), ("monday_fpr", r["monday"]["fpr"]),
                           ("monday_fpr_cp95_lo", r["monday"]["cp95"][0]), ("monday_fpr_cp95_hi", r["monday"]["cp95"][1])):
            add(experiment="AE-XGBoost r1 Monday benign scoring", dataset="CICIDS2017 original (Monday)", model="AE-XGBoost",
                view=view(r["kind"], r["group"]), run_id=rid, seed=r["seed"], population=POP_MON, metric=mname, value=val,
                source="results/milestone3b/monday_fpr_r1.json")
    r4 = load(V / "verify_r4a.json")
    for rid, r in r4["runs_r4a_ii"].items():
        for mname in METRICS:
            val = r["log_loss"] if mname == "log_loss" else r["metrics"].get(mname)
            add(experiment="R4a-ii corrected-data ablation (D-024)", dataset="CICIDS2017 Engelen WTMC2021 corrected", model="AE-XGBoost",
                view=view(r["kind"], r["group"]), run_id=rid, seed=r["seed"], population=POP_R4A, metric=mname, value=val,
                source="results/r4a/aggregate_r4a.json + phase3_final_review/evidence/verification/r4a_predictions_colab_check.json (AUROC)")
    for rid, r in r4["r4a_i"].items():
        for mname in ("recall", "fpr", "error_rate", "mcc", "accuracy", "precision", "f1", "fnr", "balanced_error_rate", "log_loss", "tp", "tn", "fp", "fn"):
            add(experiment="R4a-i transfer (descriptive; r1 models on corrected rows)", dataset="train: CICIDS2017 original; test: Engelen corrected",
                model="AE-XGBoost (r1)", view=view(r["kind"], r["group"]), run_id=rid, seed=r["seed"], population=POP_R4A,
                metric=mname, value=r[mname], source="results/r4a/r4a_i_scores.json")
    dc = load(V / "verify_dcnn.json")
    pops = {"official": "UNSW-NB15 official test, Normal+DoS (41,089; 4,089 DoS)",
            "dedup_model_visible": "UNSW-NB15 test minus model-visible training duplicates (37,759; 2,621 DoS)",
            "dedup_raw_features": "UNSW-NB15 test minus raw-feature training duplicates (39,694; 3,887 DoS) [sensitivity]"}
    for s, r in dc["seeds"].items():
        for p, label in pops.items():
            for mname in ("accuracy", "dos_precision", "dos_recall", "dos_f1", "mcc", "roc_auc", "fpr", "fnr", "tp", "tn", "fp", "fn", "errors"):
                add(experiment="DCNN+SA adaptation (D-009)", dataset="UNSW-NB15", model="DCNN+self-attention", view="22 LightGBM-SHAP features",
                    run_id=f"dcnn_seed{s}", seed=int(s), population=label, metric=mname, value=r[p][mname],
                    source=f"phase3_final_review/evidence/verification/verify_dcnn.json <- results/dcnn_fang/seed{s}/test_proba.npy")
    me = load(V / "verify_mes.json")
    for fk, f in me["fits"].items():
        mode, seed = fk.rsplit("_seed", 1)
        for key, mm in f["test"].items():
            net, model, pop = key.split("/")
            label = f"{net} test partition ({'all rows' if pop == 'all' else 'rows whose vector is absent from base/meta/val'}), {mode} split"
            for mname in ("accuracy", "precision", "recall", "f1", "mcc", "roc_auc", "fpr", "tp", "tn", "fp", "fn", "n"):
                if mname in mm:
                    add(experiment="MES-DNN two-network adaptation (D-010)", dataset=net, model=f"MES-DNN {model}", view=mode,
                        run_id=fk, seed=int(seed), population=label, metric=mname, value=mm[mname],
                        source=f"phase3_final_review/evidence/verification/verify_mes.json <- results/mes_dnn/{fk}/test_proba.npz")
    cols = ["experiment", "dataset", "model", "view", "run_id", "seed", "population", "metric", "value", "source"]
    with open(REV / "PHASE3_ALL_METRICS.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        for r in rows:
            if isinstance(r["value"], float) and not np.isfinite(r["value"]):
                r["value"] = "nan"
            w.writerow(r)
    # ---------------------------------------------------------------- statistics
    srows = []
    s1 = load(ROOT / "results/milestone3b/stats_r1.json")
    s4 = load(ROOT / "results/r4a/stats_r4a.json")
    assum = ("pairs s=0..9 independent given the fixed test rows; exact under the sharp null of exchangeable group/control "
             "within a pair; ties reduce attainable p; inference conditional on one capture")
    for fam, st, ver, lev, fsize, src in (("r1 primary (10 tests)", s1, r1["statistics"], ("99.5", "99"), 10, "results/milestone3b/stats_r1.json"),
                                         ("R4a-ii primary (3 tests)", s4["r4a_ii"], r4["statistics_r4a_ii"], ("98.33", "96.67"), 3, "results/r4a/stats_r4a.json")):
        for g, rec in st["groups"].items():
            for ep, r in rec["endpoints"].items():
                v = ver[f"{g}/{ep}"]
                prim = r.get("primary", False)
                rd = r.get("reading", {})
                srows.append({"family": fam if prim else fam.split(" ")[0] + " secondary (descriptive)", "group": g,
                              "inputs_removed": rec["removed_inputs"], "endpoint": ep, "primary": prim, "n_pairs": len(r["d"]),
                              "orientation": "Delta = ablated - full; d = Delta_group - Delta_control; d>0: group removal hurts more" + ("; MCC is higher-is-better" if ep == "mcc" else ""),
                              "mean_delta_group": r["mean_delta_group"], "mean_delta_control": r["mean_delta_control"], "mean_d": v["mean_d"],
                              "sd_d": v["sd_d"], "difference_interval_level_pct": lev[0] if prim else "",
                              "difference_interval_lo": rd.get("interval_difference", ["", ""])[0], "difference_interval_hi": rd.get("interval_difference", ["", ""])[1],
                              "tost_interval_level_pct": lev[1] if prim else "",
                              "tost_lo": rd.get("interval_equivalence", ["", ""])[0], "tost_hi": rd.get("interval_equivalence", ["", ""])[1],
                              "p_exact_signflip": r["sign_flip"]["p"], "n_nonzero_pairs": r["sign_flip"]["n_nonzero"],
                              "min_attainable_p": r["sign_flip"]["min_attainable_p"], "p_holm": r.get("p_holm", ""),
                              "holm_reject_0.05": st["holm"].get(f"{g}/{ep}", {}).get("reject", "") if prim else "",
                              "sesoi": (st["sesoi"][ep] if isinstance(st["sesoi"], dict) else st["sesoi"]) if prim else "",
                              "reading_preregistered": rd.get("reading", "not tested (secondary)"),
                              "independently_reproduced": v.get("matches_stats_r1", v.get("matches_stats_r4a")),
                              "assumptions": assum, "source": src})
    cmp = s4["original_vs_corrected"]
    for g, c in cmp["groups"].items():
        w = c["corrected_minus_original"]
        srows.append({"family": "original vs corrected (observational, not tested)", "group": g, "inputs_removed":
                      f"{c['removed_inputs_original']} (orig) / {c['removed_inputs_corrected']} (corr)", "endpoint": "error_rate",
                      "primary": False, "n_pairs": 10, "orientation": "mean d(corrected) - mean d(original)",
                      "mean_d": w["difference"], "difference_interval_level_pct": "95 (Welch, descriptive)",
                      "difference_interval_lo": w["interval"][0], "difference_interval_hi": w["interval"][1],
                      "reading_preregistered": "descriptive only (D-024): group composition, segmentation, labels, populations and definitions differ",
                      "assumptions": "Welch t on two independent sets of 10 seed-level contrasts; datasets are not exchangeable", "source": "results/r4a/stats_r4a.json"})
    # DCNN: official vs duplicate-filtered, paired across seeds (descriptive)
    for mname in ("mcc", "dos_precision", "dos_recall", "fpr", "roc_auc"):
        a = np.array([dc["seeds"][str(s)]["official"][mname] for s in range(5)])
        b = np.array([dc["seeds"][str(s)]["dedup_model_visible"][mname] for s in range(5)])
        dlt = b - a
        se = dlt.std(ddof=1) / np.sqrt(5)
        q = stats.t.ppf(0.975, 4)
        srows.append({"family": "DCNN official vs duplicate-filtered (descriptive, paired by seed)", "group": "-", "endpoint": mname,
                      "primary": False, "n_pairs": 5, "orientation": "filtered - official", "mean_d": float(dlt.mean()), "sd_d": float(dlt.std(ddof=1)),
                      "difference_interval_level_pct": "95 (paired t over 5 seeds, descriptive)", "difference_interval_lo": float(dlt.mean() - q * se),
                      "difference_interval_hi": float(dlt.mean() + q * se),
                      "reading_preregistered": "not pre-registered as a test; population change, not a model change",
                      "assumptions": "the same 5 models scored on nested test populations; rows not independent across populations",
                      "source": "phase3_final_review/evidence/verification/verify_dcnn.json"})
    cols = ["family", "group", "inputs_removed", "endpoint", "primary", "n_pairs", "orientation", "mean_delta_group", "mean_delta_control",
            "mean_d", "sd_d", "difference_interval_level_pct", "difference_interval_lo", "difference_interval_hi", "tost_interval_level_pct",
            "tost_lo", "tost_hi", "p_exact_signflip", "n_nonzero_pairs", "min_attainable_p", "p_holm", "holm_reject_0.05", "sesoi",
            "reading_preregistered", "independently_reproduced", "assumptions", "source"]
    with open(REV / "PHASE3_STATISTICAL_FINDINGS.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        for r in srows:
            w.writerow({c: r.get(c, "") for c in cols})
    print(f"metrics rows {len(rows)}, statistics rows {len(srows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
