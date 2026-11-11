# Milestone 3B-0.1 — execution safety corrections

Date: 2026-11-11. Base: `f37d0e8`. Response to the CONDITIONAL PASS on the 3B-0 readiness package.

- **Nothing was trained.** No new SHAP and no new population scored.
- **The only model inference** was the bounded consistency check on the already-inspected
  baseline test set, which the task authorized.
- **No upload, no push.** All decisions remain PROPOSED.

## 1. Colab notebook: no accidental training path (commit `9826d9d`)

**Problem:** section 6 ran `python -m src.experiments.ae_xgb ...` unconditionally, so "run all
cells" would train a full model.

**Fix** (`scripts/make_colab_notebook.py`, regenerated `notebooks/colab_runner.ipynb`):

- **Both training actions are disabled by default:** the legacy single-baseline run (§6) and a
  3B batch (§8). Each runs only when an empty-by-default variable equals an exact confirmation
  phrase (`AUTHORIZE_LEGACY_BASELINE_RUN`, `AUTHORIZE_3B_BATCH`); a 3B batch also needs an
  explicit batch number. Otherwise each cell prints that nothing was trained.
- **The results cell** no longer assumes a run exists.
- **The benchmark (§5)** is now described accurately as *bounded computational work that trains
  temporary model components* (60 AE batches, 50 XGBoost rounds) for timing. It saves no model
  and evaluates nothing.
- **Unchanged:** the dry run (`matrix_3b plan`) stays active, and the D-015 Drive guard
  (`D015_AMENDMENT_1_RECORDED = False`, asserted before any Drive access) is untouched.

**Regression tests** (`tests/test_notebook.py`, 3 new):

- they fail if any training entry point (`src.experiments.ae_xgb` without `--benchmark`, or
  `matrix_3b run`) is reachable outside a phrase-guarded block;
- they check that the guards default to empty;
- they show that the detector flags a newly added active line;
- they keep the benchmark wording honest and the dry run active.

Run against the previous notebook, the detector flags exactly the reviewer's line.

## 2. Monday prediction consistency (commit `3079bea`)

**Bounded check, already-inspected test set only.** `scripts/check_inference_consistency.py`
writes `results/protocol/milestone3b/inference_consistency_v1.json`. Saved model, 33,877
baseline test rows, CPU, threshold 0.5:

| Method | Max \|Δprob\| vs saved | Bitwise = saved (float32) | Max \|Δmargin\| vs runner path | Rows \|Δmargin\| > 1e-3 | Threshold crossings |
|---|---|---|---|---|---|
| Runner path: preprocessing → float32 → `ae.encode` (batch 8192) → XGBoost | 3.0e-8 (CSV rounding) | **yes** | 0 | 0 | 0 |
| `CompositeModel` float32, batch 8192 | 8.6e-8 | no (float64 sigmoid) | 0 | 0 | 0 |
| `CompositeModel` float32, batch 65536 | 8.6e-8 | no | 0 | 0 | 0 |
| `CompositeModel` float32, batch 1024 | 8.6e-8 | no | 0 | 0 | 0 |
| `CompositeModel` float32, batch 8192, shuffled rows | 8.6e-8 | no | 0 | 0 | 0 |
| `CompositeModel` float64 | 8.9e-4 | no | 1.57 | 16 | 0 |

**Findings:**

- **The saved pipeline is reproduced exactly.** On real test rows no batch-size or row-order
  dependence was observed in float32 (margins identical).
- **Where D-019's dependence came from.** It was observed on SHAP's masked, off-manifold
  background rows (batches of 50–100). It is not excluded in principle for other inputs.
- **The probability difference between `CompositeModel` and the saved values** comes only from
  computing the sigmoid in float64 instead of XGBoost's float32 output.
- **float64 is a numerically different function:** 16 rows move by more than 1e-3 log-odds, with
  no class changes. That is not a justified substitute.

**Validated Monday method** (`score_benign.runner_equivalent_proba`):

- the runner-identical path above, on CPU, in the recorded row order (deterministic on a given
  library/hardware stack);
- every score also records a batch-65,536 recomputation (maximum margin difference, threshold
  crossings) as a numerical-sensitivity check.

**Remaining limitations:**

- results can differ across hardware or library versions (CPU vs GPU, Colab vs laptop), so
  Monday scoring is pinned to CPU and records its environment;
- the batch check covers two batch sizes on Monday, not every possible batching.

**Regression test:** a bounded real-data test re-scores 9,000 saved test rows (spanning two
8,192-row batches) through the Monday path and requires bitwise-equal float32 probabilities,
identical classes and 0 crossings.

## 3. Monday scorer provenance: fail closed (commit `3079bea`)

`score_benign` now verifies everything before any inference, reusing `load_matrix`,
`aggregate_3b._check_config`, `lf_sha256` and the population record.

| Check | Function | Refuses when |
|---|---|---|
| Protocol files unchanged | `load_matrix` | groups or population file changed since the matrix was generated |
| Monday record ↔ matrix | `check_record` | groups file or hash ≠ committed r1; split fingerprint differs; view set ≠ exactly the 63 r1 views; counts inconsistent |
| Monday rows | `score_run` | kept-row hash ≠ record |
| Run artifacts | `check_run` | any of `DONE`, `identity.json`, `effective_config.json`, `preprocessor.json`, `run_record.json`, `data_report.json`, `checkpoints/ae_best.pt`, `xgb_model.json` missing |
| Run identity | `check_run` → `_check_config` | effective config hash ≠ the required matrix entry (catches a wrong entry, a changed seed, any edit) |
| Training population | `check_run` | run trained on another split |
| Evaluation population | `check_run` | run not evaluated on the family-common test rows |
| Input schema | `check_run` | model inputs ≠ the 68 baseline inputs minus the entry's columns, wrong `input_dim`, or removed columns not recorded as dropped |

There are synthetic tamper tests for every row. `--confirm-approved` is documented, in the CLI help
and the notebook, as **an operator confirmation only**. It is not checked against the decision
log and is not proof that any decision is approved.

## 4. R4a clarifications (this commit; documentation only)

The saved feasibility record is unchanged. `docs/MILESTONE_3B0_READINESS.md` §4 and the decision
log now state:

- **The +5:00 offset** is empirically estimated from the DDoS onset and end. It is not
  independently established as a time-zone correction.
- **Three of the four subflow changes** rest on label-separated distribution comparisons only:
  they are *suspected* definition changes, not proven semantic redefinitions.
- **R4a-ii remains PROPOSED.**
- **Separate experiments don't settle causality.** Separate original and corrected experiments
  reduce within-dataset inconsistency but do not by themselves isolate extractor-defect causality.

## 5. Verification

| Check | Result |
|---|---|
| Full test suite, laptop | **161 passed, 0 failed, 0 skipped** (3 matplotlib deprecation warnings from SHAP's plotting module). The 16 `tests/test_audit.py` tests pass locally since 2026-11-11 with Smart App Control still on; the cause is unknown and the block may recur |
| Notebook | no active training path (test); dry run active; D-015 guard intact |
| Monday inference | runner-identical path, bitwise-verified on the inspected test set |
| Provenance before scoring | all checks in §3, tamper-tested |
| Population records, 110 generated configs, `matrix.json`, frozen groups r0/r1 | unchanged since `f37d0e8` (`git diff`); `--check` and `--r1 --check` reproduce; `matrix_3b plan` loads |
| Protected artifacts | 96 unchanged (`correct_arr --verify`) |
| SHAP / training | none |

## 6. Remaining blockers

- **Approvals:** D-007, D-012, D-020 r1, D-021, D-023 (and D-004, D-005, D-024 for R4a). None is
  approved.
- **Colab has never run.** Package versions, speed and the 16 audit tests there are unmeasured.
- **Monday scoring** additionally needs D-023 approval and completed, verified matrix runs.
- **Hardware dependence:** float32 results may differ across hardware, which is why scoring is
  pinned to CPU.

## 7. Ready for the first Colab verification session?

**Yes, for verification only:** the test suite, environment snapshot, dataset checksum, the
bounded benchmark, and the dry run. Running the notebook top to bottom cannot train a model.
The user still signs in and uploads the CICIDS2017 zip and a code bundle under D-015 Amendment 1.
Training batches stay blocked until the approvals are recorded and the operator types the
confirmation phrase.
