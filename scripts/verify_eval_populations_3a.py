"""Milestone 3A review: evaluation-twin exclusions on RAW views versus MODEL-VISIBLE inputs.

For every pre-registered view in configs/protocol/ablation_groups_3a.yaml (read, never
regenerated), this rebuilds exactly what the AE-XGBoost runner would feed the model:
D-011 rows, pinned track-B split, the runner's TrainOnlyPreprocessor refit on the training
partition with the view's columns removed (constant-on-train removal, train-median imputation,
train min-max scaling), cast to float32. It then finds validation rows whose vector occurs in
train and test rows whose vector occurs in train or validation, on both representations.

Read-only and model-free: no model, prediction or metric is computed. Uses labels only to
report the class of excluded rows.

    .\\run.cmd scripts/verify_eval_populations_3a.py            # print the comparison
    .\\run.cmd scripts/verify_eval_populations_3a.py --write    # also write the record (refuses to overwrite)
"""
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))
from src.config import load_config, make_preprocessor  # noqa: E402
from src.data import ddos  # noqa: E402
from src.data.split import content_groups, exclude_eval_twins  # noqa: E402

R1 = "--r1" in sys.argv[1:]
TAG = "r1" if R1 else "r0"
FROZEN = root / f"configs/protocol/ablation_groups_3a{'_r1' if R1 else ''}.yaml"
CONFIG = root / "configs/experiments/ae_xgb_d008_trackB.yaml"
OUT = root / f"results/protocol/milestone3a/eval_population_3a_{TAG}.json"


def views(frozen):
    out = {"full": []}
    for name, spec in frozen["groups"].items():
        out[name] = spec["columns"]
    for name, c in frozen["controls"].items():
        for j, r in enumerate(c["random"]):
            out[f"{name}/random{j}"] = r
        out[f"{name}/matched"] = c["difficulty_matched"]
    out["D018_destination_port"] = ["Destination Port"]
    return out


def model_visible(cfg, prep, drop):
    cfg = json.loads(json.dumps(cfg))
    cfg["experiment"]["extra_drop_cols"] = list(drop)
    pre = make_preprocessor(cfg)
    parts = prep.split.parts()
    pre.fit(prep.frame.iloc[parts["train"]])
    matrix = pre.transform(prep.frame).to_numpy(dtype=np.float32)   # float32, as the runner feeds the model
    return pd.DataFrame(matrix), list(pre.output_columns), list(pre.constant_cols_)


def main():
    cfg = load_config(CONFIG)
    frozen = yaml.safe_load(FROZEN.read_text(encoding="utf-8"))
    prep = ddos.prepare(ddos.load(ddos.verified_csv(root)[0]), cfg["data"]["label_map"],
                        tuple(cfg["experiment"]["split"]["fractions"]), cfg["experiment"]["split"]["seed"],
                        tuple(cfg["data"]["nonnegative_cols"]))
    fingerprint = prep.split.fingerprint()
    assert fingerprint == cfg["experiment"]["split"]["expected_fingerprint"], fingerprint
    source_row = prep.frame.index.to_numpy()
    parts = prep.split.parts()
    rows, union = {}, {"raw": {"val": set(), "test": set()}, "model": {"val": set(), "test": set()}}
    for name, drop in views(frozen).items():
        raw_view = [c for c in prep.feature_cols if c not in drop]
        _, raw = exclude_eval_twins(content_groups(prep.frame, raw_view), prep.split)
        visible, cols, constants = model_visible(cfg, prep, drop)
        _, mod = exclude_eval_twins(content_groups(visible, list(visible.columns)), prep.split)
        rv, rt = set(raw["val_excluded_positions"]), set(raw["test_excluded_positions"])
        mv, mt = set(mod["val_excluded_positions"]), set(mod["test_excluded_positions"])
        assert rv <= mv and rt <= mt, f"{name}: raw exclusions not contained in model-visible ones"
        for rep, v, t in (("raw", rv, rt), ("model", mv, mt)):
            union[rep]["val"] |= v
            union[rep]["test"] |= t
        extra_t = sorted(mt - rt)
        rows[name] = {"dropped": len(drop), "model_inputs": len(cols), "constant_on_train": len(constants),
                      "raw_val": len(rv), "raw_test": len(rt), "model_val": len(mv), "model_test": len(mt),
                      "extra_val": len(mv - rv), "extra_test": len(extra_t),
                      "extra_test_ddos": int(prep.y[extra_t].sum()) if extra_t else 0}
        print(f"{name:40s} inputs={len(cols):2d} raw val/test {len(rv):4d}/{len(rt):4d}  "
              f"model {len(mv):4d}/{len(mt):4d}  extra {len(mv - rv)}/{len(extra_t)}")

    def summary(rep):
        v = np.array(sorted(union[rep]["val"]), dtype=int)
        t = np.array(sorted(union[rep]["test"]), dtype=int)
        keep_v = np.setdiff1d(parts["val"], v)
        keep_t = np.setdiff1d(parts["test"], t)
        return {"val_excluded": len(v), "test_excluded": len(t),
                "val_excluded_ddos": int(prep.y[v].sum()), "test_excluded_ddos": int(prep.y[t].sum()),
                "val_kept": len(keep_v), "test_kept": len(keep_t),
                "test_kept_ddos": int(prep.y[keep_t].sum()), "test_kept_benign": int(len(keep_t) - prep.y[keep_t].sum()),
                "val_excluded_source_rows": source_row[v].tolist(), "test_excluded_source_rows": source_row[t].tolist(),
                "val_kept_source_rows_sha256": hashlib.sha256(np.ascontiguousarray(source_row[keep_v]).tobytes()).hexdigest(),
                "test_kept_source_rows_sha256": hashlib.sha256(np.ascontiguousarray(source_row[keep_t]).tobytes()).hexdigest()}
    raw_s, mod_s = summary("raw"), summary("model")
    for label, s in (("raw union", raw_s), ("model-visible union", mod_s)):
        print(f"{label}: val {s['val_kept']} kept ({s['val_excluded']} excl, DDoS {s['val_excluded_ddos']}); "
              f"test {s['test_kept']} kept ({s['test_excluded']} excl, DDoS {s['test_excluded_ddos']}); "
              f"kept test DDoS {s['test_kept_ddos']} / BENIGN {s['test_kept_benign']}")
    record = {
        "milestone": f"3A review resolution: family-common population for protocol groups {TAG}",
        "frozen_groups_file": str(FROZEN.relative_to(root)).replace("\\", "/"),
        "frozen_groups_sha256_lf": hashlib.sha256(FROZEN.read_bytes().replace(b"\r\n", b"\n")).hexdigest(),
        "split_fingerprint": fingerprint,
        "representation": "model-visible: runner TrainOnlyPreprocessor refit on train per view, float32",
        "positions_are": "source_row = original CSV row index (DataFrame index after D-011 rules)",
        "n_views": len(rows), "views": rows,
        "family_common_raw_views": {k: v for k, v in raw_s.items() if not k.endswith("source_rows")},
        "family_common_model_visible": mod_s,
    }
    if "--write" in sys.argv[1:]:
        OUT.parent.mkdir(parents=True, exist_ok=True)
        with OUT.open("x", encoding="utf-8") as f:
            json.dump(record, f, indent=1)
            f.write("\n")
        print(f"wrote {OUT.relative_to(root)}")


if __name__ == "__main__":
    main()
