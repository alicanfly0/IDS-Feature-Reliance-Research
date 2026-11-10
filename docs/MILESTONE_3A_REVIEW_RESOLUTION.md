# Milestone 3A — response to the independent review (CONDITIONAL PASS)

Date: 2026-11-10. Base: `d3852e5` (protocol r0). **Nothing here has been trained or run on a
model.** Every new measurement is read-only on the existing local CICIDS2017 files. The original
proposal `configs/protocol/ablation_groups_3a.yaml` (r0) is unchanged. Proposed changes are
versioned as **r1** and stay PROPOSED until approved.

## 1. Findings: confirmed, rejected or refined

| # | Reviewer concern | Verdict | Evidence |
|---|---|---|---|
| 1 | Twin detection used the 78 raw columns, not the 68 model-visible inputs | **Concern valid in principle; measured leakage: none.** The 700/839 exclusions are confirmed on the exact float32 model input of every view | §2; `scripts/verify_eval_populations_3a.py`; `results/protocol/milestone3a/eval_population_3a_r0.json` |
| 1a | Float32 can merge distinct values | **Confirmed as a real mechanism**, harmless in all pre-registered views | §2 |
| 2 | 5 controls × 1 seed confounds control-draw and seed variability | **Confirmed.** It also cannot yield exact significance (below) | §3 |
| 2a | *Additional finding:* with 5 paired seeds, the smallest exact two-sided sign-flip p is 2/2⁵ = 0.0625 | **New, blocking for r0** | §3 |
| 3 | Statistical plan issues | **Partly confirmed:** the decision rule mixed Holm p-values with unadjusted intervals; it was one-directional; the bootstrap is unreliable with 5 units; it ignores time-block correlation and the discreteness of very low error counts | §4 |
| 4 | Roles of the populations | **Confirmed:** Monday cannot measure recall; the temporal split is within-session; R4a is the only test of the central question on corrected data | §5 |
| 5 | Group A control imbalance (0.051 vs ≥ 0.086) | **Confirmed;** it limits the interpretation of a null result for A, not of a positive one | §6 |

## 2. Leakage check on the model-visible inputs

**Method.** `scripts/verify_eval_populations_3a.py` rebuilds what the runner
(`src/experiments/ae_xgb.py`, `preprocess()`) feeds the model:

1. D-011 rows and the pinned split (fingerprint asserted).
2. `TrainOnlyPreprocessor` refit on train with each view's columns removed.
3. `to_numpy(float32)`.
4. `split.exclude_eval_twins` on both representations.

It asserts that raw-view exclusions are a subset of the model-visible ones.

**Mechanisms checked one by one** (read-only):

| Mechanism | Could it create twins the raw check misses? | Measured |
|---|---|---|
| Columns constant on train | Yes, if they varied in validation/test | All 10 have a single value across validation + test |
| Train-median imputation | Yes, if non-finite values remained | 0 non-finite cells after D-011 |
| Min-max scaling | No (per-column, one-to-one) | Distinct vectors 223,080 raw = 223,080 float64-scaled |
| **Float32 cast** | **Yes** | 16 columns lose distinct values (e.g. `Flow Duration` 187,750 → 187,254; `Flow Bytes/s` 202,291 → 201,764), but full vectors stay distinct (223,080) |
| Column removal per view | Yes | See below |

**Result.** In all 38 r0 views, model-visible exclusions equal raw-view exclusions (0 extra
validation, 0 extra test). The family-common population is unchanged:

| Partition | Rows | Excluded | All excluded rows BENIGN? |
|---|---|---|---|
| Validation | 33,834 → 33,134 | 700 | yes |
| Test | 33,877 → 33,038 | 839 | yes |

The test population is 19,233 DDoS and 13,805 BENIGN. The same method reproduces the executed
D-018 run's logged 357/391 exclusions exactly.

**Records.** The record holds per-view counts, the excluded source rows and SHA-256 of the kept
source rows. The r1 views (draws 5–9) were checked the same way; see §7.

**Safeguard kept.** The runner already re-checks partition overlap on the float32 inputs after
exclusion and aborts if it is not zero (`preprocess()`). Any future view must still pass both this
script and that guard. "No leakage" is claimed only for the views measured.

## 3. Control and seed design

The per-seed contrast is d_s = Δ_g,s − Δ_c,s, where Δ is metric(full) − metric(ablated), all on
the identical population. The estimand of interest is **E[d] = the effect of removing group g
minus the effect of removing a randomly drawn, size-matched set of non-artifact features**.
The randomness of the control draw therefore belongs in the estimand.

| Option | Fits | What it estimates | Paired by seed? | Identifiable variance | Main limitation | ≈ CPU-h* |
|---|---|---|---|---|---|---|
| **A** r0: 5 draws, draw *j* ↔ seed *j* | 55 | E[d] over draws and seeds | yes | total only (draw and seed confounded) | **5 units: smallest exact p = 0.0625**, so the Holm family is unreachable without a normality assumption; t-intervals rest on df = 4 | 2.3 |
| **B** 1 fixed control × 5 seeds | 55 (+25 per extra draw) | group vs **one particular** control set | yes | seed only | conditional on one arbitrary draw, so it doesn't generalize to "random features"; still 5 units | 2.3 |
| **C** full cross, 5 draws × 5 seeds | 155 | E[d], with draw, seed and residual components | yes | draw, seed, residual (no interaction replicate) | still 5 seed and 5 draw units (df ≈ 4 each); about 3× cost for decomposition, not power | 6.5 |
| **D** (recommended, r1): 10 draws, draw *j* ↔ seed *j*, seeds 0–9 | **110** | E[d] over draws and seeds | yes | total; the decomposition comes from sensitivity C′ | can't split draw from seed in the primary analysis, which isn't needed for E[d] | 4.6 |
| C′ (sensitivity with D) | +18 | draw vs seed share for A and U: 3 draws × 3 seeds | yes | draw, seed | small; descriptive | +0.8 |

\* Laptop-CPU equivalent at about 2.5 min per fit (measured 1.45–2.36 min). Colab speed is still
unmeasured.

**Why D.** Ten exchangeable paired units, each with an independent draw and seed, make the
sign-flip test exact. The smallest p is 2/1024 ≈ 0.002, below the strictest Holm/Bonferroni
threshold of 0.05/10 = 0.005. A t-interval has df = 9.

D only *extends* the frozen design. Draws 0–4 and seeds 0–4 are r0's; draws 5–9 come from the
same pre-registered rule, `RandomState(3000 + 100·g + j)`. They are frozen in
`configs/protocol/ablation_groups_3a_r1.yaml`; `--r1 --check` reproduces it, and a test confirms
draws 0–4, groups, clusters and matched controls are identical to r0.

The full model and every group then use seeds 0–9. Option A remains a valid analysis of a
subset, reported with the limits above if D is not approved.

## 4. Statistical plan: corrections (proposed, r1)

1. **Units and the conditional scope:**
   - **Seed-and-draw uncertainty:** the primary inference uses the 10 paired d_s, with an exact
     sign-flip p-value and a t-interval (df = 9).
   - **Row-sampling uncertainty:** a separate, paired bootstrap over test content groups.
     Sensitivity version: **minute-block bootstrap** (timestamps from TrafficLabelling, verified
     row-aligned), because flows within one attack session are correlated and content-group
     resampling understates that.
   - **Scope:** all intervals are **conditional on the CICIDS2017 testbed** (one network, one
     attacker–victim pair for DDoS). No resampling here represents independent network
     environments, and none is claimed to.
2. **Very low error counts:**
   - **Primary in-domain endpoint changes from MCC to error rate** (FP + FN over rows). Near the
     ceiling MCC is close to a monotone function of the error count and adds no information,
     while the error count makes the discreteness explicit.
   - **Continuous sensitivity endpoint:** log loss.
   - **Per-seed descriptive test:** exact McNemar (conditional binomial on discordant rows).
   - **Bootstrap intervals** are reported with the number of distinct replicate values. Where
     fewer than 20 distinct values occur, exact/binomial results are used.
3. **Monday FPR:**
   - per model: Clopper–Pearson interval;
   - for model differences: the paired d_s over seeds (as in 1), plus a block bootstrap over
     Monday time blocks or source hosts. Content groups alone understate correlation.
   - A positional timestamp join for Monday must first be verified, as it was for Friday.
4. **Consistent decision rules** (replaces protocol §6.5 rows; two-sided):
   - **Primary family:** 10 tests (5 groups × {in-domain error rate, Monday FPR}).
   - **Significance:** Holm on the exact sign-flip p-values.
   - **Intervals:** Bonferroni-adjusted (1 − 0.05/10 = 99.5%), so they are consistent with the
     strictest Holm step.
   - **Three readings:**

     | Reading | Condition |
     |---|---|
     | **Difference** | Holm-significant, interpreted by its sign (removal can also improve performance) |
     | **Practically relevant difference** | the adjusted interval lies entirely beyond ±SESOI |
     | **Practical equivalence at the SESOI** | the 99% interval (TOST at α = 0.005) lies within ±SESOI |
     | **Inconclusive** | none of the above |

   - **SESOI:** proposed as before (D-020), expressed for error rate as 0.001 absolute (about 33
     rows of 33,038). That is a change of scale from MCC and needs approval.
5. **Independent populations are required** for confirmatory primary claims about the central
   question. In-domain results are pre-registered estimates on an inspected test set (§5).

## 5. Roles of the evaluation populations

| Population | Labels | What it can show | What it cannot show | Status |
|---|---|---|---|---|
| Friday in-domain test (family-common) | DDoS + BENIGN | dependence on feature groups within the inspected capture | anything uninspected; generalization | pre-registered estimate on an inspected set |
| Friday temporal holdout | DDoS + BENIGN | stability across time blocks **within one attack session** (same hosts, same tool) | cross-network or cross-session generalization; it is *not* that | sensitivity |
| Monday | BENIGN only | false-positive behaviour on untouched benign traffic of the same network | recall; new attacks; other networks | confirmatory for FPR only |
| Tue–Thu benign reserve | BENIGN only | one-time replication of the Monday FPR finding | as for Monday | sealed until the end |
| **R4a: Engelen corrected Friday** | DDoS + BENIGN (95,123 DDoS) | whether performance and group dependence survive corrected flow construction and labels: **the central question** | row-level pairing (flows re-segmented) | **priority confirmatory test; blocked by D-004/D-005** |

**What D-004/D-005 must settle for R4a to run:**

1. adopt WTMC2021 (not CNS2022);
2. a hand-checked map of the 77 shared feature names, with `Fwd Header Length.1` fed from
   `Fwd Header Length`;
3. a list of features whose *definition* Engelen changed (e.g. the documented Down/Up ratio fix
   and the flag counters), reported as expected shift, never silently harmonized;
4. a label policy: DDoS → 1, BENIGN → 0, others excluded (no DDoS-Attempted exists on Friday);
5. the time window: verify Engelen's timestamp format and restrict to the original file's window;
6. exclusion of R4a rows identical to any training vector in any **model-visible** view, using
   this script's method.

## 6. Group A control fairness

A's 8 flag counters are nearly binary, with mean train-only separability 0.051. Over the 10 r1
draws, random controls range 0.086–0.178 and the matched control is 0.090. No pool feature is
flag-like, because every flag field is in A or constant on train, so no fair univariate match
exists.

**Implications:**

- **If A's removal costs more than its controls,** the claim is strengthened: A is less
  separable feature by feature yet matters more.
- **If A's effect does not exceed its controls,** that is **inconclusive about A**, not evidence
  that A is harmless.
- Univariate separability also understates multivariate use: flag counts were the top SHAP
  features.

**Proposed handling**, with no tuning on validation or test data:

- the primary analysis is unchanged;
- a pre-registered *descriptive* regression of control effects on control separability across
  the 10 draws, with A's effect read against the fitted value at 0.051;
- A's main evidence weight is placed on R4a (where Engelen corrected the flag counters) and Monday.

## 7. Recommended experiment matrix (r1, PROPOSED)

| Tier | Experiment | Fits |
|---|---|---|
| Mandatory | Full reference, seeds 0–9 | 10 |
| Mandatory | Groups A, B, C, D, U, seeds 0–9 | 50 |
| Mandatory | Random controls, draw *j* ↔ seed *j*, *j* = 0–9 | 50 |
| Mandatory | Monday FPR scoring of all mandatory fits (inference) | 0 |
| Mandatory once D-004/D-005 approved | R4a scoring of all mandatory fits (inference) | 0 |
| Sensitivity | C′ draw × seed decomposition for A and U | 18 |
| Sensitivity | Difficulty-matched controls, seeds 0–4 | 25 |
| Sensitivity | B-literal, seeds 0–4; Destination Port alone, seeds 0–9 | 15 |
| Sensitivity | Temporal holdout: full + groups + draw 0, seeds 0–2 | 33 |
| Sensitivity | AE cap 200 where the cap is hit | ≤ 25 |
| Sensitivity | Proxy-closed ARR from the saved arrays; reserve scored once | 0 |
| Optional | Wednesday cross-attack; exploratory top-5 SHAP group (5); track A (5); fixed-model masking | 10 |

**r1 population.** Measured on the model-visible inputs over all 63 r1 views:
0 extra twins in every view, and the same family-common population as r0. The 5 new draws that
exclude rows (22 validation / 52 test each) fall inside the existing union, leaving 33,134
validation and 33,038 test rows (19,233 DDoS / 13,805 BENIGN). Record:
`results/protocol/milestone3a/eval_population_3a_r1.json`.

## 8. Updated compute

| Tier | Fits | Laptop-CPU equivalent | Storage at ~30 MB/run |
|---|---|---|---|
| Mandatory | 110 | ~4.6 h | ~3.3 GB |
| + sensitivity | +91 to +116 | +3.8 to +4.8 h | +2.7 to +3.5 GB |
| + optional | +10 | +0.4 h | +0.3 GB |

This runs on Colab Free in batches of about 10 fits (user rule: jobs over 30 minutes go to
Colab). Drive needs at most about 7 GB of its free 15 GB. Colab timing is benchmarked first.

## 9. Decisions requiring approval

- **D-020 r1:**
  - controls extended to 10 draws (`ablation_groups_3a_r1.yaml`);
  - seeds 0–9;
  - Option D;
  - primary in-domain endpoint = error rate;
  - decision rules §4.4;
  - SESOI 0.001 error rate and 0.001 FPR.
- **D-007:** adopt the §4 plan (replaces the five-seed bootstrap proposal).
- **D-004, D-005:** as in §5, the priority for R4a.
- **Unchanged and still PROPOSED:** D-012, D-021, D-022, D-023, D-006, D-009, D-010.

## 10. Criteria for allowing Milestone 3B training

1. D-007, D-012, D-020 (r1 or r0, explicitly chosen), D-021 and D-023 approved and recorded.
2. The chosen groups file passes `--check` (`--r1 --check` for r1), and its population record
   exists with zero model-visible extra twins (done for r0 and r1).
3. 3B code implemented and tested locally:
   - the population-record loader;
   - generated view configs;
   - the scorers;
   - the exact sign-flip and t analyses;
   - the block bootstrap.

   Including one local smoke ablation.
4. The full test suite passes on Colab, including the 16 audit tests blocked on the laptop.
5. The seed-0 Colab reproduction matches the laptop baseline, and the timing is benchmarked.
6. No 3A model has been evaluated on any population before 1–5 hold.
