# Figure, table and evidence inventory

Every item lists its numerical source, its axes or columns, its units, how uncertainty is shown, and how to read it.

- **"New":** generated in this audit by `scripts/make_figures.py` or `scripts/build_tables.py` from the verification outputs. No training and no SHAP were run.
- **"Existing":** already in the repository.

## A. Figures

| ID | File | Status | Numerical source | Axes and units | Uncertainty | Interpretation |
|---|---|---|---|---|---|---|
| F1 | `figures/F1_r1_group_vs_control_contrasts.png` | New | `evidence/verification/verify_r1.json` → statistics | x: paired contrast d_s ×10⁻³ (error rate; Monday FPR); y: group | Dots: 10 seeds. Diamond: mean. Bar: 99.5% t-interval. Grey band: ±SESOI. | A, D, U: small positive d inside the SESOI. Monday intervals are wide. |
| F2 | `figures/F2_r4a_ii_contrasts_and_original_vs_corrected.png` | New | `verify_r4a.json`, `results/r4a/stats_r4a.json` | Left: d_s ×10⁻³ (R4a-ii). Right: mean d, original vs corrected. | Left: 98.33% t-interval. Right: none drawn (Welch intervals are in the CSV). | Corrected d ≈ 0 for all groups; r1 A and U effects absent. Right panel is descriptive. |
| F3 | `figures/F3_r4a_i_transfer_descriptive.png` | New | `verify_r4a.json` → r4a_i (from `results/r4a/r4a_i_scores.json`) | x: DDoS recall; benign FPR (proportions). y: r1 view. | Per-model dots (10), mean diamond | Only the without-A and without-U models transfer. Descriptive. |
| F4 | `figures/F4_monday_false_positives.png` | New | `verify_r1.json` → monday (from `results/milestone3b/monday_fpr_r1.json`) | x: false-positive count on 494,940 benign rows. y: view (group / control). | Per-seed dots and mean. Clopper–Pearson per model is in the CSV. | Large seed variance; benign-only. |
| F5 | `figures/F5_dcnn_official_vs_filtered.png` | New | `verify_dcnn.json` | Panels: MCC, DoS precision, DoS recall. x: population. | Per-seed dots, joined by seed | The same models score lower on the filtered population. |
| F6 | `figures/F6_mes_dnn_split_modes.png` | New | `verify_mes.json` | y: ensemble MCC per seed. x: split mode. Panels: network. | Per-seed dots; mean labelled | Duplicate-aware splitting removes most skill. Seeds are unstable. |
| F7 | `figures/F7_arr_by_k_registry_v2.png` | New | `results/corrections/milestone2b/corrected_arr_v2.json` | x: K. y: attribution-mass share (%) per registry tier. | Bar = min–max over 6 SHAP variants | Attribution concentrates on the direct defect tier at small K. One model only. |
| F8 | `figures/F8_full_model_errors_per_seed.png` | New | `verify_r1.json`, `verify_r4a.json` | x: seed. y: test error count. | None (all 10 values shown) | Seed variability. Counts are on different populations and are not comparable. |
| E1 | `evidence/existing_figures/contrasts_r1.pdf` (= `paper/figures/contrasts_r1.pdf`) | Existing (`report_3b.py`) | `results/milestone3b/stats_r1.json` | As F1 | Bar is the **99.5%** interval, but the paper caption says 99% (open issue OI-1) | As F1 |
| E2 | `evidence/existing_figures/global_importance_top20-*.png` (3 files) | Existing (M2A) | `results/shap/.../report-*.json` | Mean \|SHAP\| (log-odds) per feature, top 20 | None | One model; registry v1 era. Labels are feature names only. |
| E3 | `paper/main.tex` Fig. `fig:pipeline` | Existing (TikZ, in the draft) | — | Schematic | — | Method diagram only |

## B. Tables

| ID | File | Status | Source | Columns | Uncertainty | Notes |
|---|---|---|---|---|---|---|
| T1 | `PHASE3_ALL_METRICS.csv` | New | Verification JSONs and committed records (per-row `source`) | experiment, dataset, model, view, run_id, seed, population, metric, value, source | Per-seed values; no pooling across populations | 6,495 rows, tidy (long) format |
| T2 | `PHASE3_STATISTICAL_FINDINGS.csv` | New | `stats_r1.json`, `stats_r4a.json`, verification JSONs | Family, group, endpoint, Δs, mean d, SD, interval levels and bounds, p exact, p Holm, reading, assumptions | 99.5% / 98.33% difference intervals; 99% / 96.67% TOST; Welch 95% (descriptive); paired t 95% (DCNN, descriptive) | 37 rows |
| T3 | `results/milestone3b/tables_r1.md`, `paper/tables/main_r1.tex` | Existing | `stats_r1.json` | Group, endpoint, Δ̄_G, Δ̄_R, d̄ [CI], p_Holm, reading | The interval column is labelled "99%" but holds the **99.5%** interval (OI-1) | Values verified |
| T4 | `results/r4a/tables_r4a.md`, `paper/tables/r4a.tex` | Existing (generated, not `\input`) | `stats_r4a.json` | Group, Δ̄_G, Δ̄_R, d̄ [98.33% CI], p_Holm, d̄ (original) | Interval level not printed in the header; it is 98.33% | Values verified |
| T5 | `paper/main.tex` `tab:data` | Existing | Protocol records | Dataset rows and classes | — | Not re-audited here beyond the row counts in `PHASE3_R4A_COMPARISON.md` |
| T6 | `paper/main.tex` `tab:dcnn` | Existing | `results/dcnn_fang/summary.json` | Mean [min, max] per metric and population | Range over 5 seeds | All values match `verify_dcnn.json` |
| T7 | `paper/main.tex` `tab:mes` | Existing | `results/mes_dnn/summary.json` | MCC mean [min, max] per model, population, network | Range over 5 seeds | All values match `verify_mes.json` |
| T8 | `paper/main.tex` `tab:compare` | Existing | Handover (author numbers) and summaries | Author vs ours | — | The MES-DNN row pools two networks, and its scenario label needs checking (OI-2, OI-3) |
| T9 | `paper/main.tex` `tab:related` | Existing | Literature | — | — | Not part of the numerical audit |

## C. Coverage of the brief's topic list

| Topic | Where |
|---|---|
| Dataset and class distributions | `PHASE3_R4A_COMPARISON.md` §A; `PHASE3_EXECUTIVE_RESULTS.md` §2–5; `verify_mes.json` → networks |
| Experimental setup | `PHASE3_EXPERIMENT_AUDIT.md`; `PHASE3_BASELINE_COMPARISON.md` |
| Architecture comparisons | `PHASE3_BASELINE_COMPARISON.md` |
| AE-XGBoost metrics and ablations | T1, T2, F1, F8 |
| Group-vs-control effect plots | F1, F2 |
| ARR and SHAP | F7, E2, `PHASE3_EXPLAINABILITY.md` |
| Monday FPR | F4, T1 (metrics `monday_*`) |
| R4a original vs corrected | F2, F3, `PHASE3_R4A_COMPARISON.md` |
| DCNN duplicate filtering | F5, T1, T2 |
| MES-DNN leakage | F6, T1 |
| Multi-seed variability | F1–F6, F8 (all show per-seed values) |
| Error and limitation analyses | `PHASE3_RESEARCH_CLAIMS_MATRIX.md`, `PHASE3_OPEN_ISSUES.md` |

**Large prediction files** are not packaged. `evidence/predictions_inventory.csv` lists the path, SHA-256, row count and positives for every saved test-prediction file that is available locally (r1, DCNN, MES-DNN). R4a predictions are on the Colab VM; their per-run check is `evidence/verification/r4a_predictions_colab_check.json`.
