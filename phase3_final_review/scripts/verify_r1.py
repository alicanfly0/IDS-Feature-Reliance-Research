"""Independent read-only verification of the AE-XGBoost r1 main experiment (110 fits).

Recomputes every test metric from each run's saved predictions_test.csv.gz, re-derives the
pre-registered statistics with an independent implementation (own sign-flip enumeration, Holm,
t intervals), and compares the results with the committed records (aggregate_r1.json, stats_r1.json,
monday_fpr_r1.json). It trains nothing, needs no torch, and writes only into phase3_final_review/.

    python phase3_final_review/scripts/verify_r1.py   (run from the repository root)
"""
from __future__ import annotations

import gzip
import hashlib
import itertools
import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from src.config import load_config  # noqa: E402  (torch-free)
from src.experiments.matrix_3b import load_matrix  # noqa: E402

STORE = ROOT / "results/runs/r1_store/runs"
OUT = ROOT / "phase3_final_review/evidence/verification"
REQ = ["DONE", "ae_done.json", "data_report.json", "effective_config.json", "identity.json", "log.txt",
       "metrics.json", "predictions_test.csv.gz", "predictions_val.csv.gz", "preprocessor.json",
       "run_record.json", "xgb_model.json"]
TOL = 1e-12


def cfg_hash(cfg: dict) -> str:   # same definition as src.experiments.ae_xgb.config_hash
    body = {k: v for k, v in cfg.items() if k != "config_files"}
    return hashlib.sha256(json.dumps(body, sort_keys=True, default=str).encode()).hexdigest()


def metrics(y, prob, ypred_saved=None, thr=0.5) -> dict:
    y = np.asarray(y, int)
    prob = np.asarray(prob, float)
    pred = (prob >= thr).astype(int)
    tp = int(((pred == 1) & (y == 1)).sum()); tn = int(((pred == 0) & (y == 0)).sum())
    fp = int(((pred == 1) & (y == 0)).sum()); fn = int(((pred == 0) & (y == 1)).sum())
    n = len(y)
    prec = tp / (tp + fp) if tp + fp else float("nan")
    rec = tp / (tp + fn) if tp + fn else float("nan")
    denom = math.sqrt(float(tp + fp) * (tp + fn) * (tn + fp) * (tn + fn))
    p = np.clip(prob, 1e-15, 1 - 1e-15)
    fpr = fp / (fp + tn) if fp + tn else float("nan")
    fnr = fn / (fn + tp) if fn + tp else float("nan")
    out = {"n": n, "n_pos": int(y.sum()), "n_neg": int(n - y.sum()), "tp": tp, "tn": tn, "fp": fp, "fn": fn,
           "errors": fp + fn, "error_rate": (fp + fn) / n, "accuracy": (tp + tn) / n, "precision": prec,
           "recall": rec, "f1": 2 * prec * rec / (prec + rec) if prec + rec else float("nan"),
           "mcc": (tp * tn - fp * fn) / denom if denom else 0.0, "auroc": float(roc_auc_score(y, prob)),
           "log_loss": float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p))), "fpr": fpr, "fnr": fnr,
           "balanced_error_rate": (fpr + fnr) / 2, "prob_finite": bool(np.isfinite(prob).all()),
           "prob_in_0_1": bool(((prob >= 0) & (prob <= 1)).all())}
    if ypred_saved is not None:
        out["saved_y_pred_matches_threshold"] = bool((np.asarray(ypred_saved, int) == pred).all())
    return out


def sign_flip(d) -> dict:
    d = np.asarray(d, float)
    nz = d[np.abs(d) > TOL]
    m = len(nz)
    if m == 0:
        return {"p": 1.0, "n_nonzero": 0, "min_attainable_p": 1.0}
    obs = abs(d.sum())
    hits = sum(1 for s in itertools.product((1, -1), repeat=m) if abs(float(np.dot(s, nz))) >= obs - TOL)
    return {"p": hits / 2 ** m, "n_nonzero": m, "min_attainable_p": min(1.0, 2 / 2 ** m)}


def holm(p: dict, alpha=0.05) -> dict:
    items = sorted(p.items(), key=lambda kv: (kv[1], kv[0]))
    m, run, stop, out = len(items), 0.0, False, {}
    for i, (k, v) in enumerate(items):
        run = min(1.0, max(run, (m - i) * v))
        rej = (not stop) and v <= alpha / (m - i)
        stop = stop or not rej
        out[k] = {"p_holm": run, "reject": rej}
    return out


def tint(d, level):
    d = np.asarray(d, float)
    se = d.std(ddof=1) / math.sqrt(len(d))
    q = stats.t.ppf(0.5 + level / 2, len(d) - 1)
    return [float(d.mean() - q * se), float(d.mean() + q * se)]


def find(entry):
    hits = sorted(STORE.glob(f"{entry['experiment_name']}-seed{entry['model_seed']}-*"))
    return hits


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    matrix = load_matrix()
    pop = json.loads((ROOT / matrix["population_file"]).read_text(encoding="utf-8"))
    pop_sha = pop["family_common_model_visible"]["test_kept_source_rows_sha256"]
    agg = json.loads((ROOT / "results/milestone3b/aggregate_r1.json").read_text(encoding="utf-8"))
    st = json.loads((ROOT / "results/milestone3b/stats_r1.json").read_text(encoding="utf-8"))
    mon = json.loads((ROOT / "results/milestone3b/monday_fpr_r1.json").read_text(encoding="utf-8"))
    problems, runs, ref = [], {}, None
    for e in matrix["entries"]:
        hits = find(e)
        done = [h for h in hits if (h / "DONE").is_file()]
        rec = {"id": e["id"], "kind": e["kind"], "group": e["group"], "seed": e["model_seed"],
               "control_draw": e["control_draw"], "n_dropped": len(e["drop"]), "dirs_found": len(hits),
               "dirs_done": len(done)}
        if len(done) != 1:
            problems.append(f"{e['id']}: {len(done)} completed run directories")
            runs[e["id"]] = rec
            continue
        d = done[0]
        rec["run"] = d.name
        rec["missing_files"] = [f for f in REQ if not (d / f).is_file()]
        rec["checkpoints_present"] = (d / "checkpoints").is_dir() and any((d / "checkpoints").iterdir())
        ident = json.loads((d / "identity.json").read_text(encoding="utf-8"))
        used = json.loads((d / "effective_config.json").read_text(encoding="utf-8"))
        rr = json.loads((d / "run_record.json").read_text(encoding="utf-8"))
        rec["config_matches_committed"] = cfg_hash(load_config(ROOT / e["config"])) == cfg_hash(used)
        rec["identity_config_hash_matches"] = ident.get("config_hash") == cfg_hash(used)
        rec["seed_in_config"] = used["run"]["model_seed"]
        rec["dropped_in_config"] = sorted(used["experiment"].get("extra_drop_cols", []))
        rec["drop_matches_matrix"] = rec["dropped_in_config"] == sorted(e["drop"])
        rec["device"] = ident.get("device"); rec["git_commit"] = ident.get("git_commit")
        rec["env_fingerprint"] = ident.get("environment_fingerprint")
        rec["dataset_sha256"] = ident.get("dataset_sha256")
        rec["split_fingerprint"] = rr.get("split_fingerprint")
        rec["input_dim"] = rr.get("input_dim")
        rec["ae"] = rr["autoencoder"]; rec["ae_max_epochs"] = used["ae"]["max_epochs"]
        rec["ae_hit_epoch_cap"] = rr["autoencoder"]["epochs_run"] >= used["ae"]["max_epochs"]
        rec["xgb_best_iteration"] = rr["xgboost"]["best_iteration"]
        rec["xgb_cap"] = used["xgb"]["n_estimators"]
        rec["xgb_hit_cap"] = rr["xgboost"]["best_iteration"] >= used["xgb"]["n_estimators"] - used["xgb"]["early_stopping_rounds"]
        with gzip.open(d / "predictions_test.csv.gz", "rt", encoding="utf-8") as f:
            pred = pd.read_csv(f)
        rows_sha = hashlib.sha256(np.ascontiguousarray(pred["source_row"].to_numpy(np.int64)).tobytes()).hexdigest()
        rec["test_rows_are_family_common"] = rows_sha == pop_sha
        if ref is None:
            ref = pred[["source_row", "y_true"]].copy()
        rec["test_rows_labels_identical_to_first_run"] = bool(pred[["source_row", "y_true"]].equals(ref))
        rec["duplicate_test_rows"] = int(pred["source_row"].duplicated().sum())
        m = metrics(pred["y_true"], pred["prob_ddos"], pred["y_pred"])
        rec["metrics"] = m
        a = agg["runs"][e["id"]]
        rec["matches_aggregate"] = (a["run"] == d.name and a["errors"] == m["errors"] and a["fp"] == m["fp"]
                                    and a["fn"] == m["fn"] and abs(a["mcc"] - m["mcc"]) < 1e-12
                                    and abs(a["log_loss"] - m["log_loss"]) < 1e-12)
        saved = json.loads((d / "metrics.json").read_text(encoding="utf-8"))["test"]
        cm = saved["confusion_matrix"]
        rec["matches_run_metrics_json"] = (saved["n"] == m["n"] and cm == {"tn": m["tn"], "fp": m["fp"], "fn": m["fn"], "tp": m["tp"]}
                                           and abs(saved["auroc"] - m["auroc"]) < 1e-9)
        mo = mon[e["id"]]
        rec["monday"] = {"n": mo["n"], "fp": mo["false_positives"], "fpr": mo["fpr"], "cp95": mo["clopper_pearson_95"],
                         "run_matches": mo["run"] == d.name, "fpr_equals_fp_over_n": abs(mo["fpr"] - mo["false_positives"] / mo["n"]) < 1e-15,
                         "numerical_sensitivity": mo["numerical_sensitivity"]}
        lo = 0.0 if mo["false_positives"] == 0 else stats.beta.ppf(0.025, mo["false_positives"], mo["n"] - mo["false_positives"] + 1)
        hi = stats.beta.ppf(0.975, mo["false_positives"] + 1, mo["n"] - mo["false_positives"])
        rec["monday"]["cp95_recomputed_matches"] = bool(np.allclose([lo, hi], mo["clopper_pearson_95"], rtol=1e-9))
        rec["_pred"] = pred
        for flag in ("config_matches_committed", "identity_config_hash_matches", "drop_matches_matrix",
                     "test_rows_are_family_common", "test_rows_labels_identical_to_first_run", "matches_aggregate",
                     "matches_run_metrics_json"):
            if not rec[flag]:
                problems.append(f"{e['id']}: {flag} is False")
        if rec["missing_files"] or not m["prob_finite"] or not m["prob_in_0_1"] or not m["saved_y_pred_matches_threshold"]:
            problems.append(f"{e['id']}: missing {rec['missing_files']} / finite {m['prob_finite']} / threshold {m['saved_y_pred_matches_threshold']}")
        if not rec["monday"]["run_matches"] or not rec["monday"]["fpr_equals_fp_over_n"] or not rec["monday"]["cp95_recomputed_matches"]:
            problems.append(f"{e['id']}: Monday record inconsistency")
        runs[e["id"]] = rec
    envs = {(r.get("env_fingerprint"), r.get("git_commit"), r.get("device"), json.dumps(r.get("dataset_sha256"), sort_keys=True)) for r in runs.values()}
    if len(envs) != 1:
        problems.append(f"runs differ in environment/commit/device/dataset: {envs}")
    # paired McNemar counts vs aggregate
    full = {e["model_seed"]: e["id"] for e in matrix["entries"] if e["kind"] == "full"}
    for e in matrix["entries"]:
        if e["kind"] == "full":
            continue
        a, f = runs[e["id"]]["_pred"], runs[full[e["model_seed"]]]["_pred"]
        wa, wf = a["y_pred"] != a["y_true"], f["y_pred"] != f["y_true"]
        b, c = int((wa & ~wf).sum()), int((~wa & wf).sum())
        pv = agg["paired_vs_full"][e["id"]]
        if (b, c) != (pv["only_ablated_wrong"], pv["only_full_wrong"]):
            problems.append(f"{e['id']}: McNemar counts differ")
    # statistics, independently
    seeds = sorted(full)
    stat_out, pvals, cache = {}, {}, {}
    for g in sorted({e["group"] for e in matrix["entries"] if e["group"]}):
        gid = {e["model_seed"]: e["id"] for e in matrix["entries"] if e["kind"] == "group" and e["group"] == g}
        cid = {e["model_seed"]: e["id"] for e in matrix["entries"] if e["kind"] == "control" and e["group"] == g}
        for ep in ("error_rate", "fpr", "mcc", "log_loss"):
            val = (lambda rid: runs[rid]["monday"]["fpr"]) if ep == "fpr" else (lambda rid: runs[rid]["metrics"][ep])
            dg = np.array([val(gid[s]) - val(full[s]) for s in seeds])
            dc = np.array([val(cid[s]) - val(full[s]) for s in seeds])
            dd = dg - dc
            sf = sign_flip(dd)
            ref_ep = st["groups"][g]["endpoints"][ep]
            same = (np.allclose(dd, ref_ep["d"], atol=1e-15) and abs(sf["p"] - ref_ep["sign_flip"]["p"]) < 1e-12)
            if not same:
                problems.append(f"stats {g}/{ep}: recomputed d or p differs from stats_r1.json")
            rec = {"delta_group": dg.tolist(), "delta_control": dc.tolist(), "d": dd.tolist(), "mean_d": float(dd.mean()),
                   "sd_d": float(dd.std(ddof=1)), "sign_flip": sf, "matches_stats_r1": bool(same)}
            if ep in ("error_rate", "fpr"):
                rec["interval_99_5_difference"] = tint(dd, 1 - 0.05 / 10)
                rec["interval_99_tost"] = tint(dd, 1 - 2 * 0.05 / 10)
                rec["interval_95_t_sensitivity"] = tint(dd, 0.95)
                pvals[f"{g}/{ep}"] = sf["p"]
                cache[f"{g}/{ep}"] = rec
                if not np.allclose(rec["interval_99_5_difference"], ref_ep["reading"]["interval_difference"], atol=1e-15):
                    problems.append(f"stats {g}/{ep}: interval differs")
            stat_out[f"{g}/{ep}"] = rec
    h = holm(pvals)
    for k, v in h.items():
        stat_out[k]["p_holm"] = v["p_holm"]; stat_out[k]["holm_reject"] = v["reject"]
        if abs(v["p_holm"] - st["holm"][k]["p_holm"]) > 1e-12 or v["reject"] != st["holm"][k]["reject"]:
            problems.append(f"holm {k} differs")
    for r in runs.values():
        r.pop("_pred", None)
    res = {"experiment": "AE-XGBoost r1 (design D, 110 fits)", "store": "results/runs/r1_store/runs (Colab outputs, downloaded)",
           "population_test_sha256": pop_sha, "n_entries": len(matrix["entries"]),
           "n_verified_complete": sum(1 for r in runs.values() if r.get("dirs_done") == 1 and not r.get("missing_files")),
           "environments": [list(x) for x in envs], "problems": problems, "statistics": stat_out, "runs": runs}
    (OUT / "verify_r1.json").write_text(json.dumps(res, indent=1, default=float) + "\n", encoding="utf-8")
    print(f"r1: {res['n_verified_complete']}/{res['n_entries']} complete; problems: {len(problems)}")
    for p in problems[:40]:
        print("  PROBLEM", p)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
