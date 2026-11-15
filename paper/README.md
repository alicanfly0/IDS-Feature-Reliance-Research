# Phase IV paper

"How Real Is 99% Accuracy? Auditing Feature Reliance in Network Intrusion Detection", the final CNET paper by Ali Waseem Abbasi and Muhammad Mudassir. IEEEtran journal format, two columns, 15 pages (revised on 2026-11-15 for the updated Phase IV rubric; see `CHANGELOG_UPDATED_RUBRIC.md`).

## Files

| Path | What it is |
|---|---|
| `main.tex` | Manuscript source. Every number carries a `%` comment naming its record. |
| `references.bib` | Bibliography (20 entries, all cited). |
| `CNET_PhaseIV_Research_Paper.pdf` | Compiled paper. |
| `figures/diag_framework.tex`, `diag_aexgb.tex`, `diag_dcnn.tex`, `diag_mes.tex`, `diag_protocol.tex` | Figs. 1–5, editable TikZ sources, compiled with the paper. |
| `figures/fig_*.pdf` | Figs. 6–12, vector plots. |
| `figures/make_paper_figures.py` | Regenerates the seven plots from the verified records. |
| `tables/tab_*.tex` | Result tables V–VIII, X, XI and XIII. Tables I–IV, IX, XII and XIV are written in `main.tex`. |
| `CHANGELOG_UPDATED_RUBRIC.md` | M1–M9 corrections with PDF pages, and the 14-part rubric check. |
| `tables/make_tables.py` | Regenerates those tables from the verified records. |
| `PAPER_CLAIM_EVIDENCE_MAP.md` | Each claim, its value and its source record. |
| `FINAL_PAPER_QA.md` | Compile status, page-by-page visual check, claim validation and items for the authors. |
| `BUILD_LOG.md`, `main.log`, `main.blg` | Build record and the LaTeX and BibTeX logs. |

Older files kept for history and not used by the paper: `figures/contrasts_r1.pdf` (draft figure), `tables/main_r1.tex` (draft table, interval label now corrected to 99.5%) and `tables/r4a.tex`.

## Rebuild

From the repository root:

```
.\.venv\Scripts\python.exe paper\tables\make_tables.py
.\.venv\Scripts\python.exe paper\figures\make_paper_figures.py
Set-Location paper; ..\tools\tectonic\tectonic.exe --keep-logs main.tex
```

The scripts read `phase3_final_review/evidence/verification/verify_{r1,r4a,dcnn,mes}.json`, `phase3_final_review/PHASE3_STATISTICAL_FINDINGS.csv`, `results/r4a/stats_r4a.json` and `results/corrections/milestone2b/corrected_arr_v2.json`. They need numpy and matplotlib from the project's virtual environment and do not train or score any model.

## Submission copy

`CNET_PhaseIV_Research_Paper.pdf` is the final compiled paper. The review ZIP (`CNET_PHASE4_UPDATED_FINAL_REVIEW.zip`, built by `package_review.py`) carries the same file at its top level so it can be submitted directly. Author details and declarations, with their sources, are listed in section 4 of `FINAL_PAPER_QA.md`; open items are in section 5.
