"""R4a-i (descriptive): score the 110 r1 models (trained on ORIGINAL CICIDS2017) on the Engelen
corrected Friday test rows of R4a-ii (family-common population, 22,049 rows).

This is a descriptive transfer check, not a causal test. At least 16 of the 68 inputs change
definition between the original and the corrected extractor (docs/MILESTONE_3B0_READINESS.md §4),
so a score change mixes a covariate shift with any artifact reliance (D-024). The +5:00 clock
alignment is an empirically supported assumption, not a confirmed time-zone correction (D-005).

Inference is the runner's own float32 path (score_benign.runner_equivalent_proba), and every run
is verified first (score_benign.check_run: config hash, environment provenance, split).

  python -m src.evaluation.score_r4a_i --storage DIR --out FILE
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from src.config import ROOT

R4A_CONFIG = ROOT / "configs/experiments/ae_xgb_r4a_trackB.yaml"


def r4a_test_rows(root: Path = ROOT):
    """The R4a-ii family-common test rows (78 original-name columns) and labels, verified."""
    from src.data import ddos, engelen
    from src.experiments.ae_xgb import load_experiment
    from src.experiments.matrix_3b import load_matrix
    from src.experiments.population import load_population, lf_sha256, rows_sha256
    cfg = load_experiment(R4A_CONFIG)
    m = load_matrix(root, design="r4a")
    d, s = cfg["data"], cfg["experiment"]["split"]
    df, _ = engelen.load(root)
    prep = ddos.prepare(df, d["label_map"], tuple(s["fractions"]), s["seed"], tuple(d["nonnegative_cols"]))
    if prep.split.fingerprint() != m["split_fingerprint"]:
        raise RuntimeError("R4a split differs from the matrix")
    record = load_population(root / m["population_file"], lf_sha256(root / m["population_file"]))
    if lf_sha256(root / m["population_file"]) != m["population_sha256_lf"]:
        raise RuntimeError("R4a population record differs from the matrix")
    pop = record["family_common_model_visible"]
    rows = prep.frame.index.to_numpy()
    test = prep.split.parts()["test"]
    keep = test[~np.isin(rows[test], np.asarray(pop["test_excluded_source_rows"], dtype=np.int64))]
    if rows_sha256(rows[keep]) != pop["test_kept_source_rows_sha256"]:
        raise RuntimeError("R4a test rows differ from the population record")
    return prep.frame.iloc[keep], np.asarray(prep.y)[keep]


def class_metrics(y, prob, threshold=0.5) -> dict:
    from src.evaluation.aggregate_3b import endpoint_metrics
    out = endpoint_metrics(y, prob, threshold)
    pos, neg = int((y == 1).sum()), int((y == 0).sum())
    out["ddos_recall"] = (pos - out["fn"]) / pos if pos else float("nan")
    out["benign_fpr"] = out["fp"] / neg if neg else float("nan")
    return out


def score_all(storage: Path, root: Path = ROOT) -> dict:
    from src.evaluation.aggregate_3b import find_run
    from src.evaluation.score_benign import check_run, runner_equivalent_proba
    from src.experiments.matrix_3b import load_matrix
    frame, y = r4a_test_rows(root)
    matrix = load_matrix(root)                                   # r1: the models being transferred
    out = {"population": "R4a-ii family-common test (Engelen corrected Friday)", "n": int(len(y)),
           "n_ddos": int(y.sum()), "status": "descriptive (D-024): definitions differ for >= 16 inputs",
           "runs": {}}
    for e in matrix["entries"]:
        run_dir = find_run(storage, e)
        if run_dir is None:
            continue
        pre = check_run(run_dir, e, matrix, root)
        cols = [c for c in frame.columns if c in set(pre["numeric_cols"]) | set(pre["dropped_constant_on_train"])]
        prob, sens = runner_equivalent_proba(run_dir, cols, frame[cols].to_numpy(np.float64))
        out["runs"][e["id"]] = {"run": run_dir.name, **class_metrics(y, prob), "numerical_sensitivity": sens}
    out["n_scored"] = len(out["runs"])
    return out


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--storage", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args(argv)
    res = score_all(a.storage)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(res, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(f"R4a-i: {res['n_scored']} r1 models scored on {res['n']} corrected test rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
