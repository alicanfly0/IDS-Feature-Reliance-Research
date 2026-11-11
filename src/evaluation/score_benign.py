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


def protocol_views(groups: dict) -> dict[str, list[str]]:
    """Every pre-registered input view of a groups file (full, groups, controls, D-018 port)."""
    views = {"full": []}
    for g, spec in groups["groups"].items():
        views[g] = spec["columns"]
    for g, c in groups["controls"].items():
        views.update({f"{g}/random{j}": r for j, r in enumerate(c["random"])})
        views[f"{g}/matched"] = c["difficulty_matched"]
    views["D018_destination_port"] = ["Destination Port"]
    return views


def write_exclusions(root: Path = ROOT) -> dict:
    """Data-only: no model is loaded or scored."""
    import yaml
    from src.config import load_config
    from src.data import ddos
    from src.experiments.matrix_3b import BASE_CONFIG, GROUPS_FILE
    cfg = load_config(root / BASE_CONFIG)
    prep = ddos.prepare(ddos.load(ddos.verified_csv(root)[0]), cfg["data"]["label_map"])
    views = protocol_views(yaml.safe_load((root / GROUPS_FILE).read_text(encoding="utf-8")))
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


REQUIRED_ARTIFACTS = ("DONE", "identity.json", "effective_config.json", "preprocessor.json", "run_record.json",
                      "data_report.json", "checkpoints/ae_best.pt", "xgb_model.json")
INFERENCE = "runner-identical: train-only preprocessing -> float32 -> ae.encode (batch 8192) -> XGBoost predict_proba"


def check_record(record: dict, matrix: dict, root: Path = ROOT) -> None:
    """Fail closed unless the Monday record belongs to the committed r1 matrix and split."""
    import yaml
    from src.experiments.matrix_3b import GROUPS_FILE
    groups_sha = lf_sha256(root / GROUPS_FILE)
    if record.get("groups_file") != GROUPS_FILE or record.get("groups_sha256_lf") != groups_sha \
            or groups_sha != matrix["groups_sha256_lf"]:
        raise RuntimeError("Monday record groups file/hash does not match the committed r1 matrix")
    if record.get("split_fingerprint") != matrix["split_fingerprint"]:
        raise RuntimeError("Monday record was made for a different split")
    views = protocol_views(yaml.safe_load((root / GROUPS_FILE).read_text(encoding="utf-8")))
    if record.get("n_views") != len(views) or set(record.get("per_view_training_twins", {})) != set(views):
        raise RuntimeError("Monday record does not cover exactly the r1 views")
    if record.get("kept", -1) != record.get("rows_after_rules", -2) - len(record.get("excluded_source_rows", [])):
        raise RuntimeError("Monday record counts are inconsistent")


def check_run(run_dir: Path, entry: dict, matrix: dict, root: Path = ROOT) -> dict:
    """Fail closed unless `run_dir` is a complete run of exactly this matrix entry on the protocol population."""
    from src.evaluation.aggregate_3b import _check_config
    run_dir = Path(run_dir)
    missing = [a for a in REQUIRED_ARTIFACTS if not (run_dir / a).is_file()]
    if missing:
        raise RuntimeError(f"{run_dir.name}: missing saved artifacts {missing}")
    _check_config(run_dir, entry, root)                                     # config hash = committed entry
    record = json.loads((run_dir / "run_record.json").read_text(encoding="utf-8"))
    if record.get("split_fingerprint") != matrix["split_fingerprint"]:
        raise RuntimeError(f"{run_dir.name}: trained on a different split")
    population = json.loads((root / matrix["population_file"]).read_text(encoding="utf-8"))
    used = json.loads((run_dir / "data_report.json").read_text(encoding="utf-8")).get("family_common_population", {})
    if used.get("test_kept_source_rows_sha256") != population["family_common_model_visible"]["test_kept_source_rows_sha256"]:
        raise RuntimeError(f"{run_dir.name}: not evaluated on the family-common population")
    pre = json.loads((run_dir / "preprocessor.json").read_text(encoding="utf-8"))
    from src.experiments.matrix_3b import BASELINE_PREPROCESSOR
    baseline = json.loads((root / BASELINE_PREPROCESSOR).read_text(encoding="utf-8"))["numeric_cols"]
    expected = [c for c in baseline if c not in set(entry["drop"])]
    if pre["numeric_cols"] != expected or pre["input_dim"] != len(expected) or not set(entry["drop"]) <= set(pre["dropped_by_name"]):
        raise RuntimeError(f"{run_dir.name}: input schema does not match entry {entry['id']}")
    return pre


def runner_equivalent_proba(run_dir: Path, raw_cols: list[str], raw: np.ndarray) -> tuple[np.ndarray, dict]:
    """The runner's own float32 inference (verified bitwise against saved test predictions,
    results/protocol/milestone3b/inference_consistency_v1.json), plus a batch-size sensitivity."""
    import torch
    from src.audit.composite import CompositeModel
    from src.models import autoencoder as ae
    from src.models import xgb as xgbm
    run_dir = Path(run_dir)
    cm = CompositeModel(run_dir, raw_cols, precision="float32")
    x32 = cm.transform(raw)
    model = ae.build(x32.shape[1], json.loads((run_dir / "effective_config.json").read_text(encoding="utf-8"))["ae"])
    model.load_state_dict(torch.load(run_dir / "checkpoints" / "ae_best.pt", map_location="cpu", weights_only=True))
    z = ae.encode(model, x32, "cpu")                                       # runner default batch (8192), CPU
    clf = xgbm.load(run_dir / "xgb_model.json")
    prob = xgbm.predict_positive(clf, z).astype(np.float64)
    margin = clf.predict(z, output_margin=True).astype(np.float64)
    alt = CompositeModel(run_dir, raw_cols, batch=65536, precision="float32").margin(raw)
    sensitivity = {"alt_batch": 65536, "max_abs_margin_diff": float(np.max(np.abs(alt - margin))) if len(raw) else 0.0,
                   "threshold_crossings": int(((alt >= 0) != (margin >= 0)).sum())}
    return prob, sensitivity


def score_run(run_dir: Path, entry: dict, matrix: dict, monday: pd.DataFrame, record: dict,
              threshold: float = 0.5, root: Path = ROOT) -> dict:
    """FPR of one verified run on the recorded Monday rows (runner-identical float32 inference)."""
    if rows_sha256(monday.index.to_numpy()) != record["kept_source_rows_sha256"]:
        raise RuntimeError("Monday rows differ from the recorded population")
    pre = check_run(run_dir, entry, matrix, root)
    raw_cols = [c for c in monday.columns if c in set(pre["numeric_cols"]) | set(pre["dropped_constant_on_train"])]
    prob, sensitivity = runner_equivalent_proba(Path(run_dir), raw_cols, monday[raw_cols].to_numpy(np.float64))
    return {"run": Path(run_dir).name, "entry": entry["id"], "inference": INFERENCE, **fpr_summary(prob >= threshold),
            "numerical_sensitivity": sensitivity}


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
    matrix = load_matrix()                                     # refuses changed protocol files
    record = json.loads(RECORD.read_text(encoding="utf-8"))
    check_record(record, matrix)
    monday, _ = load_monday()
    monday = monday.drop(index=record["excluded_source_rows"])
    out = {}
    for e in matrix["entries"]:
        run_dir = find_run(a.storage, e)
        if run_dir is not None:
            out[e["id"]] = score_run(run_dir, e, matrix, monday, record)
    print(json.dumps(out, indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
