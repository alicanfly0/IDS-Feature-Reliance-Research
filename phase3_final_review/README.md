# Phase III final evidence review package

This package is for an independent reviewer. Nothing in it trains a model or runs SHAP.

**Start here:**
1. `PHASE3_EXECUTIVE_RESULTS.md`
2. `PHASE3_EXPERIMENT_AUDIT.md`
3. `PHASE3_OPEN_ISSUES.md`

## Contents

| File | Content |
|---|---|
| `PHASE3_EXECUTIVE_RESULTS.md` | Results narrative, key numbers, conclusions, limits |
| `PHASE3_EXPERIMENT_AUDIT.md` | Completion and integrity checks per experiment family (copy of `docs/PHASE3_FINAL_COMPLETION_AUDIT.md`) |
| `PHASE3_ALL_METRICS.csv` | Tidy metrics: experiment, dataset, model, view, run, seed, population, metric, value, source. Populations are never pooled. |
| `PHASE3_STATISTICAL_FINDINGS.csv` | All contrasts, intervals (with levels), exact p, Holm p, readings, assumptions |
| `PHASE3_R4A_COMPARISON.md` | Original vs corrected CICIDS2017 (R4a-ii and R4a-i) |
| `PHASE3_BASELINE_COMPARISON.md` | AE-XGBoost, DCNN and MES-DNN vs the source papers |
| `PHASE3_EXPLAINABILITY.md` | SHAP, ARR (registry v2), baseline attribution pilots |
| `PHASE3_FIGURE_TABLE_INVENTORY.md` | Every figure and table, with source, axes, uncertainty, reading |
| `PHASE3_RESEARCH_CLAIMS_MATRIX.md` | Each claim, its evidence and status |
| `PHASE3_OPEN_ISSUES.md` | Genuine unresolved issues |
| `figures/` | F1–F8, generated from verified records |
| `evidence/verification/` | Outputs of the independent verification scripts |
| `evidence/records/` | Copies of the committed result, protocol, config, decision and code records |
| `evidence/existing_figures/` | Figures that already existed |
| `evidence/predictions_inventory.csv` | Path, SHA-256 and size of every saved test-prediction file (the files themselves are not packaged) |
| `scripts/` | `verify_r1.py`, `verify_r4a.py`, `verify_dcnn.py`, `verify_mes.py`, `build_tables.py`, `make_figures.py`, `package.py` |
| `MANIFEST.sha256` | SHA-256 of every file in the package |

## Re-running the verification

Run these from the repository root, with its virtual environment, the downloaded result stores and the raw datasets in place.

The scripts are torch-free. Run them in this order:

```
python phase3_final_review/scripts/verify_r1.py
python phase3_final_review/scripts/verify_r4a.py
python phase3_final_review/scripts/verify_dcnn.py
python phase3_final_review/scripts/verify_mes.py
python phase3_final_review/scripts/build_tables.py
python phase3_final_review/scripts/make_figures.py
python phase3_final_review/scripts/package.py
```

`verify_r4a.py` uses `evidence/verification/r4a_predictions_colab_check.json`. That file was recomputed read-only from the 70 R4a prediction files on the Colab VM, using the code embedded in its own description. See open issue OI-6.
