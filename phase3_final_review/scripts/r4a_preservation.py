"""R4a run-folder preservation status (2026-11-13), from the read-only Drive inventory.

Inputs:
  evidence/verification/r4a_drive_inventory_2026-11-13.json
      listing of the second Colab account's Drive folder cnet-r4a/ (made on a fresh Colab VM;
      JSON SHA-256 047c095d22b15986b311ad7d78c2a15514f95e01718f65551f56ff6ca093f049)
  evidence/verification/r4a_predictions_colab_check.json
      all 70 predictions re-scored on the original VM on 2026-11-12, before it expired
Output: evidence/verification/r4a_preservation_status.json

    python phase3_final_review/scripts/r4a_preservation.py
"""
from __future__ import annotations

import json
from pathlib import Path

V = Path(__file__).resolve().parents[1] / "evidence/verification"
REQ = ["DONE", "ae_done.json", "data_report.json", "effective_config.json", "identity.json", "log.txt", "metrics.json",
       "predictions_test.csv.gz", "predictions_val.csv.gz", "preprocessor.json", "run_record.json", "xgb_model.json"]


def main() -> int:
    inv = json.loads((V / "r4a_drive_inventory_2026-11-13.json").read_text(encoding="utf-8"))
    chk = json.loads((V / "r4a_predictions_colab_check.json").read_text(encoding="utf-8"))
    drive = {k.split("/", 1)[1]: v for k, v in inv.items() if k.startswith("runs/")}
    status = {}
    for run in sorted(chk):
        v = drive.get(run)
        if v is None:
            status[run] = {"state": "absent from Drive (never uploaded: quota full)"}
            continue
        missing = [f for f in REQ if f not in v["files"]]
        if missing:
            status[run] = {"state": "folder only, artefacts missing (never uploaded: quota full)", "files_present": sorted(v["files"])}
            continue
        match = bool(v.get("rows_ok") and v.get("fp") == chk[run]["fp"] and v.get("fn") == chk[run]["fn"]
                     and abs(v.get("auroc", -1) - chk[run]["auroc"]) < 1e-9)
        status[run] = {"state": "complete on Drive; predictions re-scored and equal to the verified record" if match
                       else "complete on Drive but DIFFERS from the verified record",
                       "predictions_test_sha256": v.get("pred_sha"), "checkpoint_ae_best": "checkpoints/ae_best.pt" in v["files"],
                       "n_files": len(v["files"])}
    counts = {}
    for s in status.values():
        counts[s["state"]] = counts.get(s["state"], 0) + 1
    out = {"date": "2026-11-13", "drive_folder": "second Colab account: My Drive/cnet-r4a (runs/, splits/, analysis_r4a/ empty)",
           "original_vm": "expired; its complete local copy (/content/r4a_local, 70 runs) no longer exists",
           "counts": counts, "runs": status,
           "surviving_evidence_for_all_70": ["results/r4a/aggregate_r4a.json (committed 85a2ed2)",
                                             "phase3_final_review/evidence/verification/r4a_predictions_colab_check.json (SHA-256 130da7c0...)",
                                             "results/r4a/stats_r4a.json, r4a_i_scores.json"]}
    (V / "r4a_preservation_status.json").write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(counts, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
