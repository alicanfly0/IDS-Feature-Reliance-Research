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
