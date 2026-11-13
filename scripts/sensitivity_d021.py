"""D-021 cap-200 sensitivity for the r1 fits whose autoencoder reached the 100-epoch cap.

Approved rule (docs/decision_log.md, batch-0 approvals): "AE cap of 100 epochs, with the cap-200
sensitivity where the cap is hit." The primary r1 fits that hit the cap are r1_D_s0 and r1_D_s5
(phase3_final_review/evidence/verification/verify_r1.json). This script retrains exactly those two
configurations with ae.max_epochs = 200 (configs/experiments/sensitivity/d021_r1_D_s{0,5}_cap200.yaml,
otherwise identical to the committed generated configs), under a different experiment name, in a
separate storage folder, so no primary run can be touched. It then scores each sensitivity model on

  * the frozen family-common test rows (33,038; same hash as the primary aggregate), and
  * the frozen Monday benign rows (494,940; same record and runner-identical float32 inference as
    the primary Monday scoring),

and writes one JSON record. It never aggregates with, or overwrites, the primary results.

    python scripts/sensitivity_d021.py --storage /content/sens --device cuda --out /content/sens/d021_sensitivity.json
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.evaluation.aggregate_3b import endpoint_metrics  # noqa: E402
from src.experiments.population import rows_sha256  # noqa: E402

CONFIGS = {s: ROOT / f"configs/experiments/sensitivity/d021_r1_D_s{s}_cap200.yaml" for s in (0, 5)}


def sha(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--storage", type=Path, required=True)
    p.add_argument("--device", default="cuda", choices=("cpu", "cuda"))
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--seeds", type=int, nargs="+", default=[0, 5])
    a = p.parse_args(argv)
    if a.storage.resolve() == (ROOT / "results").resolve():
        raise SystemExit("refusing to write sensitivity runs into the primary results folder")
    from src.evaluation import score_benign as SB
    from src.experiments import ae_xgb
    from src.experiments.matrix_3b import BASELINE_PREPROCESSOR, load_matrix
    matrix = load_matrix()
    pop = json.loads((ROOT / matrix["population_file"]).read_text(encoding="utf-8"))["family_common_model_visible"]
    record = json.loads(SB.RECORD.read_text(encoding="utf-8"))
    SB.check_record(record, matrix)
    monday, _ = SB.load_monday()
    monday = monday.drop(index=record["excluded_source_rows"])
    if rows_sha256(monday.index.to_numpy()) != record["kept_source_rows_sha256"]:
        raise RuntimeError("Monday rows differ from the frozen record")
    baseline_cols = json.loads((ROOT / BASELINE_PREPROCESSOR).read_text(encoding="utf-8"))["numeric_cols"]
    out = {"rule": "D-021: AE cap 100 with cap-200 sensitivity where the cap is hit", "population_test_sha256":
           pop["test_kept_source_rows_sha256"], "monday_kept_sha256": record["kept_source_rows_sha256"], "runs": {}}
    for s in a.seeds:
        cfg = ae_xgb.load_experiment(CONFIGS[s])
        if cfg["ae"]["max_epochs"] != 200 or cfg["experiment"]["name"] != "ae3b_r1_D_cap200":
            raise RuntimeError("sensitivity config is not the frozen cap-200 copy")
        entry = next(e for e in matrix["entries"] if e["id"] == f"r1_D_s{s}")
        run_dir = Path(ae_xgb.run(cfg, ae_xgb.resolve_device(a.device), a.storage))
        with gzip.open(run_dir / "predictions_test.csv.gz", "rt", encoding="utf-8") as fh:
            pred = pd.read_csv(fh)
        if rows_sha256(pred["source_row"]) != pop["test_kept_source_rows_sha256"]:
            raise RuntimeError(f"{run_dir.name}: test rows are not the family-common population")
        pre = json.loads((run_dir / "preprocessor.json").read_text(encoding="utf-8"))
        expected = [c for c in baseline_cols if c not in set(entry["drop"])]
        if pre["numeric_cols"] != expected:
            raise RuntimeError(f"{run_dir.name}: input schema differs from entry {entry['id']}")
        raw_cols = [c for c in monday.columns if c in set(pre["numeric_cols"]) | set(pre["dropped_constant_on_train"])]
        prob, sens = SB.runner_equivalent_proba(run_dir, raw_cols, monday[raw_cols].to_numpy(np.float64))
        rr = json.loads((run_dir / "run_record.json").read_text(encoding="utf-8"))
        ident = json.loads((run_dir / "identity.json").read_text(encoding="utf-8"))
        out["runs"][f"r1_D_s{s}_cap200"] = {
            "primary_entry": entry["id"], "run": run_dir.name, "config_file": str(CONFIGS[s].relative_to(ROOT)).replace("\\", "/"),
            "config_file_sha256": sha(CONFIGS[s]), "config_hash": ident["config_hash"], "git_commit": ident["git_commit"],
            "environment_fingerprint": ident["environment_fingerprint"], "device": ident["device"],
            "autoencoder": rr["autoencoder"], "xgb_best_iteration": rr["xgboost"]["best_iteration"],
            "input_dim": rr["input_dim"], "test": endpoint_metrics(pred["y_true"], pred["prob_ddos"]),
            "predictions_test_sha256": sha(run_dir / "predictions_test.csv.gz"),
            "monday": {**SB.fpr_summary(prob >= 0.5), "numerical_sensitivity": sens}}
        print(json.dumps(out["runs"][f"r1_D_s{s}_cap200"], default=float)[:600])
    a.out.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(out, indent=1, sort_keys=True, default=float) + "\n"
    a.out.write_text(text, encoding="utf-8")
    print("SENSITIVITY_SHA256", hashlib.sha256(text.encode()).hexdigest(), len(text))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
