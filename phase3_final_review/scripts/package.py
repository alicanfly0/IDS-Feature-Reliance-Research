"""Assemble evidence/, the prediction inventory, MANIFEST.sha256 and the review ZIP; then verify it.

    python phase3_final_review/scripts/package.py
Read-only with respect to results: copies small records, never raw data, checkpoints or predictions.
"""
from __future__ import annotations

import csv
import gzip
import hashlib
import re
import shutil
import sys
import zipfile
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
REV = ROOT / "phase3_final_review"
EV = REV / "evidence"
ZIP = ROOT / "CNET_PHASE3_FINAL_EVIDENCE_REVIEW.zip"
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()

RECORDS = [
    "results/milestone3b/aggregate_r1.json", "results/milestone3b/stats_r1.json", "results/milestone3b/monday_fpr_r1.json",
    "results/milestone3b/tables_r1.md",
    "results/r4a/aggregate_r4a.json", "results/r4a/stats_r4a.json", "results/r4a/r4a_i_scores.json", "results/r4a/tables_r4a.md",
    "results/r4a/R4A_ANALYSIS_NOTES.md",
    "results/dcnn_fang/summary.json", "results/dcnn_fang/selection.json",
    *[f"results/dcnn_fang/seed{s}/metrics.json" for s in range(5)],
    "results/mes_dnn/summary.json", "results/mes_dnn/networks.json", "results/mes_dnn/superseded/README.md",
    *[f"results/mes_dnn/{m}_seed{s}/metrics.json" for m in ("random", "dup_aware") for s in range(5)],
    "results/attribution_pilot/dcnn.json", "results/attribution_pilot/mes.json",
    "results/corrections/milestone2b/corrected_arr_v2.json", "results/corrections/milestone2b/verification.json",
    "results/corrections/milestone2b/verification_2b1.json",
    "results/shap/ae_xgb_d008_trackB-seed0-cpu-565a8b9e/stability_all_variants.json",
    "results/baselines/ae_xgb_d008_trackB-seed0-cpu-565a8b9e/metrics.json",
    "results/comparisons/ae_xgb_d008_trackB_noDstPort-seed0-cpu-3054b399-vs-full.json",
    "results/diagnostics/ae_xgb_d008_trackB-shortcuts.json",
    "results/protocol/milestone3a/eval_population_3a_r1.json", "results/protocol/milestone3b/monday_population_r1.json",
    "results/protocol/milestone3b/inference_consistency_v1.json", "results/protocol/r4a/eval_population_r4a_v1.json",
    "results/protocol/r4a/r4a_feasibility_v1.json", "results/protocol/mesdnn/ton_subsample_v1.json",
    "results/colab results/batch0/SUMMARY.md", "results/colab results/session2/SUMMARY.md",
    "results/colab results/session2/preflight/env_check.json",
    "configs/protocol/ablation_groups_3a_r1.yaml", "configs/protocol/r4a_groups_v1.yaml", "configs/protocol/r4a_column_map_v1.yaml",
    "configs/environments/colab_env_v1.yaml", "configs/experiments/ae_xgb_d008_trackB.yaml", "configs/experiments/ae_xgb_r4a_trackB.yaml",
    "configs/experiments/generated/r1/matrix.json", "configs/experiments/generated/r4a/matrix.json",
    "docs/decision_log.md", "docs/MILESTONE_3A_REVIEW_RESOLUTION.md", "docs/MILESTONE_3B0_READINESS.md",
    "docs/BASELINE_ADAPTATIONS.md", "docs/MILESTONE_2B_CORRECTIONS.md", "docs/PHASE3_FINAL_COMPLETION_AUDIT.md",
    "src/evaluation/stats_3b.py", "src/evaluation/report_3b.py", "src/evaluation/report_r4a.py",
    "src/evaluation/aggregate_3b.py", "src/evaluation/score_r4a_i.py", "src/experiments/matrix_3b.py",
]
FIGS = ["paper/figures/contrasts_r1.pdf",
        *[f"results/shap/ae_xgb_d008_trackB-seed0-cpu-565a8b9e/global_importance_top20-{v}.png"
          for v in ("bg100-ex200-p10", "bg100-ex200-p5", "bg200-ex200-p5")]]
_TERMS = ["al" + "iwa", "sum" + "ayya", "@g" + "mail\\.com", "C:\\\\" + "Users", "C:/" + "Users", "gh" + "p_[A-Za-z0-9]{20}",
          "AK" + "IA[0-9A-Z]{16}", "api" + "[_-]?key", "BEGIN [A-Z ]*PRIV" + "ATE KEY"]
PERSONAL = re.compile("(" + "|".join(_TERMS) + ")", re.I)


def main() -> int:
    for sub in ("records", "existing_figures"):
        shutil.rmtree(EV / sub, ignore_errors=True)
    for r in RECORDS:
        dst = EV / "records" / r
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / r, dst)
    (EV / "existing_figures").mkdir(parents=True, exist_ok=True)
    for f in FIGS:
        shutil.copy2(ROOT / f, EV / "existing_figures" / Path(f).name)
    shutil.copy2(ROOT / "docs/PHASE3_FINAL_COMPLETION_AUDIT.md", REV / "PHASE3_EXPERIMENT_AUDIT.md")
    # prediction inventory (not packaged: paths, hashes, dimensions)
    rows = []
    for d in sorted((ROOT / "results/runs/r1_store/runs").iterdir()):
        p = d / "predictions_test.csv.gz"
        with gzip.open(p, "rt") as fh:
            lines = fh.read().splitlines()
        pos = sum(1 for ln in lines[1:] if ln.split(",")[1] == "1")
        rows.append({"family": "AE-XGBoost r1", "path": str(p.relative_to(ROOT)).replace("\\", "/"), "sha256": sha(p),
                     "rows": len(lines) - 1, "positives": pos, "columns": lines[0]})
    for s in range(5):
        p = ROOT / f"results/dcnn_fang/seed{s}/test_proba.npy"
        a = np.load(p)
        rows.append({"family": "DCNN", "path": f"results/dcnn_fang/seed{s}/test_proba.npy", "sha256": sha(p), "rows": len(a),
                     "positives": "labels rebuilt by verify_dcnn.py", "columns": "prob_dos (official test order)"})
    for m in ("random", "dup_aware"):
        for s in range(5):
            p = ROOT / f"results/mes_dnn/{m}_seed{s}/test_proba.npz"
            z = np.load(p)
            rows.append({"family": "MES-DNN", "path": f"results/mes_dnn/{m}_seed{s}/test_proba.npz", "sha256": sha(p),
                         "rows": ";".join(f"{k}={len(z[k])}" for k in z.files), "positives": "labels rebuilt by verify_mes.py",
                         "columns": ",".join(z.files)})
    rows.append({"family": "R4a-ii", "path": "Colab VM /content/r4a_local/runs/*/predictions_test.csv.gz (not in repository)",
                 "sha256": "see evidence/verification/r4a_predictions_colab_check.json (SHA-256 130da7c0...)", "rows": 22049,
                 "positives": 14168, "columns": "source_row,y_true,prob_ddos,y_pred"})
    with open(EV / "predictions_inventory.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["family", "path", "sha256", "rows", "positives", "columns"])
        w.writeheader(); w.writerows(rows)
    # hygiene scan of every text file to be packaged
    files = sorted(p for p in REV.rglob("*") if p.is_file() and p.name != "MANIFEST.sha256" and "__pycache__" not in p.parts)
    hits = []
    for p in files:
        if p.suffix.lower() in (".png", ".pdf", ".npy", ".npz", ".gz"):
            continue
        for i, line in enumerate(p.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            if PERSONAL.search(line):
                hits.append(f"{p.relative_to(REV)}:{i}: {line.strip()[:120]}")
    if hits:
        print("HYGIENE HITS:"); print("\n".join(hits[:50]))
        return 2
    man = "".join(f"{sha(p)}  {p.relative_to(REV).as_posix()}\n" for p in files)
    (REV / "MANIFEST.sha256").write_text(man, encoding="utf-8")
    files.append(REV / "MANIFEST.sha256")
    if ZIP.exists():
        ZIP.unlink()
    with zipfile.ZipFile(ZIP, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for p in files:
            zf.write(p, "phase3_final_review/" + p.relative_to(REV).as_posix())
    # verify: reopen, CRC-test, compare every file's hash with the manifest
    with zipfile.ZipFile(ZIP) as zf:
        bad = zf.testzip()
        names = zf.namelist()
        man_lines = zf.read("phase3_final_review/MANIFEST.sha256").decode().splitlines()
        mism = [ln for ln in man_lines if hashlib.sha256(zf.read("phase3_final_review/" + ln.split("  ", 1)[1])).hexdigest() != ln.split("  ", 1)[0]]
    print(f"ZIP {ZIP.name}: {ZIP.stat().st_size} bytes, {len(names)} files, sha256 {sha(ZIP)}")
    print(f"testzip: {bad}; manifest entries {len(man_lines)}; hash mismatches {len(mism)}")
    return 0 if bad is None and not mism else 1


if __name__ == "__main__":
    raise SystemExit(main())
