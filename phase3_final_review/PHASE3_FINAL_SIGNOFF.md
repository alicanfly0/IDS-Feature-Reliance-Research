# Phase III final sign-off (2026-11-13)

**Responds to:** `CNET_PHASE3_INDEPENDENT_AUDIT.md`, verdict CONDITIONAL PASS, archive `a2e636e3…a05c`.

**Constraints observed:**
- no main-grid rerun;
- no new SHAP;
- no paper edits;
- nothing pushed;
- no fabricated values.

## 1. Verdict

**Phase III is closed for Phase IV drafting**, with the declared limitations in §5.

All three priority items are resolved or explicitly documented:

| Item | Status |
|---|---|
| P0, R4a preservation | Done to the extent possible: 22 of 70 run folders preserved and re-verified. The original VM had already expired; what was lost and what still proves the other 48 is documented. |
| P1, D-021 | The required r1 cap-200 sensitivity was run. **No r1 conclusion changes.** R4a is outside D-021 and is declared as a limitation. |
| P2, reporting corrections | Applied in the review documents and in `docs/BASELINE_ADAPTATIONS.md`. The paper is not edited; corrections are listed for Phase IV. |

## 2. P0: preservation of the R4a run outputs

**What happened.**
- The original Colab VM (`/content/r4a_local`, all 70 complete runs) expired overnight on 2026-11-12/13, before this request.
- Its Drive mirror (second Colab account, `My Drive/cnet-r4a`) was incomplete, because that Drive hit its 5 GB quota during training.

**What survives.** Read-only inventory made on a fresh VM on 2026-11-13: `evidence/verification/r4a_drive_inventory_2026-11-13.json`, SHA-256 `047c095d…f049`; classification in `r4a_preservation_status.json`, SHA-256 `76d3f3e9…03ca`.

| State | Runs | Which |
|---|---|---|
| Complete on Drive; predictions re-scored = pre-expiry record (FP, FN, AUROC, row hash) | **22** | full s0–9, A s0–9, Actl0–1 |
| Folder only, artefacts never uploaded | 32 | Actl2–9, B s0–9, Bctl0–9, U s0–3 |
| Absent | 16 | U s4–9, Uctl0–9 |

**Durable local copy of the 22.**
- Downloaded from Drive to `results/runs/r4a_drive_copy_2026-11-13/` (git-ignored; 319,301,502 bytes).
- Archive `cnet-r4a-20261113T184613Z-1-001.zip`, SHA-256 `3f74ff75e84deb6031774a79a4a9250e7c8058a0d3946401897ccadf949cf4e0`.
- Every file of every run hashed: `evidence/verification/r4a_local_copy_verification.json` (SHA-256 `c45d4a40…bc17`).
- All 22 have all 13 required artefacts, including `checkpoints/ae_best.pt`, and predictions identical to the record. 0 problems.

**Evidence for all 70** (unchanged, created before the VM expired):
- `r4a_predictions_colab_check.json` (SHA-256 `130da7c0…1d4b`): FP, FN, AUROC, row hash, convergence and identity for each of the 70 prediction files, recomputed on the original VM.
- `results/r4a/aggregate_r4a.json` (`3ac5e226…7c2c`, commit `85a2ed2`).

**Cannot be re-verified any more:** raw predictions, models and logs of the 48 lost runs. Their per-run numbers rest on the two records above, which agree with each other (`verify_r4a.json`, 0 problems).

## 3. P1: D-021 epoch-cap sensitivity

**Rule** (`docs/decision_log.md`, batch-0 approvals 2026-11-11): "AE cap of 100 epochs, with the cap-200 sensitivity where the cap is hit". It was approved with the r1 grid.

**Applicability.**
- D-024 (R4a) does not mention D-021, and the batch approvals state "sensitivity runs … remain unapproved".
- So the rule applies to **r1 only**: the 2 capped fits `r1_D_s0` and `r1_D_s5`.
- The **17 capped R4a fits are outside the rule**: A s5, s7; B s0, s1, s8, s9; Bctl s0, s2, s3, s6, s7, s8; U s0, s5, s6, s7, s8. No sensitivity was run for them (minimum required, as instructed).

**What was run (2026-11-13, Colab T4).**
- Environment check: "compatible with spec v1 (fingerprint be81b4d6…)", the **same environment fingerprint as the primary r1 fits**.
- Code bundle `b6297226`. The training path is identical to the r1 commit `659c35d`: `git diff` touches only data-loader dispatch, the DCNN and population helpers.
- Configs `configs/experiments/sensitivity/d021_r1_D_s{0,5}_cap200.yaml` and the runner `scripts/sensitivity_d021.py` were committed in `343b780` and written to the VM byte-identically (SHA-256 `8a6b86e3…`, `1705adb4…`, `fe57f52b…`).
- The configs differ from the primary ones only in `ae.max_epochs` = 200 and the experiment name.
- Runs went into separate storage; the primary results are untouched.
- Scored on the frozen 33,038 test rows and the frozen 494,940 Monday rows (runner-identical inference; 0 threshold crossings).

**Pre-run checks on the VM:** dataset OK; split and family-common population OK; **pytest 188 passed, 9 skipped, 0 failed**.

**Results** (`evidence/verification/d021_sensitivity.json` `31060484…eb93`; comparison `d021_comparison.json` `749079bf…d466`):

| Fit | AE epochs run / best (primary → cap 200) | Test errors (FP + FN) | Monday FP |
|---|---|---|---|
| r1_D_s0 | 100 / 99 → **124 / 113** (early stopped) | 8 (3 + 5) → 9 (3 + 6) | 1,172 → 1,138 |
| r1_D_s5 | 100 / 95 → **114 / 103** (early stopped) | 14 (5 + 9) → 13 (5 + 8) | 1,051 → 1,135 |

**Group D statistics with the cap-200 values substituted** (sensitivity; the primary record is unchanged):

| Endpoint | Primary: mean d, p, Holm p, reading | Cap-200 sensitivity |
|---|---|---|
| Error rate | +0.000148, 0.0059, 0.047, difference below SESOI | **+0.000148**, 0.0059, 0.047, same reading; 99.5% interval [+0.000027, +0.000270] |
| Monday FPR | +0.000255, 0.344, 1.0, inconclusive | +0.000265, 0.336, 1.0, inconclusive |

No other Holm decision in the 10-test family changes.

**Conclusion:** both capped fits converge by about epoch 125 under the cap of 200, and the r1 conclusions are insensitive to the cap.

**Durable copy** of the two sensitivity runs (all artefacts and checkpoints):
- `results/runs/d021_sensitivity/d021_sensitivity_runs.zip` (git-ignored; 58,117,166 bytes; SHA-256 `2268ca3661b71c900b2c99328ab24798b468bf92daaa394793d157233b8d7f00`).
- Prediction hashes inside match the JSON.

**Relevance of the 17 R4a cap hits to the equivalence claim:**
- They cluster in B, B-control and U, which are exactly the arms of two of the three R4a contrasts.
- Their errors (0–4) are in the same range as the uncapped fits.
- The r1 sensitivity shows capped fits converge shortly after 100 epochs with near-identical error counts.
- Unmeasured cap effects of a few errors per arm cannot be excluded. The R4a-ii equivalence verdicts must therefore be read as "no effect larger than the SESOI (≈ 22 errors)", which a few errors could not overturn. This is a qualitative argument, not a measurement.

## 4. P2: reporting corrections (documents updated; the paper is to be corrected in Phase IV)

| Item | Correction | Where applied |
|---|---|---|
| r1 interval level | Difference intervals are **99.5%**; TOST intervals are **99%** | `PHASE3_OPEN_ISSUES.md` OI-1. Still mislabelled "99%" in `results/milestone3b/tables_r1.md` (frozen), `paper/tables/main_r1.tex` and the `paper/main.tex` captions: fix in Phase IV. |
| R4a interval level | Difference intervals **98.33%**; TOST **96.67%** | `results/r4a/R4A_ANALYSIS_NOTES.md` (corrected 2026-11-12); review documents |
| MES-DNN pooling | Report per network (prevalence 4.0% vs 64.0%); never the 85.5% / 0.715 means | `PHASE3_BASELINE_COMPARISON.md`, `PHASE3_EXECUTIVE_RESULTS.md`; paper `tab:compare` in Phase IV |
| MES-DNN interpretation | N1's own base model keeps MCC 0.939 → 0.940; the N1 ensemble collapse is a stacking effect, not duplicate loss; only the N2 base drop (0.906 → 0.150) is tied to duplicate hold-out | `PHASE3_BASELINE_COMPARISON.md`, `PHASE3_EXECUTIVE_RESULTS.md` §5 and §7, claims matrix C16 |
| Wardana scenarios | Verified from the PDF text (`pypdf`): Scenario 1 = per-network DNNs cross-tested (Table 9); **Scenario 2 = integrated stack (Table 10; 96.67% / F1 95.36%)**; **Scenario 3 = new network (Table 11)**. The PDF's Fig. 2/3 captions carry swapped labels. Our setting is the two-network analogue of Scenario 2. | `docs/BASELINE_ADAPTATIONS.md` (corrected), `PHASE3_BASELINE_COMPARISON.md`, OI-3. The code docstring in `src/experiments/mes_dnn.py` still uses the old label (code not edited). |
| ARR union vs group U | ARR "all registered" = 23 features (including the D hypotheses); ablation U = 20 (A ∪ B ∪ C) | `PHASE3_EXPLAINABILITY.md`, OI-4 |
| "Practical equivalence" | Equivalence *within the pre-declared margin* (≈ 33 r1 errors / ≈ 22 R4a errors vs baselines ≈ 6 / ≈ 2), not proof of no dependence | `PHASE3_EXECUTIVE_RESULTS.md` §7, claims matrix C7 |

## 5. Declared limitations (unresolved, stated rather than fixed)

1. **R4a artefacts:** 48 of 70 R4a run folders are lost (see §2). Their results rest on the pre-expiry, hash-matched prediction check and the aggregate.
2. **R4a convergence:** 17 R4a autoencoders hit the 100-epoch cap, outside D-021, with no sensitivity run (see §3).
3. **Floor and margin:** the R4a-ii equivalence sits near a zero-error floor, and both SESOIs are generous.
4. **R4a-i confounding:** R4a-i is descriptive and confounded (segmentation, labels, ≥ 16 definition changes, the +5:00 assumption).
5. **Inspected population:** the r1 test population was inspected during design. Seeds are the unit of analysis, with inference conditional on one test set.
6. **Adaptations:** all baselines are adaptations. MES-DNN uses 2 of 5 networks, and no unseen-network test was run.
7. **SHAP scope:** one AE-XGBoost model, float64. No corrected-data ARR exists.
8. **Not re-run locally:** the DCNN feature selection and Monday scoring, because of application-control blocks on the laptop. Their records pass every internal check.

## 6. Evidence paths and hashes

| Artefact | SHA-256 |
|---|---|
| `evidence/verification/d021_sensitivity.json` | `31060484adafd04339202fcdcded55d66126e6e38ac5de791689d9a44aa7eb93` |
| `evidence/verification/d021_comparison.json` | `749079bf6eddc2a0287f8d158be72d651621a98d3d7383a0e6cc3a913b40d466` |
| `evidence/verification/r4a_drive_inventory_2026-11-13.json` | `047c095d22b15986b311ad7d78c2a15514f95e01718f65551f56ff6ca093f049` |
| `evidence/verification/r4a_preservation_status.json` | `76d3f3e938d092fe8fe7e7556b9a8f303eb0213f8efc6da3375a97bebb5903ca` |
| `evidence/verification/r4a_local_copy_verification.json` | `c45d4a40c627de2e4805213067133a9cda94d9b614e416f94d96963e3608bc17` |
| `evidence/verification/r4a_predictions_colab_check.json` | `130da7c0ef0f617cf263115caa97bbd15eb8da15fa0e88f5cbdfa79be8321d4b` |
| `results/r4a/aggregate_r4a.json` | `3ac5e226b5cac68ed68aaae467ce7d0d7f21ad61d4958e676731c0caa16f7c2c` |
| `results/milestone3b/stats_r1.json` (unchanged) | `57e68d1794bff96ee976c74b04f703c94c08f6a8827558b690d7c30f2779ccb3` |
| `results/runs/r4a_drive_copy_2026-11-13/cnet-r4a-20261113T184613Z-1-001.zip` (local, not packaged) | `3f74ff75e84deb6031774a79a4a9250e7c8058a0d3946401897ccadf949cf4e0` |
| `results/runs/d021_sensitivity/d021_sensitivity_runs.zip` (local, not packaged) | `2268ca3661b71c900b2c99328ab24798b468bf92daaa394793d157233b8d7f00` |
| Code: sensitivity configs and runner | commit `343b780` |
| Code bundle used on Colab | `cnet_code_b6297226d6dc.zip` (commit `b6297226`) |

**Scripts** (all in `phase3_final_review/scripts/`):
- `r4a_preservation.py`
- `verify_r4a_local_copy.py`
- `d021_compare.py`
- `../../scripts/sensitivity_d021.py`
