"""Shortcut diagnostics on the D-008 scope (read-only; trains no AE-XGBoost model).

    python -m src.experiments.shortcut_diagnostics --config configs/experiments/ae_xgb_d008_trackB.yaml \
        --baseline-run results/runs/ae_xgb_d008_trackB-seed0-cpu-565a8b9e

Uses the verified data and the pinned track-B split. Simple single-feature models are
fitted on the TRAINING partition only; validation ranks them; test is reported alongside.
Writes results/diagnostics/<experiment>-shortcuts.json. Association is measured here;
whether a feature is an artifact needs separate evidence (decision log D-012).
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.tree import DecisionTreeClassifier

from src.config import ROOT
from src.data import ddos
from src.data.split import conflicting_groups, content_groups, exclude_eval_twins, partition_overlap
from src.evaluation.metrics import binary_metrics
from src.experiments.ae_xgb import load_experiment

PORT = "Destination Port"


def _short(m: dict) -> dict:
    return {k: (round(m[k], 6) if isinstance(m[k], float) else m[k])
            for k in ("accuracy", "precision", "recall", "f1", "mcc", "auroc", "confusion_matrix")}


def port_association(prep) -> dict:
    df, y, parts = prep.frame, prep.y, prep.split.parts()
    port = df[PORT].to_numpy()
    out = {"per_class": {}, "per_partition": {}}
    for label, name in ((1, "ddos"), (0, "benign")):
        vc = pd.Series(port[y == label]).value_counts()
        out["per_class"][name] = {"rows": int((y == label).sum()), "distinct_ports": int(vc.size),
                                  "top_ports": {str(k): int(v) for k, v in vc.head(10).items()},
                                  "share_port_80": round(float((port[y == label] == 80).mean()), 6)}
    for p, idx in parts.items():
        py, pp = y[idx], port[idx]
        out["per_partition"][p] = {
            "ddos_port80": int(((py == 1) & (pp == 80)).sum()), "ddos_other": int(((py == 1) & (pp != 80)).sum()),
            "benign_port80": int(((py == 0) & (pp == 80)).sum()), "benign_other": int(((py == 0) & (pp != 80)).sum()),
        }
    # Rule "port == 80 -> DDoS" (no fitting) and a port-only lookup fitted on train.
    train = pd.DataFrame({"port": port[parts["train"]], "y": y[parts["train"]]})
    rate = train.groupby("port")["y"].mean()
    prior = float(train["y"].mean())
    out["rule_port80_is_ddos"], out["port_lookup_fitted_on_train"] = {}, {}
    for p in ("val", "test"):
        idx = parts[p]
        out["rule_port80_is_ddos"][p] = _short(binary_metrics(y[idx], (port[idx] == 80).astype(float)))
        prob = pd.Series(port[idx]).map(rate).fillna(prior).to_numpy()
        out["port_lookup_fitted_on_train"][p] = _short(binary_metrics(y[idx], prob))
        out["port_lookup_fitted_on_train"][p]["unseen_ports_rows"] = int((~pd.Series(port[idx]).isin(rate.index)).sum())
    out["benign_port80_rows_with_ddos_rate_in_train"] = round(float(rate.get(80, np.nan)), 6)
    return out


def single_feature_trees(prep, depths=(1, 2)) -> list[dict]:
    df, y, parts = prep.frame, prep.y, prep.split.parts()
    rows = []
    for col in prep.feature_cols:
        x = df[col].to_numpy(dtype=np.float64).reshape(-1, 1)
        if np.unique(x[parts["train"]]).size < 2:
            continue
        entry = {"feature": col}
        for depth in depths:
            tree = DecisionTreeClassifier(max_depth=depth, random_state=0).fit(x[parts["train"]], y[parts["train"]])
            for p in ("val", "test"):
                prob = tree.predict_proba(x[parts[p]])[:, list(tree.classes_).index(1)]
                m = binary_metrics(y[parts[p]], prob)
                entry[f"depth{depth}_{p}_mcc"] = round(m["mcc"], 6)
                entry[f"depth{depth}_{p}_accuracy"] = round(m["accuracy"], 6)
            if depth == 1:
                t = tree.tree_
                entry["depth1_threshold"] = float(t.threshold[0])
                left = t.value[1][0]
                entry["depth1_left_is_ddos"] = bool(left[list(tree.classes_).index(1)] > left[list(tree.classes_).index(0)])
        rows.append(entry)
    return sorted(rows, key=lambda r: -r["depth1_val_mcc"])


def port80_conditional_trees(prep, top: int = 10) -> dict:
    """Among port-80 flows only (where the port cannot separate the classes), how well does one
    other feature separate DDoS from BENIGN? Fitted on train port-80 rows; ranked on validation."""
    df, y, parts = prep.frame, prep.y, prep.split.parts()
    is80 = df[PORT].to_numpy() == 80
    idx = {p: i[is80[i]] for p, i in parts.items()}
    rows = []
    for col in prep.feature_cols:
        if col == PORT:
            continue
        x = df[col].to_numpy(dtype=np.float64).reshape(-1, 1)
        tree = DecisionTreeClassifier(max_depth=1, random_state=0).fit(x[idx["train"]], y[idx["train"]])
        entry = {"feature": col, "threshold": float(tree.tree_.threshold[0])}
        for p in ("val", "test"):
            prob = tree.predict_proba(x[idx[p]])[:, list(tree.classes_).index(1)]
            m = binary_metrics(y[idx[p]], prob)
            entry[f"{p}_mcc"], entry[f"{p}_accuracy"] = round(m["mcc"], 6), round(m["accuracy"], 6)
            entry[f"{p}_confusion"] = m["confusion_matrix"]
        rows.append(entry)
    rows.sort(key=lambda r: -r["val_mcc"])
    sizes = {p: {"rows": int(len(i)), "ddos": int(y[i].sum()), "benign": int((y[i] == 0).sum())} for p, i in idx.items()}
    return {"port80_rows": sizes, "top": rows[:top]}


def removal_overlap(prep, drop: list[str]) -> dict:
    """Cross-partition duplicates and label conflicts if `drop` columns leave the model input,
    under the ORIGINAL (78-feature) split."""
    feats = [c for c in prep.feature_cols if c not in drop]
    groups = content_groups(prep.frame, feats)
    split = prep.split
    overlap = partition_overlap(groups, split)
    conflicts = conflicting_groups(groups, prep.y)
    conflict_rows = np.isin(groups, conflicts)
    parts = split.parts()
    train_groups = set(groups[parts["train"]])
    affected = {}
    for p in ("val", "test"):
        idx = parts[p]
        hit = np.array([g in train_groups for g in groups[idx]])
        affected[p] = {"rows_with_train_twin": int(hit.sum()), "ddos": int(prep.y[idx][hit].sum()),
                       "benign": int((prep.y[idx][hit] == 0).sum())}
    reduced, info = exclude_eval_twins(groups, split)
    common = {p: {"rows": int(len(i)), "ddos": int(prep.y[i].sum()), "benign": int((prep.y[i] == 0).sum())}
              for p, i in reduced.parts().items()}
    excluded_rows = prep.frame.index.to_numpy()[info["test_excluded_positions"]]
    return {"dropped": drop, "n_features": len(feats), "distinct_vectors": int(len(np.unique(groups))),
            "partition_overlap": overlap, "rows_with_train_twin": affected,
            "exclude_eval_twins": {"val_excluded": info["val_excluded"], "test_excluded": info["test_excluded"],
                                   "evaluation_population": common,
                                   "excluded_test_rows_port80": int((prep.frame.loc[excluded_rows, PORT] == 80).sum()),
                                   "excluded_test_rows_top_ports": {str(k): int(v) for k, v in
                                       prep.frame.loc[excluded_rows, PORT].value_counts().head(5).items()},
                                   "evaluation_fingerprint": reduced.fingerprint()},
            "conflicting_label_groups": int(len(conflicts)), "conflicting_label_rows": int(conflict_rows.sum()),
            "conflicting_label_rows_per_partition": {p: int(conflict_rows[i].sum()) for p, i in parts.items()}}


def baseline_errors(prep, run_dir: Path, top_features: list[str]) -> dict:
    out = {}
    for p in ("val", "test"):
        pred = pd.read_csv(run_dir / f"predictions_{p}.csv.gz")
        wrong = pred[pred.y_true != pred.y_pred]
        cols = [PORT, *[c for c in top_features if c != PORT]]
        rows = prep.frame.loc[wrong.source_row, cols]
        out[p] = [{"source_row": int(r.source_row), "y_true": int(r.y_true), "prob_ddos": round(float(r.prob_ddos), 6),
                   **{c: float(rows.loc[r.source_row, c]) for c in cols}} for r in wrong.itertuples()]
    return out


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--baseline-run", type=Path, help="completed run folder whose saved predictions to inspect")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)
    cfg = load_experiment(args.config)
    s, d = cfg["experiment"]["split"], cfg["data"]
    csv, provenance = ddos.verified_csv()
    prep = ddos.prepare(ddos.load(csv), d["label_map"], tuple(s["fractions"]), s["seed"], tuple(d["nonnegative_cols"]))
    if prep.split.fingerprint() != s["expected_fingerprint"]:
        raise RuntimeError("split differs from the pinned track-B split")
    trees = single_feature_trees(prep)
    report = {
        "scope": cfg["experiment"]["name"], "split_fingerprint": prep.split.fingerprint(),
        "data_provenance": provenance, "partition_rows": prep.report["partition_rows"],
        "note": "single-feature models fitted on train only; ranked on validation; test reported, not used for choices",
        "destination_port": port_association(prep),
        "single_feature_trees_top15": trees[:15],
        "single_feature_trees_top10_by_depth2": sorted(trees, key=lambda r: -r["depth2_val_mcc"])[:10],
        "features_with_depth1_val_mcc_above": {t: sum(r["depth1_val_mcc"] > t for r in trees) for t in (0.9, 0.95, 0.99)},
        "features_with_depth2_val_mcc_above": {t: sum(r["depth2_val_mcc"] > t for r in trees) for t in (0.9, 0.95, 0.99)},
        "port80_conditional_single_features": port80_conditional_trees(prep),
        "removal_overlap": {"Destination Port": removal_overlap(prep, [PORT])},
    }
    if args.baseline_run:
        report["baseline_errors"] = baseline_errors(prep, args.baseline_run, [t["feature"] for t in trees[:5]])
    out = args.out or ROOT / "results" / "diagnostics" / f"{cfg['experiment']['name']}-shortcuts.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("features_with_depth1_val_mcc_above", "features_with_depth2_val_mcc_above",
                                             "removal_overlap")}, indent=1, default=str))
    print("top single features, depth-1 val MCC:", [(t["feature"], t["depth1_val_mcc"]) for t in trees[:5]])
    print("top single features, depth-2 val MCC:",
          [(t["feature"], t["depth2_val_mcc"], t["depth2_test_mcc"]) for t in report["single_feature_trees_top10_by_depth2"][:5]])
    c = report["port80_conditional_single_features"]
    print("port-80 rows:", c["port80_rows"])
    print("port-80-only single features:", [(t["feature"], t["val_mcc"], t["test_mcc"], t["test_confusion"]) for t in c["top"][:5]])
    if "baseline_errors" in report:
        print("baseline test errors:", [(e["source_row"], e["y_true"], e[PORT]) for e in report["baseline_errors"]["test"]])
    print(f"saved {out.relative_to(ROOT) if out.is_relative_to(ROOT) else out.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
