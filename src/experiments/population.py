"""Family-common evaluation population for Milestone 3B (protocol r1).

Every 3B model, full or ablated, trains on the same training rows, early-stops on the same
validation rows and is scored on the same test rows. Those rows come from a validated,
committed record (results/protocol/milestone3a/eval_population_3a_r1.json, produced by
scripts/verify_eval_populations_3a.py on the float32 model-visible inputs).

`apply_population` refuses to continue if:
- the record file's hash differs from the config's expected hash;
- the record was made for a different split;
- this run's own feature view has evaluation twins the record does not exclude;
- the kept validation/test rows differ from the record (hash check), i.e. the rows are not
  identical across models.
The runner's float32 overlap guard (ae_xgb.preprocess) still runs afterwards.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np

from src.data.split import Split, content_groups, exclude_eval_twins


def lf_sha256(path: Path) -> str:
    """SHA-256 of the file with CRLF normalised to LF (Git may check text files out with CRLF)."""
    return hashlib.sha256(Path(path).read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def rows_sha256(rows) -> str:
    return hashlib.sha256(np.ascontiguousarray(np.asarray(rows, dtype=np.int64)).tobytes()).hexdigest()


def load_population(path: Path, expected_sha256: str) -> dict:
    path = Path(path)
    actual = lf_sha256(path)
    if actual != expected_sha256:
        raise RuntimeError(f"population record {path.name} hash {actual[:12]} != expected {expected_sha256[:12]}")
    record = json.loads(path.read_text(encoding="utf-8"))
    pop = record.get("family_common_model_visible")
    if not pop or "val_excluded_source_rows" not in pop:
        raise ValueError(f"{path.name} is not a family-common population record")
    return record


def apply_population(prep, record: dict, view_cols: list[str]):
    """Return (reduced split, report). `prep` is the ddos.Prepared object after the pinned split."""
    if record["split_fingerprint"] != prep.split.fingerprint():
        raise RuntimeError("population record was made for a different split")
    pop = record["family_common_model_visible"]
    rows = prep.frame.index.to_numpy()
    parts = prep.split.parts()
    excl_val = np.asarray(pop["val_excluded_source_rows"], dtype=np.int64)
    excl_test = np.asarray(pop["test_excluded_source_rows"], dtype=np.int64)
    # This view's own twins (raw view; equal to model-visible for every r1 view, recorded) must be covered.
    _, own = exclude_eval_twins(content_groups(prep.frame, view_cols), prep.split)
    missing_val = set(rows[own["val_excluded_positions"]].tolist()) - set(excl_val.tolist())
    missing_test = set(rows[own["test_excluded_positions"]].tolist()) - set(excl_test.tolist())
    if missing_val or missing_test:
        raise RuntimeError(f"feature view not covered by the population record: {len(missing_val)} validation and "
                           f"{len(missing_test)} test twins are not excluded")
    keep_val = parts["val"][~np.isin(rows[parts["val"]], excl_val)]
    keep_test = parts["test"][~np.isin(rows[parts["test"]], excl_test)]
    for name, keep, key in (("validation", keep_val, "val_kept_source_rows_sha256"),
                            ("test", keep_test, "test_kept_source_rows_sha256")):
        if rows_sha256(rows[keep]) != pop[key]:
            raise RuntimeError(f"kept {name} rows differ from the population record")
    reduced = Split(parts["train"], keep_val, keep_test, f"{prep.split.strategy}+family_common",
                    prep.split.seed, {**prep.split.params, "base_fingerprint": prep.split.fingerprint()})
    report = {"record_milestone": record.get("milestone"), "val_kept": int(len(keep_val)), "test_kept": int(len(keep_test)),
              "val_excluded": int(len(parts["val"]) - len(keep_val)), "test_excluded": int(len(parts["test"]) - len(keep_test)),
              "own_view_twins": {"val": own["val_excluded"], "test": own["test_excluded"]},
              "test_kept_source_rows_sha256": pop["test_kept_source_rows_sha256"]}
    return reduced, report


def verify(root: Path | None = None) -> dict:
    """Recompute the pinned split and the r1 family-common population from the data (no model)."""
    from src.config import ROOT, load_config
    from src.data import ddos
    from src.experiments.matrix_3b import BASE_CONFIG, POPULATION_FILE
    root = Path(root) if root is not None else ROOT
    cfg = load_config(root / BASE_CONFIG)
    csv, provenance = ddos.verified_csv(root)
    prep = ddos.prepare(ddos.load(csv), cfg["data"]["label_map"], tuple(cfg["experiment"]["split"]["fractions"]),
                        cfg["experiment"]["split"]["seed"], tuple(cfg["data"]["nonnegative_cols"]))
    expected = cfg["experiment"]["split"]["expected_fingerprint"]
    record_path = root / POPULATION_FILE
    record = load_population(record_path, lf_sha256(record_path))
    split, rep = apply_population(prep, record, prep.feature_cols)          # full view; refuses on any mismatch
    rows = prep.frame.index.to_numpy()
    out = {"split_fingerprint": prep.split.fingerprint(), "expected_split_fingerprint": expected,
           "split_matches": prep.split.fingerprint() == expected, "population_record": POPULATION_FILE,
           "population_record_sha256_lf": lf_sha256(record_path), **rep,
           "val_kept_matches": rows_sha256(rows[split.val]) == record["family_common_model_visible"]["val_kept_source_rows_sha256"],
           "test_kept_matches": rows_sha256(rows[split.test]) == record["family_common_model_visible"]["test_kept_source_rows_sha256"],
           "data_provenance": provenance}
    if not (out["split_matches"] and out["val_kept_matches"] and out["test_kept_matches"]):
        raise RuntimeError(f"split or population does not reproduce: {out}")
    return out


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(description="Verify the pinned split and the family-common population (no model).")
    p.add_argument("command", choices=("verify",))
    p.add_argument("--json", type=Path)
    a = p.parse_args()
    result = verify()
    if a.json:
        a.json.parent.mkdir(parents=True, exist_ok=True)
        a.json.write_text(json.dumps(result, indent=1) + "\n", encoding="utf-8")
    print(f"split {result['split_fingerprint'][:16]} OK; family-common val {result['val_kept']} / test {result['test_kept']} OK")


def compute_family_common(cfg: dict, prep, views: dict[str, list[str]]) -> dict:
    """Evaluation-twin exclusions for every view, on raw columns AND on the runner's float32
    model-visible inputs (train-only preprocessing refit per view); the union defines one common
    validation/test population. Read-only; no model. Used for R4a-ii (D-005)."""
    import pandas as pd
    from src.config import make_preprocessor
    parts = prep.split.parts()
    rows = prep.frame.index.to_numpy()
    per_view, union_v, union_t = {}, set(), set()
    for name, drop in views.items():
        raw_view = [c for c in prep.feature_cols if c not in drop]
        _, raw = exclude_eval_twins(content_groups(prep.frame, raw_view), prep.split)
        c = json.loads(json.dumps(cfg))
        c["experiment"]["extra_drop_cols"] = list(drop)
        pre = make_preprocessor(c)
        pre.fit(prep.frame.iloc[parts["train"]])
        visible = pd.DataFrame(pre.transform(prep.frame).to_numpy(dtype=np.float32))
        _, mod = exclude_eval_twins(content_groups(visible, list(visible.columns)), prep.split)
        rv, rt = set(raw["val_excluded_positions"]), set(raw["test_excluded_positions"])
        mv, mt = set(mod["val_excluded_positions"]), set(mod["test_excluded_positions"])
        if not (rv <= mv and rt <= mt):
            raise AssertionError(f"{name}: raw exclusions not contained in model-visible ones")
        per_view[name] = {"dropped": len(drop), "model_inputs": len(pre.output_columns), "raw_val": len(rv),
                          "raw_test": len(rt), "model_val": len(mv), "model_test": len(mt),
                          "extra_val": len(mv - rv), "extra_test": len(mt - rt)}
        union_v |= mv
        union_t |= mt
    v = np.array(sorted(union_v), dtype=int)
    t = np.array(sorted(union_t), dtype=int)
    keep_v, keep_t = np.setdiff1d(parts["val"], v), np.setdiff1d(parts["test"], t)
    y = prep.y
    pop = {"val_excluded": len(v), "test_excluded": len(t), "val_excluded_ddos": int(y[v].sum()) if len(v) else 0,
           "test_excluded_ddos": int(y[t].sum()) if len(t) else 0, "val_kept": len(keep_v), "test_kept": len(keep_t),
           "test_kept_ddos": int(y[keep_t].sum()), "test_kept_benign": int(len(keep_t) - y[keep_t].sum()),
           "val_excluded_source_rows": rows[v].tolist(), "test_excluded_source_rows": rows[t].tolist(),
           "val_kept_source_rows_sha256": rows_sha256(rows[keep_v]), "test_kept_source_rows_sha256": rows_sha256(rows[keep_t])}
    return {"n_views": len(views), "views": per_view, "split_fingerprint": prep.split.fingerprint(),
            "representation": "model-visible: runner TrainOnlyPreprocessor refit on train per view, float32",
            "positions_are": "source_row = row index in the corrected Friday CSV", "family_common_model_visible": pop}
