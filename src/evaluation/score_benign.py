"""Monday benign false-positive scoring for Milestone 3B (protocol r1, PROPOSED).

    python -m src.evaluation.score_benign exclusions --write        # data-only: Monday rows + twin record
    python -m src.evaluation.score_benign score --storage DIR       # scores completed matrix runs (not run yet)

Monday (MachineLearningCVE/Monday-WorkingHours.pcap_ISCX.csv) is entirely BENIGN, so it measures
false positives only, never recall. Rows identical to any TRAINING vector in any pre-registered
model-visible view (float32, train-only preprocessing per view) are excluded once, for every
model, so all models are scored on the same Monday rows.

The sealed Tuesday-Thursday reserve deliberately has no scorer: it may be opened only once,
after the analysis of everything else is frozen (protocol D-023).
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from src.config import ROOT
from src.evaluation.stats_3b import clopper_pearson
from src.experiments.population import lf_sha256, rows_sha256

MONDAY = "MachineLearningCVE/Monday-WorkingHours.pcap_ISCX.csv"
RECORD = ROOT / "results/protocol/milestone3b/monday_population_r1.json"


def load_monday(root: Path = ROOT):
    from src.data import ddos
    from src.data.preprocess import invalid_row_mask
    csv, provenance = ddos.verified_csv(root, member=MONDAY)
    df = ddos.load(csv)
    labels = set(df["Label"].astype(str).str.strip())
    if labels != {"BENIGN"}:
        raise RuntimeError(f"Monday is expected to be all BENIGN, found {sorted(labels)}")
    invalid = invalid_row_mask(df, nonnegative_cols=("Flow Duration",)).any(axis=1).to_numpy()
    return df.loc[~invalid], {**provenance, "raw_rows": int(len(df)), "invalid_rows_excluded": int(invalid.sum())}


def _row_keys(matrix: np.ndarray) -> np.ndarray:
    a = np.ascontiguousarray(matrix.astype(np.float32) + np.float32(0.0))   # -0.0 -> 0.0
    return a.view(np.dtype((np.void, a.dtype.itemsize * a.shape[1]))).ravel()


def training_twin_mask(cfg: dict, prep, views: dict[str, list[str]], frame: pd.DataFrame) -> tuple[np.ndarray, dict]:
    """True for rows of `frame` whose model-visible vector equals a training vector in ANY view."""
    from src.config import make_preprocessor
    train = prep.frame.iloc[prep.split.parts()["train"]]
    union = np.zeros(len(frame), bool)
    per_view = {}
    for name, drop in views.items():
        c = json.loads(json.dumps(cfg))
        c["experiment"]["extra_drop_cols"] = list(drop)
        pre = make_preprocessor(c)
        pre.fit(train)
        seen = _row_keys(pre.transform(train).to_numpy(np.float32))
        hit = np.isin(_row_keys(pre.transform(frame).to_numpy(np.float32)), seen)
        per_view[name] = int(hit.sum())
        union |= hit
    return union, per_view


def write_exclusions(root: Path = ROOT) -> dict:
    """Data-only: no model is loaded or scored."""
    import yaml
    from src.config import load_config
    from src.data import ddos
    from src.experiments.matrix_3b import BASE_CONFIG, GROUPS_FILE
    cfg = load_config(root / BASE_CONFIG)
    prep = ddos.prepare(ddos.load(ddos.verified_csv(root)[0]), cfg["data"]["label_map"])
    groups = yaml.safe_load((root / GROUPS_FILE).read_text(encoding="utf-8"))
    views = {"full": []}
    for g, spec in groups["groups"].items():
        views[g] = spec["columns"]
    for g, c in groups["controls"].items():
        views.update({f"{g}/random{j}": r for j, r in enumerate(c["random"])})
        views[f"{g}/matched"] = c["difficulty_matched"]
    views["D018_destination_port"] = ["Destination Port"]
    monday, provenance = load_monday(root)
    mask, per_view = training_twin_mask(cfg, prep, views, monday)
    kept = monday.index.to_numpy()[~mask]
    record = {"population": "Monday BENIGN (model-untouched); false positives only", "groups_file": GROUPS_FILE,
              "groups_sha256_lf": lf_sha256(root / GROUPS_FILE), "split_fingerprint": prep.split.fingerprint(),
              "provenance": provenance, "n_views": len(views), "per_view_training_twins": per_view,
              "rows_after_rules": int(len(monday)), "excluded_training_twins": int(mask.sum()), "kept": int(len(kept)),
              "kept_source_rows_sha256": rows_sha256(kept), "excluded_source_rows": monday.index.to_numpy()[mask].tolist()}
    RECORD.parent.mkdir(parents=True, exist_ok=True)
    with RECORD.open("x", encoding="utf-8") as f:
        json.dump(record, f, indent=1)
        f.write("\n")
    return record


def fpr_summary(pred: np.ndarray) -> dict:
    pred = np.asarray(pred, int)
    k, n = int(pred.sum()), int(len(pred))
    lo, hi = clopper_pearson(k, n)
    return {"n": n, "false_positives": k, "fpr": k / n, "clopper_pearson_95": [lo, hi]}


def score_run(run_dir: Path, monday: pd.DataFrame, record: dict, threshold: float = 0.5) -> dict:
    """FPR of one completed run on the recorded Monday rows (float32, as the run's own evaluation)."""
    from src.audit.composite import CompositeModel
    if rows_sha256(monday.index.to_numpy()) != record["kept_source_rows_sha256"]:
        raise RuntimeError("Monday rows differ from the recorded population")
    pre = json.loads((Path(run_dir) / "preprocessor.json").read_text(encoding="utf-8"))
    raw_cols = [c for c in monday.columns if c in set(pre["numeric_cols"]) | set(pre["dropped_constant_on_train"])]
    model = CompositeModel(Path(run_dir), raw_cols, precision="float32")
    prob = model.proba(monday[raw_cols].to_numpy(np.float64))
    return {"run": Path(run_dir).name, **fpr_summary(prob >= threshold)}


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("command", choices=("exclusions", "score"))
    p.add_argument("--write", action="store_true")
    p.add_argument("--storage", type=Path)
    a = p.parse_args(argv)
    if a.command == "exclusions":
        if not a.write:
            p.error("exclusions needs --write (it refuses to overwrite an existing record)")
        r = write_exclusions()
        print(f"Monday: {r['rows_after_rules']} rows, {r['excluded_training_twins']} training twins excluded, {r['kept']} kept")
        return 0
    from src.evaluation.aggregate_3b import find_run
    from src.experiments.matrix_3b import load_matrix
    record = json.loads(RECORD.read_text(encoding="utf-8"))
    monday, _ = load_monday()
    monday = monday.drop(index=record["excluded_source_rows"])
    out = {}
    for e in load_matrix()["entries"]:
        run_dir = find_run(a.storage, e)
        if run_dir is not None:
            out[e["id"]] = score_run(run_dir, monday, record)
    print(json.dumps(out, indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
