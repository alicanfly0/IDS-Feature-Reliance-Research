"""Original-feature SHAP for the AE-XGBoost baseline, with ARR@K (decision log D-002, D-012, D-019).

    python -m src.audit.shap_explain --config configs/experiments/ae_xgb_d008_trackB.yaml \
        --run results/runs/ae_xgb_d008_trackB-seed0-cpu-565a8b9e --background 100 --explain 200 \
        --permutations 5 --variants 0:0 1:0 0:1

Method: SHAP Permutation explainer on the composite function raw features -> preprocessing -> AE ->
XGBoost (CompositeModel, float64 batch-invariant evaluation), output on the log-odds (margin) scale, interventional masking with an
independent masker whose background is a stratified sample of the TRAINING partition. Explained rows
are a stratified sample of the TEST partition; misclassified test rows are explained separately for
local explanations and are not part of the global importance. Each variant (background seed, sample
seed) is cached under results/shap/<run>/<settings hash>/ and never recomputed. Attributions describe
what this model's output responds to under this masking; they are not causal evidence.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
from pathlib import Path

import numpy as np
import pandas as pd
import shap

from src.audit.arr import arr_table, merge_columns, top_k
from src.audit.composite import CompositeModel
from src.audit.registry import load_registry, feature_sets
from src.config import ROOT
from src.data import ddos
from src.experiments.ae_xgb import load_experiment

KS = (2, 5, 10, 20)
MERGES = {"Fwd Header Length.1": "Fwd Header Length"}   # identical duplicate column (registry R05)


def stratified_sample(positions: np.ndarray, y: np.ndarray, n: int, seed: int) -> np.ndarray:
    """Deterministic class-proportional sample of `positions` (y gives each position's label)."""
    rng = np.random.RandomState(seed)
    out = []
    labels, counts = np.unique(y, return_counts=True)
    alloc = np.floor(n * counts / counts.sum()).astype(int)
    alloc[np.argmax(counts)] += n - alloc.sum()
    for lab, k in zip(labels, alloc):
        pool = positions[y == lab]
        out.append(rng.choice(pool, size=min(k, len(pool)), replace=False))
    return np.sort(np.concatenate(out))


def _hash(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()


def explain_rows(cm: CompositeModel, background: np.ndarray, x: np.ndarray, max_evals: int, seed: int) -> dict:
    masker = shap.maskers.Independent(background, max_samples=len(background))
    explainer = shap.explainers.Permutation(cm.margin, masker, seed=seed)
    t = time.perf_counter()
    ex = explainer(x, max_evals=max_evals, silent=True)
    seconds = time.perf_counter() - t
    values, base = np.asarray(ex.values, dtype=np.float64), np.asarray(ex.base_values, dtype=np.float64)
    fx = cm.margin(x)
    unused = [i for i, c in enumerate(cm.raw_columns) if c not in cm.model_columns]   # constant on train
    checks = {
        "unused_columns_max_abs_shap": float(np.abs(values[:, unused]).max()) if len(x) and unused else 0.0,
        "shape": list(values.shape), "finite": bool(np.isfinite(values).all() and np.isfinite(base).all()),
        "additivity_max_abs_error": float(np.abs(values.sum(axis=1) + base - fx).max()) if len(x) else 0.0,
        "base_value_equals_mean_background_margin": float(abs(base.mean() - cm.margin(background).mean())) if len(x) else 0.0,
    }
    return {"values": values, "base": base, "fx": fx, "seconds": seconds, "checks": checks}


def global_importance(values: np.ndarray, columns: list[str]) -> dict[str, float]:
    return {c: float(v) for c, v in zip(columns, np.abs(values).mean(axis=0))}


def run_variant(cm, prep, reg, out_root: Path, bg_seed: int, sample_seed: int, n_background: int, n_explain: int,
                permutations: int, log=print) -> dict:
    cols, parts, y = prep.feature_cols, prep.split.parts(), prep.y
    raw = prep.frame[cols].to_numpy(dtype=np.float64)
    bg_pos = stratified_sample(parts["train"], y[parts["train"]], n_background, bg_seed)
    ex_pos = stratified_sample(parts["test"], y[parts["test"]], n_explain, sample_seed)
    max_evals = permutations * (2 * len(cols) + 1)   # shap: npermutations = max_evals // (2 * n_varying + 1)
    settings = {
        "method": "shap.explainers.Permutation", "shap_version": shap.__version__, "output": "margin (log-odds of DDoS)",
        "masker": "Independent (interventional), background = stratified TRAIN sample",
        "background_partition": "train", "explain_partition": "test", "n_background": n_background,
        "n_explain": n_explain, "permutations": permutations, "max_evals": max_evals,
        "background_seed": bg_seed, "sample_seed": sample_seed, "explainer_seed": sample_seed,
        "model": cm.provenance, "split_fingerprint": prep.split.fingerprint(), "columns": cols,
        "background_source_rows": prep.frame.index[bg_pos].tolist(), "explained_source_rows": prep.frame.index[ex_pos].tolist(),
    }
    key = _hash(settings)[:12]
    out = out_root / f"variant-bg{n_background}x{bg_seed}-ex{n_explain}x{sample_seed}-p{permutations}-{key}"
    if (out / "summary.json").is_file():
        log(f"variant {out.name}: cached, not recomputed")
        return json.loads((out / "summary.json").read_text(encoding="utf-8"))
    out.mkdir(parents=True, exist_ok=True)
    res = explain_rows(cm, raw[bg_pos], raw[ex_pos], max_evals, sample_seed)
    importance = global_importance(res["values"], cols)
    merged = merge_columns(importance, MERGES)
    tiers_cols = feature_sets(reg, cols)
    tiers_merged = {t: {MERGES.get(c, c) for c in s} for t, s in tiers_cols.items() if t != "missing"}
    summary = {
        "variant": out.name, "settings_hash": key, "runtime_seconds": round(res["seconds"], 2),
        "seconds_per_explained_row": round(res["seconds"] / max(n_explain, 1), 4), "checks": res["checks"],
        "mean_base_value": float(res["base"].mean()),
        "importance_column_level": dict(sorted(importance.items(), key=lambda kv: -kv[1])),
        "importance_merged": dict(sorted(merged.items(), key=lambda kv: -kv[1])),
        "arr_merged": arr_table(merged, {t: s for t, s in tiers_merged.items() if t in ("direct", "shortcut", "all")}, KS),
        "arr_column_level": arr_table(importance, {t: s for t, s in tiers_cols.items() if t in ("direct", "shortcut", "all")}, KS),
        "registry_missing_from_model": tiers_cols["missing"],
    }
    np.savez_compressed(out / "shap_values.npz", values=res["values"].astype(np.float32), base=res["base"], fx=res["fx"],
                        source_rows=prep.frame.index[ex_pos].to_numpy(), y_true=y[ex_pos])
    (out / "settings.json").write_text(json.dumps(settings, indent=1), encoding="utf-8")
    summary = json.loads(json.dumps(summary))
    tmp = out / "summary.tmp.json"
    tmp.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    os.replace(tmp, out / "summary.json")
    log(f"variant {out.name}: {n_explain} rows in {res['seconds']:.1f}s, additivity error {res['checks']['additivity_max_abs_error']:.2e}")
    return summary


def local_explanations(cm, prep, out_root: Path, bg_seed: int, n_background: int, permutations: int,
                       baseline_run: Path, n_correct_per_class: int = 2, seed: int = 0, top: int = 8) -> dict:
    """Misclassified test rows plus a few correctly classified ones, explained individually."""
    out = out_root / f"local-bg{n_background}x{bg_seed}-p{permutations}-s{seed}"
    if (out / "local.json").is_file():
        return json.loads((out / "local.json").read_text(encoding="utf-8"))
    cols, parts, y = prep.feature_cols, prep.split.parts(), prep.y
    pred = pd.read_csv(baseline_run / "predictions_test.csv.gz").set_index("source_row")
    pos_of = pd.Series(np.arange(len(prep.frame)), index=prep.frame.index)
    wrong = pred.index[pred.y_true != pred.y_pred]
    rng = np.random.RandomState(seed)
    chosen = [("misclassified", r) for r in wrong]
    for label in (1, 0):
        pool = pred.index[(pred.y_true == label) & (pred.y_pred == label)]
        chosen += [("correct", r) for r in rng.choice(pool, n_correct_per_class, replace=False)]
    raw = prep.frame[cols].to_numpy(dtype=np.float64)
    bg_pos = stratified_sample(parts["train"], y[parts["train"]], n_background, bg_seed)
    x_pos = pos_of.loc[[r for _, r in chosen]].to_numpy()
    res = explain_rows(cm, raw[bg_pos], raw[x_pos], permutations * (2 * len(cols) + 1), seed)
    rows = []
    for i, (kind, r) in enumerate(chosen):
        contrib = pd.Series(res["values"][i], index=cols)
        contrib = contrib.groupby(lambda c: MERGES.get(c, c)).sum()
        topc = contrib.reindex(contrib.abs().sort_values(ascending=False).index[:top])
        rows.append({"kind": kind, "source_row": int(r), "y_true": int(pred.at[r, "y_true"]),
                     "prob_ddos_saved": float(pred.at[r, "prob_ddos"]), "margin": float(res["fx"][i]),
                     "base_value": float(res["base"][i]),
                     "top_contributions": {c: round(float(v), 4) for c, v in topc.items()},
                     "feature_values": {c: float(prep.frame.at[r, c]) for c in topc.index}})
    result = {"background_seed": bg_seed, "checks": res["checks"], "rows": rows}
    out.mkdir(parents=True, exist_ok=True)
    (out / "local.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def stability(summaries: list[dict]) -> dict:
    """Rank agreement of global importance (merged) across variants."""
    imps = [pd.Series(s["importance_merged"]) for s in summaries]
    names = [s["variant"] for s in summaries]
    frame = pd.concat(imps, axis=1, keys=names).fillna(0.0)
    out = {"spearman_all_features": frame.rank(ascending=False).corr(method="pearson").round(4).to_dict()}
    # Zero-importance (constant) features tie and inflate the all-feature value; also report the
    # correlation over the union of every variant's Top-20.
    union = sorted(set().union(*(top_k(s.to_dict(), 20) for s in imps)))
    sub = frame.loc[union].rank(ascending=False).corr(method="pearson")
    out["spearman_top20_union"] = {"features": len(union), "min": round(float(sub.values.min()), 4),
                                   "matrix": sub.round(4).to_dict()}
    for k in (5, 10, 20):
        tops = [set(top_k(s.to_dict(), k)) for s in imps]
        out[f"top{k}_intersection"] = sorted(set.intersection(*tops))
        out[f"top{k}_intersection_size"] = len(set.intersection(*tops))
    out["arr_merged_range"] = {tier: {k: [min(vals), max(vals)] for k in KS
                                      for vals in [[s["arr_merged"][str(k)][tier] for s in summaries]]}
                               for tier in ("direct", "shortcut", "all")}
    return out


def summarize_cached(out_root: Path) -> dict:
    """Stability and ARR@K over every cached variant of a run (reads results only, computes no SHAP)."""
    summaries = [json.loads(f.read_text(encoding="utf-8")) for f in sorted(out_root.glob("variant-*/summary.json"))]
    if len(summaries) < 2:
        raise RuntimeError("need at least two cached variants")
    mean = pd.DataFrame({x["variant"]: x["importance_merged"] for x in summaries}).mean(axis=1)
    out = {"variants": [x["variant"] for x in summaries], "stability": stability(summaries),
           "mean_importance_merged_top20": {c: round(float(mean[c]), 4) for c in top_k(mean.to_dict(), 20)},
           "rank_per_variant": {x["variant"]: {c: top_k(x["importance_merged"], 99).index(c) + 1
                                               for c in top_k(mean.to_dict(), 20)} for x in summaries},
           "arr_merged": {x["variant"]: {k: {t: x["arr_merged"][k][t] for t in ("direct", "shortcut", "all")}
                                         for k in x["arr_merged"]} for x in summaries},
           "runtime_seconds": {x["variant"]: x["runtime_seconds"] for x in summaries}}
    (out_root / "stability_all_variants.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    return out


def plot_global(summary: dict, path: Path, top: int = 20) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    imp = pd.Series(summary["importance_merged"]).sort_values(ascending=False).iloc[:top][::-1]
    reg = load_registry()
    level = {MERGES.get(c, c): e["evidence_level"] for c, e in ((c, e) for e in reg["features"] for c in e["columns"])}
    colors = {"direct_extraction_error": "#B0413E", "shortcut_indicator": "#D08C2E", "unverified_hypothesis": "#7A7AA0"}
    fig, ax = plt.subplots(figsize=(7.5, 6.5))
    ax.barh(imp.index, imp.values, color=[colors.get(level.get(c), "#9AA3AD") for c in imp.index])
    ax.set_xlabel("mean |SHAP| (log-odds of DDoS)")
    ax.set_title(f"AE-XGBoost, original features — {summary['variant']}", fontsize=9)
    from matplotlib.patches import Patch
    handles = [Patch(color=col, label=name) for name, col in [
        ("direct extraction error", colors["direct_extraction_error"]), ("shortcut indicator", colors["shortcut_indicator"]),
        ("unverified hypothesis", colors["unverified_hypothesis"]), ("not registered", "#9AA3AD")]]
    ax.legend(handles=handles, loc="lower right", fontsize=8, frameon=False)
    ax.set_xlim(left=0)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(path, dpi=110)
    plt.close(fig)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--run", required=True, type=Path, help="completed baseline run folder (not retrained)")
    parser.add_argument("--background", type=int, default=100)
    parser.add_argument("--explain", type=int, default=200)
    parser.add_argument("--permutations", type=int, default=5)
    parser.add_argument("--variants", nargs="+", default=["0:0", "1:0", "0:1"], help="background_seed:sample_seed")
    parser.add_argument("--no-local", action="store_true")
    parser.add_argument("--out", type=Path)
    parser.add_argument("--summarize", action="store_true", help="only compare the cached variants of --run")
    args = parser.parse_args(argv)
    if args.summarize:
        res = summarize_cached(args.out or ROOT / "results" / "shap" / args.run.name)
        print(json.dumps({k: res[k] for k in ("mean_importance_merged_top20", "runtime_seconds")}, indent=1))
        return 0
    cfg = load_experiment(args.config)
    s, d = cfg["experiment"]["split"], cfg["data"]
    csv, _ = ddos.verified_csv()
    prep = ddos.prepare(ddos.load(csv), d["label_map"], tuple(s["fractions"]), s["seed"], tuple(d["nonnegative_cols"]))
    if prep.split.fingerprint() != s["expected_fingerprint"]:
        raise RuntimeError("split differs from the pinned split")
    reg = load_registry()
    cm = CompositeModel(args.run, prep.feature_cols, precision="float64")   # batch-invariant (D-019)
    out_root = args.out or ROOT / "results" / "shap" / args.run.name
    out_root.mkdir(parents=True, exist_ok=True)
    summaries = []
    for v in args.variants:
        bg_seed, sample_seed = (int(x) for x in v.split(":"))
        summaries.append(run_variant(cm, prep, reg, out_root, bg_seed, sample_seed, args.background, args.explain,
                                     args.permutations))
    report = {"variants": [x["variant"] for x in summaries], "stability": stability(summaries) if len(summaries) > 1 else None,
              "runtime_seconds": {x["variant"]: x["runtime_seconds"] for x in summaries},
              "checks": {x["variant"]: x["checks"] for x in summaries}}
    if not args.no_local:
        report["local"] = local_explanations(cm, prep, out_root, 0, args.background, args.permutations, args.run)
    tag = f"bg{args.background}-ex{args.explain}-p{args.permutations}"
    report["settings"] = {"background": args.background, "explain": args.explain, "permutations": args.permutations,
                          "variants": args.variants, "precision": cm.precision}
    (out_root / f"report-{tag}.json").write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    plot_global(summaries[0], out_root / f"global_importance_top20-{tag}.png")
    print(json.dumps({k: report[k] for k in ("runtime_seconds", "checks", "stability")}, indent=1, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
