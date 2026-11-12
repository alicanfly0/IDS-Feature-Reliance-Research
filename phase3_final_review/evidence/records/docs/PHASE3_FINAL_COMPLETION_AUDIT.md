# Phase III final completion audit (2026-11-12)

This audit was **read-only**: nothing was trained, no SHAP was rerun, and no frozen protocol or experimental output was changed.

**How it was checked:**
- Every completed fit was re-checked from its own saved artefacts, using independent scripts in `phase3_final_review/scripts/`.
- The scripts' outputs are in `phase3_final_review/evidence/verification/`.
- "Verified" means:
  - the artefacts exist;
  - provenance fields agree;
  - every metric was **recomputed from the saved predictions** and equals the committed record;
  - the statistics were **re-derived with an independent implementation** and equal the committed record.

## 1. Summary by experiment family

| Family | Expected | Completed and verified | Problems found | Verification source |
|---|---|---|---|---|
| AE-XGBoost r1 (design D: full + A, B, C, D, U + 10-draw matched controls; seeds 0–9) | 110 | **110** | 0 | `verify_r1.py` → `verify_r1.json` (predictions re-scored on the laptop) |
| Monday benign scoring of the 110 r1 models | 110 | 110 (record-level) | 0 | `verify_r1.json` (FPR = FP/n, Clopper–Pearson recomputed, same run IDs as the aggregate) |
| R4a-ii corrected data (full + A, B, U + controls; seeds 0–9) | 70 | **70** | 0 | `verify_r4a.py` + `r4a_predictions_colab_check.json` (predictions re-scored on the Colab VM) |
| R4a-i (110 r1 models scored on corrected rows) | 110 | 110 (record-level) | 0 | `verify_r4a.json` (confusion identities, same run IDs as r1) |
| DCNN + self-attention (D-009), 5 seeds × 3 test populations | 5 | **5** | 0 | `verify_dcnn.py` (labels and masks rebuilt from the verified CSVs; probabilities re-scored) |
| MES-DNN two-network adaptation (D-010), 2 split modes × 5 seeds | 10 | **10** | 0 | `verify_mes.py` (networks reloaded, partitions regenerated, probabilities re-scored) |
| SHAP / ARR (M2B corrected registry v2, 6 variants, 1 model) | 6 variants | 6 (record-level) | 0 | `corrected_arr_v2.json` (additivity error ≤ 3.8e-7 per variant; ARR recomputed from saved arrays in M2B) |
| DCNN / MES-DNN attribution pilots | 5 + 20 rankings | present | n/a | `results/attribution_pilot/*.json` (descriptive, not re-run) |

**Total model fits verified from saved predictions: 195.** That is 110 r1, 70 R4a-ii, 5 DCNN and 10 MES-DNN ensembles. Each MES ensemble also contains 2 base networks.

**Inference-only evaluations verified at record level: 220.** These are 110 Monday scorings and 110 R4a-i scorings.

## 2. AE-XGBoost r1: checks per run (all 110 passed)

**Run identity**
- Exactly one completed run directory per matrix entry (`DONE` marker); no duplicate or orphan completed runs.
- All 12 required artefacts present (DONE, ae_done, data_report, effective_config, identity, log, metrics, predictions_test, predictions_val, preprocessor, run_record, xgb_model).
- Non-empty `checkpoints/`.

**Configuration**
- The effective configuration hash equals both the hash of the committed generated configuration (`configs/experiments/generated/r1/*.yaml`) and the identity `config_hash`.
- The model seed equals the matrix seed.
- The dropped columns equal the matrix entry's drop list exactly.

**Provenance**
- One environment fingerprint `be81b4d6…fbdb1a8b`: Colab, Tesla T4, CUDA 13.0, torch 2.14.1+cu130, xgboost 3.4.1.
- One code commit `659c35d8349e…`; device `cuda` for all runs.
- Dataset SHA-256: MachineLearningCSV.zip `c3f26274…`.
- Split fingerprint `50bd9948…` for all 110.

**Evaluation population**
- Every test-prediction file holds exactly the family-common rows: SHA-256 of source rows = `2893fd3c…`; 33,038 rows (19,233 DDoS / 13,805 benign).
- Labels and order are identical across all runs; no duplicated rows.

**Predictions**
- All probabilities are finite and in [0, 1].
- The saved `y_pred` equals `prob ≥ 0.5` for every row.

**Metrics**
- tp/tn/fp/fn, error rate, MCC and log loss recomputed from predictions equal `aggregate_r1.json` (exactly for counts, within 1e-12 for reals).
- They also equal each run's `metrics.json` test block, including AUROC.
- Paired McNemar discordance counts equal `aggregate_r1.json`.

**Statistics** (all equal to `stats_r1.json`)
- Δ, d, exact sign-flip p for all 5 groups × 4 endpoints.
- Holm-adjusted p and decisions for the 10 primary tests.
- 99.5% difference intervals.

**Monday record**
- Same run directory as the aggregate; n = 494,940 for every model.
- FPR = FP/n; Clopper–Pearson 95% recomputed.
- Numerical-sensitivity check (batch 65,536 vs 8,192): max |margin difference| = 0 and 0 threshold crossings for every model.

**Convergence**
- XGBoost early-stopped in every fit: best iteration 114–360 of a 2,000-round cap.
- The autoencoder early-stopped in 108 of 110 fits.
- **2 fits reached the 100-epoch cap without early stopping:** `ae3b_r1_D-seed0`, `ae3b_r1_D-seed5`. Both are group-D fits. Their test error counts are inside the group-D range, but they are flagged as a convergence note.

## 3. R4a-ii and R4a-i: checks

**R4a-ii population and aggregate**
- The aggregate population hash equals the frozen record `eval_population_r4a_v1.json`: `48045372…`, 22,049 rows (14,168 DDoS / 7,881 benign).
- `aggregate_r4a.json` is internally consistent (errors = FP + FN; error rate and MCC match the confusion counts).

**R4a-ii Colab cross-check** (read-only recomputation from the 70 `predictions_test.csv.gz` on the Colab VM)
- Row-set hash equals the frozen population for all 70; all probabilities finite; `y_pred` = threshold for all 70.
- FP/FN equal the aggregate for all 70; seed equals the matrix seed.
- Device `cuda`; one environment fingerprint, the same as r1 (`be81b4d6…`).
- The transferred JSON's SHA-256 matched the Colab-side hash (`130da7c0…`).

**R4a-ii statistics**
- d, sign-flip p, Holm (family of 3) and the 98.33% / 96.67% intervals re-derived independently; all equal `stats_r4a.json`.

**Code**
- R4a ran at commit `b6297226`, r1 at `659c35d`.
- `git diff 659c35d b6297226` on the training code changes only `prepare_data`'s data-loader dispatch (the Engelen loader). The model, preprocessing and training code are unchanged.

**R4a-i**
- 110 of 110 r1 models scored; each `run` equals the r1 aggregate's run directory.
- Recall, FPR, error rate and MCC are consistent with the FP/FN counts.
- Threshold crossings under the alternative batch size: 0.

**Convergence**
- XGBoost early-stopped in all 70 fits (best iteration 89–1,337 of 2,000).
- **17 of 70 autoencoders reached the 100-epoch cap:** A s5, s7; B s0, s1, s8, s9; Bctl s0, s2, s3, s6, s7, s8; U s0, s5, s6, s7, s8. This is far more than in r1 (2 of 110). The test errors of these fits are not elevated (corrected-data errors are 0–4 for every model), but the AE reconstruction objective had not plateaued.

**Execution deviations**
- These are recorded in `results/r4a/R4A_ANALYSIS_NOTES.md`.
- The Colab account's Drive reached its 5 GB quota during the campaign, so eight fits (`Actl2`–`Actl9`) were retrained after their incomplete first attempts were moved to `quarantine/`. The incomplete attempts were never scored.
- Aggregation and R4a-i scoring ran on the VM's local disk.
- Four runs lack only `latent.npz`, a training cache that aggregation does not read.
- The 13 laptop-CPU R4a fits from the morning were **not used**.

## 4. DCNN (D-009): checks

**Data and selection**
- UNSW-NB15 training and testing CSVs reloaded through the manifest-verified loader.
- Row counts equal `selection.json`: train 68,264 (12,264 DoS); test 41,089 (4,089 DoS).
- The training-matrix hash equals `selection.json`.
- The selection ranking is internally consistent: the top-22 equal the selected list; cumulative share at K = 22 is 0.9053; the 95% rule gives 30.
- The LightGBM + SHAP selection itself was **not re-run**: `shap` imports `numba`, which this laptop's application-control policy blocks.

**Duplicate filters**
- Both masks were rebuilt and their hashes equal `selection.json`:
  - model-visible: 3,330 excluded (1,862 Normal, 1,468 DoS);
  - raw-feature: 1,395 excluded.

**Metrics**
- For each seed, `test_proba.npy`'s hash equals `metrics.json`.
- Every metric recomputed for the 3 populations equals `metrics.json`.
- All probabilities are finite.

**Training**
- 50 epochs run in every seed; best epoch restored.
- One code commit `9d65e0a`; laptop CPU environment `50d4a357…`.

## 5. MES-DNN (D-010): checks

**Networks**
- Both networks reloaded through the project loaders; the log1p input matrices equal the `networks.json` hashes.
- N1 NF-UNSW-NB15-v2: 2,390,275 rows, 95,053 attack, 236,999 distinct vectors.
- N2 NF-ToN-IoT-v2 subsample: 2,390,275 rows, 1,529,289 attack, 505,611 distinct vectors.
- 39 inputs each.

**Numerical stability**
- All log1p inputs are finite.
- Maximum log1p value: 34.99 (N1) and 592.39 (N2).
- N2 contains 22 + 23 raw values above the float32 maximum (`SRC_TO_DST_SECOND_BYTES`, `DST_TO_SRC_SECOND_BYTES`). After log1p they are finite.

**Partitions**
- All 20 (10 fits × 2 networks) regenerated; partition records and hashes equal `metrics.json`.
- Duplicate-aware test partitions contain **0** rows whose vector occurs in base, meta or validation.
- Random test partitions contain 604,046–604,657 such rows (N1) and 522,546–523,370 (N2), out of 645,374.

**Metrics**
- Every ensemble and base-model metric recomputed (all and novel-vector populations) equals `metrics.json`.
- All probabilities are finite.

**Superseded runs**
- Five duplicate-aware fits with partitioner v1 are kept in `results/mes_dnn/superseded/`. They are excluded and documented: v1 produced distorted class mixes.

## 6. Mismatches and corrections found by this audit

1. **Interval labelling (r1)**
   - The pre-registered difference interval is the **99.5%** t-interval (1 − 0.05/10; decision log lines 820–821), and the code computes exactly that.
   - `results/milestone3b/tables_r1.md`, `paper/tables/main_r1.tex`, and the caption of `paper/main.tex` Table `tab:main` / Fig. `fig:contrasts` label it **"99%"**. The 99% level belongs to the TOST interval.
   - The values are right; the label is wrong. Not edited here, because these are a frozen output and the paper. To fix in Phase IV.
2. **Interval labelling (R4a)**
   - My own note `results/r4a/R4A_ANALYSIS_NOTES.md` called the R4a-ii interval "95%"; it is the 98.33% Bonferroni-consistent interval (family of 3).
   - Corrected in that note, with a visible correction line.
3. **MES-DNN pooled metric**
   - `paper/main.tex` Table `tab:compare` reports "ensemble accuracy 85.5%, F1 0.715 (random); 61.7%, F1 0.445 (duplicate-aware)".
   - These values are correct as computed, but they are **means over the two networks' test partitions**. The partitions have different attack prevalence: 4.0% (N1) vs 64.0% (N2).
   - Averaging incompatible populations should be replaced by per-network values in Phase IV:
     - random: N1 accuracy 0.941, F1 0.665, MCC 0.658; N2 accuracy 0.769, F1 0.764, MCC 0.625;
     - duplicate-aware: N1 accuracy 0.536, F1 0.087, MCC 0.001; N2 accuracy 0.699, F1 0.804, MCC 0.242.
4. **Wardana comparison scenario**
   - The paper compares our setting (all networks integrated) with Wardana's 96.67% / 95.36%, which the handover records as their *scenario 2* (Table 10).
   - `docs/BASELINE_ADAPTATIONS.md` calls our setting "scenario 1" and calls scenario 2 "unseen network", while the handover calls the new-network case scenario 3 (Table 11).
   - The numbering must be checked against the PDF before Phase IV; see open issues.
5. **Stale header**
   - `configs/protocol/ablation_groups_3a_r1.yaml` still says "PROPOSED … NOT approved, NOT run".
   - Approval is recorded in `docs/decision_log.md`. Documentation only; the frozen file is not edited.
6. **"Union" terminology**
   - In the ARR registry, "all registered" means 23 features: direct defects, shortcut and hypothesis.
   - Ablation group U means 20 features: A ∪ B ∪ C, *without* the D hypotheses. The paper's "registered features (all evidence tiers)" wording is correct, but "union" must not be used for both.

No metric or statistical value in the committed records was found to differ from its recomputation.

## 7. Scientifically usable?

All 195 fits and 220 inference evaluations are usable for their pre-registered or declared purpose:
- R4a-i and the original-vs-corrected comparison are descriptive.
- DCNN and MES-DNN are adaptations, not reproductions.

**Limits of usability** (not failures):
- The 19 autoencoder fits at the epoch cap (2 in r1, 17 in R4a).
- The DCNN selection, which could not be re-run locally.
- The R4a run folders, which live only on the Colab VM and a full Drive. Their predictions were re-scored on the VM before this audit and the result was packaged.
