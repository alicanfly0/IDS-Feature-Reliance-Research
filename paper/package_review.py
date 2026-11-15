"""Build CNET_PHASE4_SUBMISSION_READY.zip (paper, sources, QA documents and the records the numbers come from).

    .\.venv\Scripts\python.exe paper\package_review.py

Files keep their repository-relative paths inside the archive, so every path in
PAPER_CLAIM_EVIDENCE_MAP.md resolves. The archive is re-opened and checked after writing.
"""
from __future__ import annotations

import hashlib
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "CNET_PHASE4_SUBMISSION_READY.zip"

FILES = [
    "paper/CNET_PhaseIV_Research_Paper.pdf",
    "paper/main.tex",
    "paper/references.bib",
    "paper/README.md",
    "paper/FINAL_PAPER_QA.md",
    "paper/PAPER_CLAIM_EVIDENCE_MAP.md",
    "paper/BUILD_LOG.md",
    "paper/CHANGELOG_UPDATED_RUBRIC.md",
    "paper/CHANGELOG_FINAL.md",
    "paper/FINAL_PRINT_QA.md",
    "paper/main.log",
    "paper/main.blg",
    "paper/package_review.py",
    "paper/figures/make_paper_figures.py",
    "paper/tables/make_tables.py",
    # evidence the paper's numbers come from
    "phase3_final_review/PHASE3_STATISTICAL_FINDINGS.csv",
    "phase3_final_review/evidence/verification/verify_r1.json",
    "phase3_final_review/evidence/verification/verify_r4a.json",
    "phase3_final_review/evidence/verification/verify_dcnn.json",
    "phase3_final_review/evidence/verification/verify_mes.json",
    "phase3_final_review/evidence/verification/d021_sensitivity.json",
    "phase3_final_review/evidence/verification/d021_comparison.json",
    "phase3_final_review/evidence/verification/r4a_preservation_status.json",
    "results/r4a/stats_r4a.json",
    "results/corrections/milestone2b/corrected_arr_v2.json",
    "docs/evidence/engelen_extended_2026-11-09.md",
    # frozen protocol files cited in Appendix B
    "configs/protocol/ablation_groups_3a_r1.yaml",
    "configs/protocol/r4a_groups_v1.yaml",
    "configs/experiments/ae_xgb_d008_trackB.yaml",
    "configs/experiments/ae_xgb_r4a_trackB.yaml",
]
FILES += sorted(str(p.relative_to(ROOT)).replace("\\", "/") for p in (ROOT / "paper/figures").glob("diag_*.tex"))
FILES += sorted(str(p.relative_to(ROOT)).replace("\\", "/") for p in (ROOT / "paper/figures").glob("fig_*.pdf"))
FILES += sorted(str(p.relative_to(ROOT)).replace("\\", "/") for p in (ROOT / "paper/tables").glob("tab_*.tex"))

sha = lambda b: hashlib.sha256(b).hexdigest()
manifest = []
with zipfile.ZipFile(OUT, "w", compression=zipfile.ZIP_DEFLATED) as z:
    for rel in FILES:
        data = (ROOT / rel).read_bytes()
        z.writestr(rel, data)
        manifest.append(f"{sha(data)}  {rel}")
    # Submission copy at the top level, identical to paper/CNET_PhaseIV_Research_Paper.pdf.
    pdf = (ROOT / "paper/CNET_PhaseIV_Research_Paper.pdf").read_bytes()
    z.writestr("CNET_PhaseIV_Research_Paper.pdf", pdf)
    manifest.append(f"{sha(pdf)}  CNET_PhaseIV_Research_Paper.pdf")
    z.writestr("MANIFEST.sha256", "\n".join(manifest) + "\n")

with zipfile.ZipFile(OUT) as z:
    assert z.testzip() is None, "corrupt member"
    lines = z.read("MANIFEST.sha256").decode().splitlines()
    for line in lines:
        digest, rel = line.split("  ", 1)
        assert sha(z.read(rel)) == digest, rel
    print(f"members: {len(z.namelist())} ({len(lines)} files + manifest), all hashes match")
print(f"size: {OUT.stat().st_size:,} bytes")
print(f"sha256: {sha(OUT.read_bytes())}")
