"""Verify the durable local copy of the surviving R4a run folders (downloaded from Drive 2026-11-13).

    python phase3_final_review/scripts/verify_r4a_local_copy.py <downloaded zip> <extract dir>

Extracts the archive (if needed), then for every run folder: lists files, hashes every file,
re-scores predictions_test.csv.gz (row hash, FP, FN, AUROC) and compares with the pre-expiry
prediction check (evidence/verification/r4a_predictions_colab_check.json).
Writes evidence/verification/r4a_local_copy_verification.json.
"""
from __future__ import annotations

import gzip
import hashlib
import json
import sys
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

V = Path(__file__).resolve().parents[1] / "evidence/verification"
POP = "4804537214604662050cabcf14dd2c53a68865fd409f35d86c897fa345ea8171"
REQ = ["DONE", "ae_done.json", "data_report.json", "effective_config.json", "identity.json", "log.txt", "metrics.json",
       "predictions_test.csv.gz", "predictions_val.csv.gz", "preprocessor.json", "run_record.json", "xgb_model.json",
       "checkpoints/ae_best.pt"]


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def main() -> int:
    zpath, dest = Path(sys.argv[1]), Path(sys.argv[2])
    zsha = sha(zpath)
    if not dest.exists():
        with zipfile.ZipFile(zpath) as zf:
            bad = zf.testzip()
            if bad:
                raise SystemExit(f"corrupt member {bad}")
            zf.extractall(dest)
    runs_root = next(p for p in dest.rglob("runs") if p.is_dir())
    chk = json.loads((V / "r4a_predictions_colab_check.json").read_text(encoding="utf-8"))
    out, problems = {}, []
    for d in sorted(p for p in runs_root.iterdir() if p.is_dir()):
        files = {str(f.relative_to(d)).replace("\\", "/"): sha(f) for f in sorted(d.rglob("*")) if f.is_file()}
        rec = {"n_files": len(files), "files_sha256": files, "missing_required": [r for r in REQ if r not in files]}
        pt = d / "predictions_test.csv.gz"
        if pt.is_file():
            with gzip.open(pt, "rt", encoding="utf-8") as fh:
                q = pd.read_csv(fh)
            y, pr = q["y_true"].to_numpy(int), q["prob_ddos"].to_numpy(float)
            yp = (pr >= 0.5).astype(int)
            rows = hashlib.sha256(np.ascontiguousarray(q["source_row"].to_numpy(np.int64)).tobytes()).hexdigest()
            rec.update(rows_ok=rows == POP, fp=int(((yp == 1) & (y == 0)).sum()), fn=int(((yp == 0) & (y == 1)).sum()),
                       auroc=float(roc_auc_score(y, pr)))
            c = chk.get(d.name)
            rec["matches_pre_expiry_check"] = bool(c and rec["rows_ok"] and c["fp"] == rec["fp"] and c["fn"] == rec["fn"]
                                                   and abs(c["auroc"] - rec["auroc"]) < 1e-9)
            if not rec["matches_pre_expiry_check"]:
                problems.append(f"{d.name}: differs from the pre-expiry check")
        out[d.name] = rec
    complete = [k for k, v in out.items() if not v["missing_required"] and v.get("matches_pre_expiry_check")]
    res = {"archive": zpath.name, "archive_sha256": zsha, "archive_bytes": zpath.stat().st_size,
           "extracted_to": str(dest.relative_to(Path.cwd())).replace("\\", "/") if dest.is_relative_to(Path.cwd()) else dest.name,
           "run_folders": len(out), "complete_and_matching": len(complete), "complete_runs": complete, "problems": problems, "runs": out}
    (V / "r4a_local_copy_verification.json").write_text(json.dumps(res, indent=1) + "\n", encoding="utf-8")
    print(f"archive sha256 {zsha}; folders {len(out)}; complete & matching {len(complete)}; problems {len(problems)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
