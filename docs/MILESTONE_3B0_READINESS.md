# Milestone 3B-0 — execution readiness

Date: 2026-11-11. Base: `964d507` (3A review resolution). Working design: protocol **r1**
(`configs/protocol/ablation_groups_3a_r1.yaml`), as the reviewer recommended. **Status: preparation
and local verification only.**

- **Nothing was trained**, and no population was scored by any model.
- **No upload or sign-in** to any cloud service happened.
- **Every decision stays PROPOSED.** Accepting r1 as the working design does not approve the 110
  fits.

---

## 1. Statistical clarifications

### 1.1 Orientation

All primary endpoints are "lower is better": error rate, Monday FPR, and log loss as the
sensitivity.

| Quantity | Definition | Positive value means |
|---|---|---|
| Removal effect Δ_x,s | metric(model without x, seed s) − metric(full, seed s) | removing x made the model **worse** |
| Contrast d_s | Δ_group,s − Δ_control(draw s),s | removing the group hurt **more** than removing a random size-matched control |

Every table, interval and figure uses this orientation. It is implemented and tested in
`src/evaluation/stats_3b.py` (`removal_effect`, `contrasts`) and in `aggregate_3b.py`.

### 1.2 What the sign-flip test assumes, and what it can show

**Assumptions:**

1. **Independent pairs, conditional on the fixed evaluation rows.** Each pair s = 0..9 has its own
   training seed and an independent control draw. The test rows are shared, so every p-value and
   interval is **conditional on this test set and this capture**.
2. **Exactness only under the sharp null.** The sign-flip p-value is exact under the *sharp* null:
   within each pair, the group and the control draw are exchangeable (the group behaves like one
   more random draw), so d_s is symmetric about 0. Under the weaker null ("equal mean removal
   effect, possibly different spread or skew") the test is only approximate. The group is fixed
   while controls vary, so their spreads can differ.
3. **Ties carry no sign.** With very few errors, many d_s may be exactly 0. Zeros stay in the mean
   but carry no sign information. The smallest attainable p is 2/2^m, where m is the number of
   non-zero contrasts. With m ≤ 8 (p ≥ 2/256 ≈ 0.0078), the Holm/Bonferroni threshold of
   0.05/10 = 0.005 **cannot** be reached.

**Conservative interpretation, pre-registered:**

- **Exact test reported only when assumption 2 is plausible:** exact p-values are reported with
  m and their minimum attainable value. A Holm-significant result is called exact only if the
  sharp-null framing is accepted; otherwise it is "significant under an approximate
  randomization test".
- **t-interval as sensitivity:** df = 9, Bonferroni-consistent level. When the exact test and the
  t-interval disagree, the reading is **inconclusive**.
- **Too many ties:** if m ≤ 8 for an endpoint, that endpoint is reported as **"not testable at the
  family α by design"**, with effect sizes and intervals only. The continuous log-loss endpoint
  (no ties) is the pre-specified sensitivity.
- **No resampling of independent networks:** nothing here resamples networks, capture sessions or
  attack tools. No claim extends beyond the CICIDS2017 testbed.

### 1.3 Group A matching

Group A's weak univariate match (0.051 against controls of at least 0.086) is a **matching
limitation in both directions**. A larger effect for A than for its controls is *not*
automatically stronger evidence. A null result for A is inconclusive. The descriptive regression of
control effects on separability stays as a sensitivity analysis. The resolution document §6 is
corrected accordingly.

---

## 2. Infrastructure implemented (commit `4008315`)

| Component | Where | What it enforces |
|---|---|---|
| Family-common population loader | `src/experiments/population.py`; `run.eval_population` in `src/experiments/ae_xgb.py` | Record hash (LF-normalised SHA-256) and split fingerprint; refuses a view whose own twins are not excluded; kept validation/test rows must hash-equal the record, so the rows are identical for every model; cannot be combined with `exclude_eval_twins`; the existing float32 overlap guard still runs |
| Matrix and run configs | `src/experiments/matrix_3b.py`; `configs/experiments/generated/r1/` (110 YAML + `matrix.json`) | Design D (full and 5 groups at seeds 0–9; draw *j* ↔ seed *j*); refuses unknown groups, inputs outside the 68 model columns, wrong draw counts or sizes, a groups/population hash mismatch, protocol changes since generation, and overwriting a differing config |
| Dry run | `python -m src.experiments.matrix_3b plan [--storage DIR]` | Batches, done/pending status, estimates; trains nothing |
| Batch training gate | `... run --batch K --storage DIR --device cuda --confirm-approved` | Refuses (exit 2) without the flag; one batch at a time; each run is the existing resumable runner |
| Run isolation and resume | existing `ae_xgb.run` | `run_id` = experiment + seed + device + config hash; per-epoch checkpoints; a finished run is never recomputed; resume refused if config, device, dataset or commit changed |
| Aggregation | `src/evaluation/aggregate_3b.py` | Each run must come from its committed config (config hash); test rows, order and labels must be identical across runs and equal to the population; deterministic output; paired discordance and exact McNemar against the same-seed full model |
| Monday FPR scorer | `src/evaluation/score_benign.py` | Monday only (all BENIGN, checked); D-011 rules; rows identical to any **model-visible** training vector in any r1 view are excluded for all models; Clopper–Pearson per model. **No scorer exists for the sealed reserve** |
| Statistics | `src/evaluation/stats_3b.py` | Orientation, exact sign-flip with tie handling and attainable-p reporting, t-intervals, Holm, pre-registered readings, Clopper–Pearson, cluster bootstrap with a distinct-replicate count |
| Colab notebook | `scripts/make_colab_notebook.py` → `notebooks/colab_runner.ipynb` | Installs numba and shap if missing (needed by `tests/test_audit.py`); new §8 3B dry-run cell; the training line is commented out and needs `--confirm-approved` |

**Original artifacts:** all 96 SHA-256-protected artifacts are unchanged, and `correct_arr --verify`
passes. The six SHAP arrays and original runs are untouched.

## 3. Tests and blockers

| Run (laptop, 2026-11-11) | Passed | Failed | Skipped | Blocked |
|---|---|---|---|---|
| `pytest --ignore=tests/test_audit.py` | **139** | 0 | 0 | — |
| `tests/test_audit.py` | — | — | — | **16 not collectable**: Smart App Control blocks Numba, which SHAP imports |

The 13 new tests (`tests/test_milestone3b0.py`) cover:

- orientation, exact sign-flip values and ties, Holm and readings;
- Clopper–Pearson and the bootstrap;
- the design-D matrix, consistency with the committed configs, and every refusal path;
- idempotent generation and the approval gate;
- aggregation row-identity enforcement;
- model-visible Monday twin detection;
- one **real-data** check: every view gets identical family-common rows, and tampered records or
  hashes are refused.

**Unresolved:** the 16 audit tests run only on Colab (§6). Nothing is marked as passed for them.

## 4. R4a feasibility (read-only audit)

**Records:**

- `configs/protocol/r4a_column_map_v1.yaml`: PROPOSED map plus documented definition changes;
- `results/protocol/r4a/r4a_feasibility_v1.json`: all measurements;
- `scripts/audit_r4a_feasibility.py`: reproduces them.

No model was loaded.

| Item | Finding |
|---|---|
| Column coverage | All 78 original inputs map to Engelen columns (21 renames; `Destination Port` ← `Dst Port`; `Fwd Header Length.1` ← `Fwd Header Length`, its documented duplicate; `CWE Flag Count` ← `CWR Flag Count`, name only, and constant on train so not a model input) |
| Clock | Engelen timestamps run **exactly +5:00** relative to the original. The DDoS onset (15:56 vs 20:56) and end (16:16 vs 21:16) agree, and after alignment the per-minute DDoS counts span the same 21 minutes. The cause is undocumented; a UTC−3 vs UTC+2 time-zone difference fits but is a hypothesis |
| Candidate population | Inside the aligned original window (15:30–17:03): **95,123 DDoS + 51,520 BENIGN**. Outside it, PortScan and Bot are out of scope. No "DDoS - Attempted" class exists. D-011 removes 3 rows. 0 rows duplicate an original training vector in the 6 views checked (full + 5 groups); the union over all 63 views must be recomputed before scoring |
| Label windows | Engelen's documentation gives its tuned DDoS label window as 03:40–04:30 PM (local, by their table). In the data, DDoS flows occur only in 15:56–16:16 after alignment |
| **Definition and encoding changes** (documented or label-free evidence) | **≥ 16 of the 68 model inputs:** (1) 8 flag fields of group A, counted per packet instead of first packet only (documented); (2) 4 subflow features: for `Subflow Fwd Packets`, the label-free relation `Subflow Fwd Packets` = `Total Fwd Packets` holds in 100% of original rows vs 0% in Engelen, where the value is 0 in 99.4% (undocumented); the other three subflow features show the same collapse (DDoS median 0 or far below the original) in the descriptive comparison; (3) 2 init-window fields: "not observed" coded −1 in the original (14.6% / 39.1%) vs 0 in Engelen, never −1 (encoding change); (4) `min_seg_size_forward`: value set changes (20/32/40/28 → 8/20/40/24); (5) Down/Up Ratio (fix logged on the landing page, 24/11/2021) |
| Distribution shift (descriptive) | For DDoS, 24 inputs have KS ≥ 0.5 between original and corrected flows, many at 1.0 (flags, subflow, forward lengths); for BENIGN, 7. `Destination Port` = 80 for 99.998% of original and 100% of corrected DDoS flows |

### Conclusion: R4a is executable, but its original design cannot answer the question alone

**R4a-i** (score the original-trained models on corrected Friday data) is technically executable.
But it confounds three things:

1. corrected flow construction, which is the artifact question;
2. **re-defined or re-encoded features** (at least 16 inputs), which is not an artifact question;
3. re-tuned labels.

A performance drop could not be attributed to artifact reliance. The group-vs-control contrast
is also contaminated: random controls contain re-defined features (e.g. subflow), so "removal
improves transfer" may reflect definition changes rather than artifacts.

**Proposed fix (D-024, new):**

- **R4a-ii (primary):** rebuild the same protocol *within* the corrected data. That means the
  Engelen Friday window, DDoS vs BENIGN, track-B duplicate-aware split, the same groups mapped by
  name with proxy closure recomputed on the corrected training partition, the same design D and
  statistics.
  - **The question it answers:** does near-perfect detection, and group dependence, persist once
    extraction is corrected?
  - **The key contrast:** a group's effect in the original data vs in the corrected data (a
    difference of effects), which removes most of the definition confound because each side
    uses its own consistent definitions.
- **R4a-i (secondary, descriptive):** original models scored on corrected data. It is reported
  as "robustness to an extractor change" with the definition-change list, never as artifact
  reliance.
- **Optional R4a-i′:** models trained on a pre-declared *definition-stable* input view (dropping
  the ≥ 16 changed inputs, chosen from documentation and label-free checks only, never from R4a
  performance), then scored on corrected data.

**What D-004/D-005 must settle:**

- **D-004:** WTMC2021 only (recommended).
- **D-005, five items:**
  1. adopt the column map v1;
  2. adopt the +5:00 alignment rule (estimated from attack onset and end; recorded);
  3. label policy: DDoS → 1, BENIGN → 0, other labels out of scope;
  4. the window = the original file's recording window after alignment;
  5. twin exclusion against all 63 model-visible views before any scoring.

**What would invalidate R4a entirely:**

- if alignment failed (it did not);
- if DDoS were absent in the window (it is present);
- if corrected rows were mostly copies of training vectors (0 in 6 views).

None applies. The definition changes do invalidate R4a-i *as an artifact test*; R4a-ii avoids
that.

## 5. Approvals still required

| Decision | Needed for | Status |
|---|---|---|
| D-007 (statistics, §1 and the resolution doc §4) | any training | PROPOSED |
| D-012 (registry levels, group mapping) | any training | PROPOSED |
| D-020 r1 (10 draws, seeds 0–9, error-rate endpoint, rules, SESOI) | any training | PROPOSED; r1 is the working design only |
| D-021 (AE epoch cap) | any training | PROPOSED |
| D-023 (Monday confirmatory, sealed reserve, index-only Drive records) | Monday scoring; temporal split | PROPOSED |
| D-004, D-005 (as in §4) | R4a | PROPOSED |
| **D-024** (R4a-ii primary; R4a-i secondary) | R4a design | **new, PROPOSED** |
| Colab session (user signs in and uploads the CICIDS2017 zip + code bundle; D-015 Am.1) | first Colab run | the user's action |
| Engelen `dataset.zip` on Drive (if R4a-ii trains on Colab) | R4a-ii on Colab | **not covered by D-015 Am.1**; needs a new amendment, or run locally |

## 6. Colab readiness

**Ready:**

- **The notebook** installs only what is missing, now including numba and shap; runs the full test
  suite (including the 16 audit tests blocked locally); verifies the dataset by checksum;
  benchmarks; and has a 3B dry-run cell.
- **Training needs explicit flags:** the batch command is present but commented, and refuses
  without `--confirm-approved`.
- **Disconnections:** a run that is interrupted resumes from its last AE epoch or later stage when
  the same batch command is rerun. A finished run prints "already complete". Changed configs,
  devices, data or commits are refused (tested locally: `tests/test_ae_xgb.py` resume tests).

**Not measured (no Colab run has ever happened):**

- Colab package versions;
- whether the 16 audit tests pass there;
- GPU/CPU speed per fit;
- Drive write speed.

**Estimates (laptop-measured only):**

- 110 fits × 1.45–2.36 min = **2.7–4.3 h** laptop-CPU equivalent;
- **~3.2 GB** of run outputs at ~30 MB each (Drive free tier 15 GB);
- each fit writes AE checkpoints every epoch plus latent codes, model and predictions.

## 7. Proposed sequence for the first authorized experiment

1. **Record approvals** (D-007, D-012, D-020 r1, D-021, D-023) in the decision log.
2. **Colab session 1** (user signs in, uploads `MachineLearningCSV.zip` and a `git archive` code
   bundle of the approved commit):
   - full test suite, which must include the 16 audit tests;
   - `src.env` snapshot;
   - dataset checksum;
   - `matrix_3b plan`.
3. **Benchmark** on Colab (`ae_xgb --benchmark`), then **batch 0 only** (the 10 full-model seeds).
   Compare seed 0 against the laptop baseline: same population and config family, different
   validation rows, so a close but not identical result is expected and is reported as such.
4. **Review batch 0** before any further batch. Then run batches 1–10 in order, one session at a
   time; aggregation refuses any run that deviates from its committed config.
5. **After all 110:** aggregation, Monday scoring (record `results/protocol/milestone3b/`), the
   pre-registered analysis, then the RES unsealing once (needs its scorer to be written and
   approved).
6. **R4a-ii** is prepared in parallel after D-004/D-005/D-024 (local population and groups for the
   corrected data; no training before approval).

## 8. Commits and integrity

| Commit | Content |
|---|---|
| `4008315` | Execution infrastructure, tests, generated r1 configs, notebook, Group A wording fix |
| (this commit) | R4a feasibility audit and column map, Monday population record, this readiness document, decision-log proposals |

- **No push.**
- **Protected artifacts:** 96 unchanged.
- **Frozen protocol files:** `ablation_groups_3a.yaml` (r0) and `ablation_groups_3a_r1.yaml`
  unchanged.
