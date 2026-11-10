# Milestone 3A — Pre-registered experiment protocol

**Status: PROPOSED, awaiting team approval. Nothing in this document has been run.**
Date: 2026-11-10. Base commit: `fe7263e` (Milestone 2B.1). Frozen groups:
`configs/protocol/ablation_groups_3a.yaml`, generated from the training partition only by
`scripts/freeze_ablation_groups_3a.py` (`--check` reproduces it from the data).

The measured facts in this document came from read-only checks on 2026-11-10. They involved no
model, no prediction and no validation or test metric:

- the frozen groups, from the training partition;
- evaluation-twin counts per view, from feature values only;
- TrafficLabelling row correspondence and timestamps;
- label counts, from the existing inspection reports.

No training, SHAP, upload or dataset rewrite took place.

---

## 1. Objectives and hypotheses

**Central question.** Does the near-perfect in-domain performance of the AE-XGBoost baseline
(test F1 0.99987, one seed) depend on documented CICIDS2017 measurement artifacts or
non-generalizable shortcuts? Or does it survive their removal, new time periods and corrected
captures?

| ID | Hypothesis (direction not assumed) | Primary population | Status |
|---|---|---|---|
| H1 | Removing a literature-defined artifact group changes in-domain performance by more than removing a size-matched random set of non-artifact features | In-domain, family-common test (inspected) | Pre-registered estimate; not confirmatory (§5.1) |
| H2 | Models without a documented-artifact group have a different false-positive rate on untouched benign traffic than the full model | Monday benign (model-untouched) | **Confirmatory** for FPR |
| H3 | Models trained without documented-artifact groups transfer differently to Engelen's corrected Friday capture | Engelen Friday DDoS window | **Confirmatory** once D-004/D-005 are approved |
| H4 | Performance holds when train and test come from different time blocks of the same attack | Temporal holdout | Sensitivity analysis |

Any outcome is a result. Removing artifacts may lower, preserve or raise in-domain scores. A
null result is reported as "no practically relevant difference at the pre-registered margin"
only when the equivalence criterion in §6.5 is met. Otherwise it is "inconclusive", never
"equivalent".

**What we will not claim:**

- that a group is an artifact *for this model*;
- that any row is corrupt (no packet reconstruction exists);
- causality from SHAP or ARR@K;
- generalization beyond the populations actually tested.

---

## 2. Literature-grounded ablation groups

**Inputs.** 68 model inputs: the 78 raw columns minus 10 that are constant on train. Source:
`results/baselines/…/preprocessor.json`.

**Proxy closure (new, measured on train).** CICIDS2017 repeats several measurements under
different names. Removing one copy while its twin stays makes an ablation meaningless, because
the model can still read the same value. Every group and every control is therefore closed
under these proxy clusters: exact equality on train, or |Pearson r| ≥ 0.999.

| Cluster (train partition) | Relation |
|---|---|
| `Total Fwd Packets` = `Subflow Fwd Packets` | exact |
| `Total Backward Packets` = `Subflow Bwd Packets` | exact |
| `Total Length of Fwd Packets` = `Subflow Fwd Bytes` | exact |
| `Total Length of Bwd Packets` = `Subflow Bwd Bytes` | exact |
| `Fwd Packet Length Mean` = `Avg Fwd Segment Size` | exact |
| `Fwd Header Length` = `Fwd Header Length.1` | exact (also documented by Engelen) |
| `SYN Flag Count` = `Fwd PSH Flags` | exact on train |
| `RST Flag Count` = `ECE Flag Count` | exact on train |
| `Bwd Packet Length Mean` ≈ `Avg Bwd Segment Size` | r = 1.0000 |
| `Packet Length Mean` ≈ `Average Packet Size` | r = 0.9994 |

**Consequence for the 2B ARR values.** `Subflow Fwd Packets` and `Avg Bwd Segment Size` are
unregistered copies of registered features. Attribution split between twins means registry-v2
ARR slightly *understates* the shortcut tier. A proxy-closed ARR recomputation from the six saved
arrays is listed as sensitivity S7. It is pure postprocessing and is not done here.

### Groups (frozen)

| Group | Columns (exact original names) | Evidence | Mechanism | Strength |
|---|---|---|---|---|
| **A: TCP flag-count defects** (8) | `FIN Flag Count`, `SYN Flag Count`, `RST Flag Count`, `PSH Flag Count`, `ACK Flag Count`, `URG Flag Count`, `ECE Flag Count`, `Fwd PSH Flags` | Engelen extended documentation, *Flow Construction / TCP flag count* (registry v2; `docs/evidence/engelen_extended_2026-11-09.md`) | Aggregate counters update on the first packet only; directional PSH/URG increments documented as wrong | Documented extractor defect; **row-level errors unverified** |
| **B: Engelen TCP-appendix shortcut indicators**, proxy-closed (10) | `Init_Win_bytes_forward`, `min_seg_size_forward`, `Fwd Header Length`, `Fwd Header Length.1`, `Total Fwd Packets`, `SYN Flag Count`, `Bwd Packet Length Mean` + proxies `Subflow Fwd Packets`, `Avg Bwd Segment Size`, `Fwd PSH Flags` | Engelen et al. 2021, §IV-B.1, physical p.5 | Values are correct, but they mark artifact (appendix) flows, so a model can use them as a shortcut | Shortcut indicator, paper-supported |
| B-literal (7, sensitivity) | the 7 registered columns without proxies | same | same | shows the effect of closure |
| **C: Lanvin duplication-affected** (4) | `Flow IAT Min`, `Flow IAT Mean`, `Flow Packets/s`, `Bwd Packets/s` | Lanvin et al. §3.3 pp.8–9 (Table 5), §4.2 Q3 p.15 | Duplicated capture packets distort timing and rate values (~5% of packets; 3.48–5.96% per day) | Direct value distortion for affected flows; affected Friday flows **not identified** |
| **D: metadata and hypothesis controls** (2) | `Destination Port`, `Init_Win_bytes_backward` | Phase II; Engelen §III-D p.4 leaves the port open; D-018 | Service/topology shortcut (port 80 = 99.998% of DDoS) | **Unverified hypothesis**: never called an artifact |
| **U: documented union** (20) | A ∪ B (closed) ∪ C | as above | all documented mechanisms together | union only; no new evidence |

**Overlaps.** `SYN Flag Count` and its twin `Fwd PSH Flags` belong to both A and B (two
mechanisms, registry R07). In U they are counted once. A and B results are not additive and
are never summed.

**Unavailable after train-only preprocessing.** These 4 registered flag fields are constant on
train, so no model sees them: `CWE Flag Count`, `Bwd PSH Flags`, `Fwd URG Flags`,
`Bwd URG Flags`. They stay in the registry but are not part of A.

**Disclosure about selection.** Group A was added to the registry in 2B after a reviewer
noticed that `ACK Flag Count` and `PSH Flag Count` ranked 1st and 4th in the **test-set** SHAP
pilot. Its membership is defined by the documented defect family (all flag fields, not just
the top-ranked ones), and the source predates our data. But the decision to look was triggered
by test-set attribution. We therefore treat A's in-domain result as exploratory and rely on
untouched populations (Monday, R4a) for confirmatory claims about A. No group was selected
from SHAP rankings.

**Exploratory, not pre-registered as confirmatory.** "Destination Port + top-5 test-SHAP
features" (the old 2A suggestion) is kept as O2 and always labelled exploratory.

---

## 3. Matched-size controls

Controls are drawn from a **pool of 46 inputs in 41 proxy clusters**: all 68 inputs minus every
registered column and its proxies. Two kinds are frozen per primary group, before any
experiment:

1. **Random controls (primary).** There are 5 draws per group. Each is made of whole proxy
   clusters, so no control removes half of a twin pair, and matches the group's column count
   exactly. Draws use `RandomState(3000 + 100·group_index + draw)`. Draw *j* is trained with
   model seed *j*, so the control family carries both draw and seed variability.
2. **Difficulty-matched control (sensitivity).** Each group cluster is matched to the pool
   cluster of the same size whose train-only univariate separability (|AUROC − 0.5|) is
   closest.

| Group | Size | Group mean separability | Matched control | Random controls (5 draws) |
|---|---|---|---|---|
| A | 8 | 0.051 | 0.090 | 0.086–0.138 |
| B (closed) | 10 | 0.157 | 0.148 | 0.123–0.140 |
| C | 4 | 0.134 | 0.127 | 0.037–0.203 |
| D | 2 | 0.074 | 0.078 | 0.052–0.244 |
| U | 20 | 0.122 | 0.141 | 0.122–0.137 |

**Limitation.** Group A's flag counters are nearly binary, so every pool feature separates the
classes better on its own. A's controls are therefore "harder" than A itself; this is disclosed
and not tuned away. The full column lists are in the frozen file. None of these selections
looked at validation or test rows, model outputs or SHAP values.

---

## 4. Experiment definitions

### 4.1 Common settings (all AE-XGBoost fits)

- **Data and split:** D-008 data, D-011 rules, the pinned track-B split (fingerprint `50bd9948…`).
  Identical training rows for every fit.
- **Model:** the D-017 architecture and hyperparameters, threshold 0.5, AE `max_epochs` 100 and
  patience 10 (see D-021).
- **Seeds:** model seeds **0–4** for every configuration. The existing seed-0 runs are *not*
  reused, because the validation population changes (below).
- **Family-common populations (measured).** In every one of the 38 pre-registered input views,
  validation and test rows whose vector duplicates an earlier partition are excluded. The union
  of all those exclusions defines one population for every fit, full model included:

  | Partition | Original | Excluded (union over 38 views) | Family-common |
  |---|---|---|---|
  | Validation (early stopping) | 33,834 | 700 (all BENIGN) | **33,134** |
  | Test | 33,877 | 839 (all BENIGN) | **33,038** (19,233 DDoS / 13,805 BENIGN) |

  This removes D-018's validation asymmetry: every model early-stops on the same 33,134 rows
  and is scored on the same 33,038 rows. Largest single-view exclusion: D (466 test rows), then
  the D-018 port view (391), U (382) and B (379); A and C exclude none. Full-population metrics
  of each model are reported separately and never mixed.

### 4.2 Evaluation populations

| Code | Population | Rows | Model contact so far | Use |
|---|---|---|---|---|
| **ID** | Track-B test, family-common | 33,038 | **Inspected**: baseline and D-018 metrics, 5 error rows, 397 distinct SHAP-explained rows + 9 local explanations, registry v2 triggered by test SHAP | Pre-registered estimates (H1); not confirmatory |
| **TMP** | Temporal holdout of the same Friday file (§5.2) | TBD in 3B | Contains previously inspected rows | Sensitivity (H4) |
| **MON** | Monday, all BENIGN (MachineLearningCVE, same zip already authorized for Drive) | 529,918 before twin exclusion | **Never scored** by any model | Confirmatory FPR (H2) |
| **RES** | Tuesday–Thursday BENIGN, sealed reserve | TBD | Never scored | Used **once**, at the very end, to replicate H2; no decision may depend on it |
| **R4a** | Engelen WTMC2021 Friday, DDoS and BENIGN within the original file's time window | 95,123 DDoS in the full Friday file | Descriptive inspection only | Confirmatory transfer (H3); **blocked by D-004/D-005** |
| **WED** | Wednesday DoS (Hulk, GoldenEye, slowloris, slowhttptest) + BENIGN | 692,703 rows | Never scored | Optional cross-attack transfer; DoS ≠ DDoS labels, so caveated |

For MON, RES, WED and R4a, rows identical to any training vector in any pre-registered view are
excluded once (union), and counts are reported. Within-population duplicates are kept; the
bootstrap clusters them (§6).

### 4.3 Experiment matrix

**M = mandatory · S = recommended sensitivity · O = optional extension · B = blocked by a decision.**
"Fits" are new AE-XGBoost trainings; "inference" means scoring saved models only.

| ID | Tier | Experiment | Model / inputs | Seeds | Fits | Evaluation | Purpose |
|---|---|---|---|---|---|---|---|
| M1 | M | Full reference | 68 inputs | 0–4 | 5 | ID, MON | reference with aligned validation |
| M2 | M | Primary groups A, B, C, D, U removed | 60 / 58 / 64 / 66 / 48 inputs | 0–4 each | 25 | ID, MON | H1, H2 |
| M3 | M | Random controls, 5 per group | size-matched | draw *j* ↔ seed *j* | 25 | ID, MON | null distribution for H1/H2 |
| M4 | M | MON scoring of M1–M3 | — | — | 0 (55 inferences) | MON | H2 (confirmatory) |
| S1 | S | Difficulty-matched controls | size-matched | 0–4 | 25 | ID, MON | control robustness |
| S2 | S | B-literal (no proxy closure) | 61 inputs | 0–4 | 5 | ID | shows why closure matters |
| S3 | S | Destination Port alone | 67 inputs | 0–4 | 5 | ID, MON | D-018 replicated with seeds |
| S4 | S | Temporal holdout: full, A–U, random draw 0 per group | — | 0–2 | 33 | TMP | H4 |
| S5 | S | AE cap 200 for configurations whose fits hit the 100-epoch cap | as hit | as hit | ≤ 25 | ID | convergence check (D-021) |
| S6 | S | Sealed reserve, scored once at the end | — | — | 0 | RES | H2 replication |
| S7 | S | Proxy-closed ARR@K from the six saved arrays | — | — | 0 | — | attribution sensitivity |
| O1 | O | Wednesday cross-attack | M1–M3 models | — | 0 | WED | attack-type transfer |
| O2 | O | Exploratory: port + top-5 test-SHAP features removed | 62 inputs | 0–4 | 5 | ID | **exploratory only** |
| O3 | O | SHAP rankings on train/validation rows; E-XAI stability and descriptive accuracy | M1 seed 0 | — | 0 | — | unbiased rankings (Colab: Numba) |
| O4 | O | Track A, paper-comparable 5-fold | 68 inputs | 1 | 5 | folds | paper comparability, with leakage counts |
| O5 | O | Fixed-model masking of groups (no retraining) | M1 models | — | 0 | ID | "uses" vs "needs" |
| B1 | B | R4a: score M1–M3 on Engelen Friday | — | — | 0 | R4a | H3; needs D-004, D-005 |
| B2 | B | R4a-ii: retrain M1/M2 on corrected data | — | 0–4 | ≤ 30 | Engelen split | needs D-005 |
| B3 | B | DCNN + self-attention (§8) | — | — | — | — | needs D-009, D-022 |
| B4 | B | MES-DNN (§8) | — | — | — | — | needs D-010 |

**Totals (AE-XGBoost):** mandatory 55 fits; with recommended sensitivities about 123–148; with
optional extensions about 133–158. Inference runs are cheap (seconds per model).

---

## 5. Dataset and evaluation protocols

### 5.1 In-domain (ID)

- **Partitioning:** the track-B duplicate-aware split, unchanged.
- **Leakage safeguards:**
  - partition overlap checked per view on raw and preprocessed inputs;
  - twins excluded per view;
  - the family-common union is applied to all models;
  - training rows never change.
- **Confirmatory status:** the ID test set has been inspected. The baseline and D-018 metrics,
  5 misclassified rows, 397 distinct SHAP-explained rows plus 9 local explanations, and the
  registry-v2 trigger all came from it. ID results are **pre-registered estimates on an
  inspected population**. They are reported with that label and never as an untouched
  holdout. Recomputing rankings on validation later cannot restore the test set's pristine
  status.

### 5.2 Temporal holdout (TMP)

**Measured on 2026-11-10:**

- **Row correspondence:** `TrafficLabelling/Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv`
  has the same 225,745 rows in the same order as the MachineLearningCVE file. All 79 shared
  columns are identical row by row, so its `Timestamp` can be attached by position.
- **Timestamp resolution:** minutes only (e.g. `7/7/2017 3:30`, 12-hour clock without AM/PM;
  the relative order within the file is what is used).
- **DDoS window:** 3:56–4:16 (21 minute stamps).
- **BENIGN window:** 3:30–5:02.
- **Hosts:** 128,024 of 128,027 DDoS flows go from `172.16.0.1` to `192.168.10.50`. A host- or
  session-grouped holdout is therefore **impossible** for the attack class; only time blocks
  are possible.

**Proposed rule**, fixed before any model sees the split:

1. Cut points are whole minutes, chosen from DDoS row counts per minute only, aiming at about
   70 / 15 / 15 of DDoS rows for train / validation / test.
2. One gap minute is left before test.
3. BENIGN rows follow the same time cuts.
4. Content-twin exclusion is applied across the temporal partitions.

The class balance will shift, and test will hold the BENIGN tail after the attack; this is
reported. TMP tests drift within one attack session, not a new environment.

**Implementation note:** `GeneratedLabelledFlows.zip` is **not** covered by D-015 Amendment 1. The
split is therefore built locally, and only the index-only split record goes to Drive (D-023).

### 5.3 Original → corrected (R4a)

- **Data:** Engelen WTMC2021 `Friday-WorkingHours.csv`: 547,915 rows, with 95,123 DDoS, 291,433
  BENIGN, PortScan, Bot and Bot-Attempted. There is **no** "DDoS - Attempted" class on Friday.
- **Needs before running:**
  - a hand-checked map of the 77 shared feature names (`Fwd Header Length.1` is fed from
    `Fwd Header Length`, its documented duplicate);
  - restriction to the original DDoS file's time window, using Engelen's timestamps (format to
    be verified);
  - a label policy (D-005).
- **No row correspondence exists** (flows were re-segmented), so results are distributional, not
  paired by row. Models are scored without retraining (B1). Retraining on corrected data (B2)
  is a separate, optional analysis.

### 5.4 Cross-dataset

- **AE-XGBoost:** no valid cross-schema evaluation exists. UNSW-NB15 (Argus/Bro) and
  NetFlow-v2 share neither feature semantics nor units with CICFlowMeter (D-006). None is
  planned, and none will be presented as transfer.
- **WED** is a same-schema, cross-attack test with a label-semantics caveat: DoS is not DDoS.

### 5.5 Rules for every population

- Rows are never added, relabelled or imputed beyond D-011.
- Every exclusion is logged with counts by class.
- No host identifier, session key, row correspondence or feature map is invented. The temporal
  join is verified; the R4a map is hand-checked and reviewed before use.

---

## 6. Statistical analysis plan

### 6.1 Units

There are two independent sources of variation:

- **Model seed:** training randomness (AE initialisation, batch order, XGBoost subsampling).
- **Test content group:** sampling of evaluation flows. Identical vectors form one group.

Folds are never units (D-007). Rows inside one content group are not independent.

### 6.2 Metrics

- **Primary:** MCC at the fixed 0.5 threshold, on ID and TMP.
- **H2 primary:** FPR on MON.
- **H3 primary:** MCC and DDoS recall on R4a.
- **Secondary** (descriptive, unadjusted):
  - F1, recall, precision, AUROC;
  - log loss, which stays sensitive when error counts are tiny;
  - FN and FP counts;
  - per-seed early-stopping epochs and cap hits;
  - XGBoost trees;
  - exclusion counts and class shifts.

### 6.3 Effects

- **Δ_g** = mean over seeds of [metric(full) − metric(group g removed)], on the identical
  population.
- **Control-adjusted effect:** **C_g = Δ_g − mean(Δ_controls,g)**. This is the primary
  estimand for H1/H2.
- The percentile rank of Δ_g within the 5 control effects is also reported (descriptive; with
  5 draws it has coarse resolution).

### 6.4 Uncertainty

- **Method:** hierarchical paired bootstrap, B = 2,000.
- **Each replicate:**
  1. resample the 5 seeds (with their tied control draws) with replacement;
  2. resample test content groups with replacement;
  3. recompute every model's metric on the same resampled rows;
  4. form Δ and C.
- **Reported:** 95% percentile intervals, and two-sided bootstrap p-values for the primary family.

### 6.5 Multiplicity, equivalence and decision rules

- **Primary family:** 10 tests (C_g for groups A, B, C, D, U on ID-MCC and on MON-FPR).
  Holm–Bonferroni across the 10. Everything else is secondary or descriptive and labelled so.
- **Smallest effect size of interest (SESOI, proposed, D-020):**
  - |ΔMCC| = 0.001 on ID (about 8 extra errors out of 33,038);
  - |ΔFPR| = 0.001 (0.1 percentage points) on MON.
- **Three possible readings:**

  | Reading | Condition |
  |---|---|
  | **Dependence** | Holm-adjusted p < 0.05, and the 95% interval lies beyond +SESOI |
  | **No practically relevant difference** | 90% interval inside ±SESOI (two one-sided tests) |
  | **Inconclusive** | anything else |

  A non-significant p-value alone is never read as equivalence.
- **McNemar:** only as a descriptive, per-seed comparison of two fixed models on identical rows
  (exact two-sided). It ignores duplicate clustering and seed variation, so it is never the
  primary test. The D-018 p = 0.625 stays "not significant, not equivalent".

---

## 7. Compute feasibility (PKR 0)

**Measured costs:**

- AE-XGBoost fit on the laptop CPU: 1.45 min (baseline), 2.36 min (ablation hitting the
  epoch cap).
- Data preparation: about 13 s.
- Run folder: about 30 MB (the 29.7 MB `latent.npz` dominates).

| Block | Fits | Laptop-CPU equivalent | Storage |
|---|---|---|---|
| Mandatory (M1–M3) | 55 | ~2.3 h | ~1.7 GB |
| + recommended (S1–S5) | +68 to +93 | +2.8 to +3.9 h | +2–2.8 GB |
| + optional (O2, O4) | +10 | +0.4 h | +0.3 GB |
| Inference (MON, RES, WED, R4a) | 0 | minutes | small |

**Where it runs**, per the user's rule of 2026-11-10 (jobs over about 30 minutes go to Colab
Free):

- **Colab, in batches:** all fit blocks. They are CPU-cheap, so a GPU is optional. Colab's CPU
  speed and GPU availability are **unmeasured**, so the first Colab session must benchmark
  before committing to a batch.
- **Laptop:** inference and post-processing jobs under 30 minutes. PyTorch loads locally
  again; Numba (SHAP) does not.

**Resilience:**

- Runs are resumable per epoch and never overwrite a finished run.
- Each run's identity is config hash + seed + device.
- Batches of about 10 fits fit comfortably in one Colab session.
- Outputs persist in `MyDrive/cnet-runs/` (15 GB free tier; about 4–5 GB needed at the maximum).
  Only the small artifacts come back to the laptop for scoring: checkpoints, `xgb_model.json`,
  the preprocessor and predictions.

**Reuse:**

- the verified data, split and preprocessing code;
- the existing seed-0 baseline and D-018 runs, as historical references only, since they use a
  different validation population;
- the six SHAP arrays (S7).

**Benchmark before committing:**

1. the Colab test suite, including the 16 audit tests that are blocked locally;
2. a reproduction of the seed-0 baseline on Colab, compared with the laptop run (same device
   class: predictions identical or documented differences);
3. timing of one ablation fit.

---

## 8. Remaining baselines

The three baselines run on **different datasets, label definitions, splits and preprocessing**.
Their numbers are never placed side by side as comparable performance. Each gets its own
in-domain audit.

| | DCNN + self-attention (Fang et al. 2026) | MES-DNN (Wardana et al. 2026) |
|---|---|---|
| Original data | UNSW-NB15 Normal vs DoS: 92,998 / 16,353; the official partition (train 56,000 vs Fang's 55,998 Normal, 12,264 DoS; test 37,000 / 4,089) | Five NetFlow-v2 networks; only NF-UNSW-NB15-v2 acquired (2,390,275 rows, 90.1% duplicates on the 39 inputs) |
| Features | 47 reported → 22 selected by LightGBM + TreeSHAP at a 95% cumulative-importance threshold (training data only) | 39 inputs (43 − 4 IP/port; D-001) |
| Published protocol | Median imputation, IQR + 1st/99th-percentile winsorizing, train min–max, one-hot; Adam lr 5e-4, batch 128, 50 epochs, L2 1e-3, patience 10, 4 heads, BCE, seed 42, 20% validation | Five base DNNs (9-7-5-3, ReLU) + meta-model (10, ReLU, sigmoid); Adam, BCE, batch 1000, 10 epochs; 70/30 with meta-sample |
| Polarity | Normal = positive in the paper; we use DoS = 1 and convert | binary |
| Necessary adaptations | Duplicate-aware split as track B (4.9% of DoS test rows have a training twin in the official partition); a separate explainer for the DCNN itself (the selector's SHAP explains LightGBM) | Reduced scope (D-010); track B mandatory given the duplication |
| Artifact registry | **None established for UNSW-NB15** in our literature (D-012/D-013); only hypothesis groups unless new evidence is cited | **None established for NetFlow-v2**; the Engelen/Lanvin defects concern CICFlowMeter and do not transfer |
| Dependencies | D-009; inspect the author repository (`github.com/ZHF123775838/WSN-DCNN-SHAP`) before implementing; UNSW upload needs a new D-015 amendment | D-010; more NetFlow datasets need download and storage approval |
| Compute | GPU helps (Colab) | small networks; mostly CPU |

**Recommendation (D-022).** Neither paper's dataset carries the CICIDS2017 artifact evidence.
To test the same artifact groups with a second model family, add a labelled **adaptation of the
DCNN + self-attention architecture to the D-008 scope**. It would use the same groups, controls
and populations as §4, alongside the faithful Fang reproduction on UNSW-NB15. MES-DNN at
reduced scope then contributes a duplicate-leakage and cross-network audit, not a CICIDS2017
artifact test.

---

## 9. Execution order and dependencies

| Stage | Content | Where | Gate |
|---|---|---|---|
| 3B-0 | Implement the family-common population builder, view configs generated from the frozen file, the MON/RES/WED scorer, the temporal split builder (local) and the hierarchical bootstrap; tests; local smoke runs | laptop | protocol approved |
| 3B-1 | First Colab session: full test suite, seed-0 reproduction, benchmark | Colab | D-023; user uploads the zip and code bundle |
| 3B-2 | M1–M3 (55 fits) in batches of about 10; then M4 | Colab, then laptop for scoring | 3B-1 passed |
| 3B-3 | S1–S3, S5; S7 | Colab / laptop | after 3B-2 |
| 3B-4 | Temporal split built locally, index record uploaded; S4 | Colab | D-023 |
| 3B-5 | R4a map hand-checked; B1 | laptop | D-004, D-005 |
| 3B-6 | Analysis and report; then RES scored once (S6) | laptop | everything above frozen |
| 4 | DCNN (faithful + D-008 adaptation), then MES-DNN | Colab | D-009, D-022, D-010 |

---

## 10. Decisions requiring approval

| ID | Question | Evidence | Options | Recommendation | Impact |
|---|---|---|---|---|---|
| D-004 | Which corrected CICIDS2017? | WTMC2021 downloaded and verified; CNS2022 newer, not downloaded | WTMC2021 / CNS2022 / both | **WTMC2021 only** (cited paper; counts reconcile) | Unblocks R4a |
| D-005 | Label policy and column map for R4a | No row key; renamed columns; Friday has no DDoS-Attempted | Map + policy, then score / skip R4a | **Hand-checked 77-column map; DDoS→1, BENIGN→0, other labels excluded; original DDoS time window** | Unblocks B1/B2 |
| D-006 | Cross-schema transfer? | Schemas incompatible | None / written field map | **None for AE-XGBoost**; WED only as a same-schema extension | Removes R4b |
| D-007 | Statistics and track A | Two tracks approved; statistics were a proposal | §6 / alternatives | **Adopt §6** (seeds 0–4, hierarchical paired bootstrap, Holm on the primary family); track A optional (O4) | Freezes the analysis |
| D-009 | Fang split | Official partition matches Fang (2 rows unexplained) | Official / own split | **Official partition + track-B twin exclusion; inspect the repository first** | Stage 4 |
| D-010 | MES-DNN scope | ~150M flows for five networks; 1 acquired | Reduced / full | **Reduced; decide the extra networks before Stage 4** | Stage 4 |
| D-012 | Registry levels | v2 built; team never confirmed | Confirm / change | **Confirm v2 levels and the A/B/C/D group mapping, including the A-selection disclosure** | Groups are final only after this |
| D-020 *(new)* | Controls and SESOI | §3, §6.5 | as proposed / other margins | **Approve the frozen controls and SESOI (0.001 MCC, 0.1 pp FPR)** | Primary inference |
| D-021 *(new)* | AE epoch cap | D-018 ablated AE hit 100 (best 98) | Keep 100 / raise to 200 | **Keep 100 (paper range), report cap hits, S5 rerun at 200 where hit** | Convergence |
| D-022 *(new)* | Second model family on CICIDS2017 | §8 | Faithful Fang only / + D-008 adaptation | **Both, the adaptation clearly labelled** | Stage 4 |
| D-023 *(new)* | Independent populations and Drive scope | MON/RES/WED are in the authorized zip; the temporal split needs GLF timestamps | as proposed | **Use MON as confirmatory, RES sealed, WED optional; allow index-only split records on Drive** | 3B-1, 3B-4 |

---

## 11. Research integrity safeguards

- **Frozen design:** the groups and controls are frozen in a committed file, reproducible from
  train data (`--check`). Any change needs a new decision entry and a new file, never an edit.
- **Before training:** the family-common population is computed and committed. No validation
  or test metric of any 3A model is looked at before all mandatory fits finish.
- **Untouched populations:** RES is scored exactly once, after analysis of everything else.
- **Leakage safeguards** stay as they are: per-view twin exclusion, train-only fitting, pinned
  split, no test-driven tuning.
- **Integrity:** original artifacts are protected by SHA-256 (96 files); runs never overwrite.
- **Labelling:** every result is labelled confirmatory, pre-registered-on-inspected,
  sensitivity or exploratory. Author-reported numbers are never mixed with ours.
- **Test reporting:** environment-blocked tests are reported as blocked, never as passed.

## 12. Acceptance criteria for starting training (3B-2)

1. D-007, D-012, D-020, D-021 and D-023 approved and recorded. D-004/D-005 are needed only for R4a.
2. `configs/protocol/ablation_groups_3a.yaml` committed, and `--check` passes.
3. Family-common populations committed (expected: 33,134 validation / 33,038 test), and the 3B
   code tested locally, including a smoke run of one ablation view.
4. The full test suite passes on Colab, including the 16 audit tests blocked on this laptop.
5. The seed-0 Colab reproduction matches the laptop baseline (identical predictions, or
   documented differences within the same device class), and the timing benchmark is recorded.
6. No 3A model has been evaluated on any population before these criteria are met.
