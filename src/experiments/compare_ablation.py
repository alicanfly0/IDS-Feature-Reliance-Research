"""Compare a feature-removal run with the full-feature run on one common test population.

    python -m src.experiments.compare_ablation \
        --full results/runs/ae_xgb_d008_trackB-seed0-cpu-565a8b9e \
        --ablated results/runs/<ablation run id>

Both runs must be complete and share the pinned split, dataset hashes and model seed. The
common population is the ablated run's test set (the original test set minus rows whose
reduced-feature vector duplicates train/validation); the full model is scored on the same
rows from its saved predictions, so it is not retrained. Paired differences are reported as
discordant counts with an exact two-sided McNemar test (one seed: descriptive evidence).
"""
from __future__ import annotations

import argparse
import json
from math import comb
from pathlib import Path

import pandas as pd

from src.config import ROOT
from src.evaluation.metrics import binary_metrics

KEYS = ("accuracy", "precision", "recall", "f1", "macro_f1", "auroc", "mcc")


def _load(run_dir: Path) -> dict:
    if not (run_dir / "DONE").is_file():
        raise RuntimeError(f"{run_dir.name} is not complete")
    read = lambda name: json.loads((run_dir / name).read_text(encoding="utf-8"))
    return {"record": read("run_record.json"), "config": read("effective_config.json"),
            "data": read("data_report.json"), "test": pd.read_csv(run_dir / "predictions_test.csv.gz")}


def mcnemar_exact(b: int, c: int) -> float:
    """Two-sided exact McNemar p-value for discordant counts b and c."""
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    return min(1.0, 2 * sum(comb(n, i) for i in range(k + 1)) / 2 ** n)


def compare(full_dir: Path, ablated_dir: Path) -> dict:
    full, abl = _load(full_dir), _load(ablated_dir)
    fr, ar = full["record"], abl["record"]
    for key, a, b in (("split_fingerprint", fr["split_fingerprint"], ar["split_fingerprint"]),
                      ("dataset_sha256", fr["identity"]["dataset_sha256"], ar["identity"]["dataset_sha256"]),
                      ("model_seed", full["config"]["run"]["model_seed"], abl["config"]["run"]["model_seed"])):
        if a != b:
            raise RuntimeError(f"runs are not comparable: {key} differs")
    t_full, t_abl = full["test"].set_index("source_row"), abl["test"].set_index("source_row")
    if not t_abl.index.isin(t_full.index).all():
        raise RuntimeError("ablated test rows are not a subset of the full run's test rows")
    common = t_abl.index
    if not (t_full.loc[common, "y_true"] == t_abl["y_true"]).all():
        raise RuntimeError("labels differ between runs")
    y = t_abl["y_true"].to_numpy()
    thr = full["config"]["run"]["threshold"]
    m_full_all = binary_metrics(t_full["y_true"], t_full["prob_ddos"], thr)
    m_full = binary_metrics(y, t_full.loc[common, "prob_ddos"], thr)
    m_abl = binary_metrics(y, t_abl["prob_ddos"], thr)
    ok_full = t_full.loc[common, "y_pred"].to_numpy() == y
    ok_abl = t_abl["y_pred"].to_numpy() == y
    b, c = int((ok_full & ~ok_abl).sum()), int((~ok_full & ok_abl).sum())
    excluded = abl["data"].get("eval_twin_exclusion", {})
    return {
        "full_run": fr["identity"]["run_id"], "ablated_run": ar["identity"]["run_id"],
        "split_fingerprint": fr["split_fingerprint"],
        "input_dim": {"full": fr["input_dim"], "ablated": ar["input_dim"]},
        "excluded_from_ablated_evaluation": {k: excluded.get(k) for k in ("val_excluded", "test_excluded")},
        "common_test_rows": int(len(common)), "full_test_rows": int(len(t_full)),
        "full_on_full_test": {k: m_full_all[k] for k in KEYS} | {"confusion_matrix": m_full_all["confusion_matrix"]},
        "full_on_common": {k: m_full[k] for k in KEYS} | {"confusion_matrix": m_full["confusion_matrix"]},
        "ablated_on_common": {k: m_abl[k] for k in KEYS} | {"confusion_matrix": m_abl["confusion_matrix"]},
        "delta_ablated_minus_full": {k: m_abl[k] - m_full[k] for k in KEYS},
        "paired": {"both_correct": int((ok_full & ok_abl).sum()), "only_full_correct": b,
                   "only_ablated_correct": c, "both_wrong": int((~ok_full & ~ok_abl).sum()),
                   "mcnemar_exact_p": mcnemar_exact(b, c)},
        "note": "single model seed; descriptive. Same training rows, labels, split and settings except the removed feature.",
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--full", required=True, type=Path)
    parser.add_argument("--ablated", required=True, type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)
    result = compare(args.full, args.ablated)
    out = args.out or ROOT / "results" / "comparisons" / f"{result['ablated_run']}-vs-full.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
