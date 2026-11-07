# Research decision log

Each entry records an ambiguity, the evidence, the options, and the decision. An
entry stays **OPEN** until the project team decides it. Nothing in Milestone 1
that depends on an open entry should start.

Evidence sources:

- Phase II submission `i232630_i232562_PHASE_II_CNET.pdf`
- `CNET_FULL_PAPER_AUDIT.md` (7 Nov 2026)
- `CNET_MILESTONE_0_INDEPENDENT_AUDIT.md` (7 Nov 2026)
- the anchor PDFs in `../project/`, cited by physical page
- official dataset pages, checked 2026-11-07 (see `configs/datasets.yaml`)

Status values: OPEN · APPROVED (team decision) · PARTIALLY APPROVED · DEFERRED · DECIDED (operational) · SUPERSEDED.

## Summary (2026-11-08, end of Milestone 0)

| ID | Topic | Status |
|---|---|---|
| D-001 | NetFlow 43 / 40 / 39 | **APPROVED** |
| D-002 | AE-XGBoost feature attribution | **DEFERRED** to the SHAP milestone |
| D-003 | AE-XGBoost input dimensionality | **APPROVED** |
| D-004 | Which corrected CICIDS2017 | OPEN |
| D-005 | Original vs corrected comparison | OPEN |
| D-006 | Cross-dataset schemas | OPEN |
| D-007 | Evaluation design | **PARTIALLY APPROVED**; exact procedure documented and demonstrated, awaiting sign-off |
| D-008 | First baseline dataset | **APPROVED** |
| D-009 | Fang subset and split | OPEN |
| D-010 | MES-DNN scale | OPEN |
| D-011 | Invalid rows | **APPROVED** for the initial DDoS experiment |
| D-012 | Artifact registry evidence levels | OPEN |
| D-013 | Unverifiable Phase II citations | OPEN |
| D-014 | Python environment | DECIDED |
| D-015 | Storage location (local only) | DECIDED; no amendments |
| D-016 | Compute: local CPU + Google Colab GPU | DECIDED (team requirement) |

---

## D-001 NetFlow feature count: 43 vs 40 vs 39 — APPROVED (2026-11-08)

**Decision.**

- **Model inputs:** use the **39 model inputs** in Wardana's Table 2. These are the 43 NetFlow-v2 dataset features minus the four identifiers `IPV4_SRC_ADDR`, `L4_SRC_PORT`, `IPV4_DST_ADDR` and `L4_DST_PORT`.
- **Keep the three counts distinct in all writing:**
  - **43** dataset features;
  - **40** columns used by Wardana: the 39 inputs plus `Label`;
  - **39** model inputs.
- **Phase IV:** correct the "43-feature" wording where it describes the model input.

**Evidence (from the downloaded data)**

- `NF-UNSW-NB15-v2.csv` has 45 columns: 43 NetFlow features plus `Label` and `Attack`.
- Wardana's 39 Table 2 inputs are *exactly* the 43 features minus the 4 identifiers (set comparison, `configs/datasets.yaml`).
- The publisher's BagIt SHA-1 checksums verify the file.
- Wardana §4.1 (p.5): "45 different features, but only 40 were used".
- Wardana Table 2 (p.5): 39 fields + `Label`, no IP or port fields.
- Wardana Table 6 (p.9): input dimension 39.
- Phase II (Step 2, Table II) called this a "uniform 43-feature NetFlow schema mapping". That describes the dataset, not the model input.

## D-002 SHAP on AE-XGBoost: latent codes vs original features — DEFERRED to the SHAP milestone

**Decision.**

- **Rule now:** the research audit must explain **original flow features**.
- **Not now:** no attribution method is chosen and no SHAP is computed in Milestone 0. The choice is made when the SHAP milestone starts.

**Evidence**

- Nezhadsistani's XGBoost is trained on the 40-dimensional AE latent codes (120→80→40; §3 and §4.2.1, pp. 3–5).
- Fig. 5 nevertheless shows SHAP plots labelled with raw CICFlowMeter names such as `min_seg_size_forward`, ACK Flag Count and Min Packet Length.
- The paper does not explain how attributions reach raw features.

**Options to choose from at the SHAP milestone**

- **(a) Composite-model explanation.** Explain `raw features → preprocessing → encoder → XGBoost` as one prediction function with a model-agnostic explainer (e.g. KernelExplainer or a permutation explainer) on a fixed, documented background and evaluation sample.
  - This is the only option that attributes the actual model to original features.
  - It is expensive, and the background set and feature dependence affect results.
- **(b) Separately labelled raw-feature proxy.** Train an XGBoost on the same preprocessed raw features and explain it with TreeExplainer.
  - It must always be labelled as a different model. It is a comparison or sanity check, not an explanation of AE-XGBoost.
- **(c) Latent-code SHAP only.** No raw-feature claims; not sufficient for ARR@K.

**Rule regardless of the choice:** latent SHAP values are never relabelled with raw feature names.

**Also recorded: Phase II's description of Paper 1's findings**

- Phase II says `min_seg_size_forward` dominates "overwhelmingly". In the paper it appears in the *local* explanation; the global CICIDS2017 plot is led by ACK Flag Count and Min Packet Length.
- Phase II says Paper 1 "degraded substantially" across datasets. Paper 1 reports a leave-one-dataset-out F1 of 0.9089 and calls its generalization promising.
- Both are our interpretation, not the paper's, and must be worded that way.

## D-003 Input dimension of AE-XGBoost — APPROVED (2026-11-08)

**Decision.**

- **Input dimension:** for the CICIDS2017-only reproduction, the autoencoder input dimension is whatever our train-fitted preprocessing actually produces on the D-008 scope.
  - All 78 features are numeric, so there is no one-hot expansion.
  - Ten columns are constant across the whole Friday DDoS file and are therefore also constant on any training partition: `Bwd PSH Flags`, `Fwd URG Flags`, `Bwd URG Flags`, `CWE Flag Count` and the six bulk-rate columns. The input is therefore **at most 68** features.
  - The exact number is fixed on the training partition and recorded in each run record.
- **Architecture:** keep the paper's architecture wherever technically justified: encoder → 80 → 40 latent, symmetric decoder, ReLU, Adam with lr 0.001, batch 256, early stopping.
- **Reporting:** report every modification next to the paper's value.
- **No exact-reproduction claim:** we do not claim an exact reproduction. Wording: "documented reproduction/adaptation of Nezhadsistani et al. on the CICIDS2017 DDoS subset".

**Evidence and implications**

- The paper's AE input is 120-dimensional and includes one-hot attributes (p.5).
- The paper doesn't show how the 120 dimensions are composed across 5G-NIDD, CICIDS2017 and the 5G dataset. The two 5G datasets are not in our manifest.
- The CICIDS2017 DDoS file has 78 features and no categorical columns, so a 120-wide input can't be reconstructed from it.
- **Reproducibility consequence:** the first layer differs (≤68 → 80 instead of 120 → 80, so the first hidden layer is wider than the input, not a compression). Our results are comparable to the paper's CICIDS2017 row (Table 6) only as an adaptation, with the scope difference stated. Whether to keep 80 or scale the layer widths is an architecture choice to make, justify and report in Milestone 1.

## D-004 Engelen WTMC2021 corrected CICIDS2017 vs the CNS2022 update — OPEN

**Evidence**

- The project specification names Engelen's corrected CICIDS2017, which is the WTMC2021 paper [10].
- The WTMC2021 page (update dated 18/11/2022) points to a newer release at `.../CNS2022/index.html` as "the most recent version".
- Lanvin et al. [11] built further fixes on Engelen's extractor, at `gitlab.inria.fr/mlanvin/crisis2022`.

**Manifest status:** the manifest lists only WTMC2021, and that is what was downloaded and verified on 2026-11-07. CNS2022 was not downloaded. Adopting CNS2022 or Lanvin's version would be a substitution and needs a decision here first.

**Decision required:** which corrected version, or more than one as separate, labelled experiments. Does not block the first DDoS baseline.

## D-005 Correction-induced record and label changes — OPEN

**Evidence**

- Engelen's data is re-extracted from PCAP. Flows are re-segmented after the TCP appendix and RST fixes, and labels are revised, including new `X - Attempted` classes.
- There is no row-level key linking corrected rows to original rows.
- Engelen's own row counts exclude corrupted rows and rows with NaN features.

**Consequences**

- "Same flows, corrected label" comparisons are impossible at row level.
- R4 (train on original, test on corrected) needs:
  - a shared column schema;
  - a policy for `Attempted` classes: benign, a separate class, or excluded;
  - per-class reporting, because class totals change.
- Phase II R4 merges two questions. They are split here:
  - **R4a:** corrected-capture evaluation.
  - **R4b:** cross-dataset transfer.

**Measured (2026-11-07, `results/inspection/engelen_*`)**

- **Size and counts:**
  - 2,100,814 rows over 5 day files, 25.8% fewer than the original 2,830,743. Engelen reports 25.9% TCP appendices.
  - 25 labels, 10 of them `- Attempted` (9,144 rows).
  - Measured counts minus the 793 rows containing Infinity/NaN equal the landing-page table exactly, class by class.
- **Column alignment needs a hand-checked map.** Engelen's file has 84 columns, no duplicated `Fwd Header Length`, and many renamed columns, e.g.:
  - `Source IP` → `Src IP`
  - `Total Fwd Packets` → `Total Fwd Packet`
  - `Init_Win_bytes_forward` → `FWD Init Win Bytes`
  - `min_seg_size_forward` → `Fwd Seg Size Min`

  The alignment rule must therefore be an explicit, hand-checked name map (77 shared features expected), not a positional match.
- **Possible linking key.** Both the corrected files and the original `TrafficLabelling` files carry Flow ID / IPs / ports / Timestamp. Flow-tuple + time matching is possible in principle. It is still not a row key, because flows were re-segmented.

**Decision required:** the `Attempted` policy, the column map, and whether R4a also retrains on corrected data.

## D-006 Incompatible cross-dataset schemas — OPEN

| Dataset | Feature definition |
|---|---|
| CICIDS2017 (original and Engelen) | CICFlowMeter: 78 features (original MachineLearningCVE) vs 77 renamed features + 6 identifiers (Engelen) |
| UNSW-NB15 | Argus/Bro, 49 columns including labels |
| NF-UNSW-NB15-v2 | NetFlow v2, 43 features |

- Phase II Step 1 gives `d ∈ [43, 78]` as if the datasets shared one feature space. They do not.
- A model trained on one schema cannot be evaluated on another without explicit feature engineering, unit harmonization and label harmonization.
- NF-UNSW-NB15-v2 and UNSW-NB15 come from the same traffic in two representations. That allows a within-traffic schema comparison, but it is not cross-domain transfer.

**Decision required:** which cross-dataset pairs, if any, are in scope. Default proposal: R4 limited to CICIDS2017 original → corrected (R4a); R4b only after a written field map.

## D-007 Evaluation design — PARTIALLY APPROVED (2026-11-08)

**Approved by the team**

- **Two distinct tracks:**
  - **A. Paper-comparable.** Reproduce the original paper's validation protocol as faithfully as possible, with every deviation documented.
  - **B. Leakage-resistant audit.** A duplicate-aware protocol with disjoint train / validation / test partitions. Exact-duplicate rates and cross-split overlap are recorded for every run.
- **Same test set:** comparable ablation experiments use the same held-out test data.
- **Train-only fitting:** preprocessing and augmentation (e.g. Nezhadsistani's latent-space oversampling) are fitted on training data only.
- **No fold-based statistics:** dependent cross-validation folds are never treated as independent statistical observations.

**Before D-007 is marked fully decided,** the team signs off on the exact procedure below. It is a proposal, documented and demonstrated on real data, not yet approved.

### Proposed exact procedure — Track B (leakage-resistant)

1. **Rows:** the D-008 scope after the D-011 row rules: 225,709 rows, original source positions kept.
2. **Feature set for duplicate detection:** exactly the columns the model receives. Today that is all 78 CICFlowMeter features. If D-012 removes any column (e.g. `Destination Port`) from the input, the groups must be recomputed, because fewer columns can make more rows identical.
3. **Duplicate policy:** keep all rows, but group identical feature vectors (`split.content_groups`, a 64-bit row hash). Every vector then lives in exactly one partition. Duplicates within a partition are kept, which preserves the class and traffic frequencies.
   - Groups whose identical vectors carry different labels are listed and excluded from all partitions. There are none in the D-008 scope.
   - Within-partition deduplication is a sensitivity analysis, not the primary result.
4. **Splitting algorithm:** `split.group_split(groups, fractions=(0.70, 0.15, 0.15), seed=42)`. This runs scikit-learn `GroupShuffleSplit` twice: 70% of groups to train, then the remaining groups split 50/50 into validation and test.
   - Fractions apply to groups, so row fractions and class shares are measured and reported, not assumed.
5. **Grouping strategy:** content groups, because MachineLearningCVE has no host, session or time keys. A host/session or time-based grouping using `TrafficLabelling` identifiers is a later sensitivity analysis. It needs a join between the two CSV releases, which is not built.
6. **Seeds:**
   - **Partition seed:** 42, one fixed train/val/test partition shared by all comparable experiments and ablations.
   - **Model seeds:** {0, 1, 2, 3, 4} for initialisation, augmentation and XGBoost randomness. The number 5 is a proposal.
7. **Statistical comparison:**
   - Report each metric as mean ± SD across the 5 model seeds, descriptively.
   - To compare two conditions (e.g. full vs ablated features), compute paired differences on the fixed test set per model seed.
   - Give a 95% CI from a **cluster bootstrap over test content groups** (resampling groups, not rows; 2,000 resamples proposed).
   - No Wilcoxon test over folds or seeds treated as independent samples.
8. **Leakage check per run:** `cross_split_duplicates` must be 0 for validation and test. A run with a non-zero value is invalid unless the exception is documented.

**Demonstration on real data** (`tests/test_real_data_smoke.py::test_friday_ddos_row_rules_and_duplicate_aware_split`, passing):

- **Groups:** 223,080 distinct feature vectors among the 225,709 rows (3,934 rows sit in duplicate groups; the largest group has 118 rows); no conflicting labels.
- **Track-B split, seed 42:**
  - 157,994 / 33,819 / 33,896 rows (70.0 / 15.0 / 15.0%);
  - DDoS share 0.568 / 0.564 / 0.568 against 0.567 overall;
  - **0 validation and 0 test rows share a feature vector with training.**
- **Contrast:** a row-stratified random split of the same rows (seed 42) leaks **498** validation and **486** test rows with exact training twins.

### Proposed exact procedure — Track A (paper-comparable, Nezhadsistani)

- **Protocol:** 5-fold cross-validation as in the paper (Table 7).
  - The fold type isn't stated in the paper; we propose `StratifiedKFold(n_splits=5, shuffle=True, random_state=42)` and declare it as a deviation.
- **Training fold only:** preprocessing and latent-space augmentation are fitted on the training fold only.
- **Reporting:** fold metrics as mean ± SD, descriptively, next to the paper's values. Report each fold's cross-split duplicate count, so readers can see how much the paper protocol leaks.

**Measured duplication** (2026-11-07, `results/inspection/`). "Content duplicates" means identical rows once labels and identifier columns are ignored.

| Data | Content duplicates |
|---|---|
| NF-UNSW-NB15-v2, on Wardana's 39 inputs | 90.1% of rows (2,153,276), no conflicting labels |
| UNSW-NB15 training-set (`id` ignored) | 42.4% |
| UNSW-NB15 testing-set (`id` ignored) | 34.5% |
| UNSW-NB15 full CSVs, per file | 9.3–33.9% |
| CICIDS2017 MachineLearningCVE, per day | 2.0% (Friday DDoS) to 58.3% (Friday PortScan) |
| Engelen corrected CICIDS2017, per day | 3.9% (Wednesday) to 32.4% (Friday; 596 conflicting-label groups) |

- 10.4% of official UNSW-NB15 testing-set rows have an exact training twin.
- Under Phase II's random stratified 70/15/15 on NF-UNSW-NB15-v2, 93.5% of test rows have a training twin (measured 2026-11-07).

**Background:**

- Phase II is internally inconsistent: Step 7 uses a stratified 70/15/15 split, Step 9 a Wilcoxon over 10-fold CV.
- The papers use different protocols:
  - Nezhadsistani: 5-fold CV;
  - Wardana: 70/30 with meta-sampling and validation subsets;
  - Fang: the official UNSW partition (D-009);
  - Engelen: 75/25.

## D-008 First baseline dataset — APPROVED (2026-11-08)

**Decision.** The initial AE-XGBoost experiment uses the CICIDS2017 Friday-afternoon DDoS subset, `MachineLearningCVE/Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv`:

- 225,745 original rows: 128,027 DDoS and 97,718 BENIGN;
- binary classification, **DDoS = positive class (1)**, BENIGN = 0;
- documented as a limited scope, separate from the full CICIDS2017 release (2,830,743 rows, 15 labels).

**Evidence:**

- Nezhadsistani used a 225,745-row DDoS subset with 78 features + label. The file matches exactly: 79 columns.
- Phase II attributes "2.83 million flows across 15 classes" to [1]. That is a misattribution; [1] used only this file.
- Before each run, the extracted CSV is checked against its zip member's CRC, and the zip against the manifest sha256 and CIC's MD5 (real-data test).

Extending to the full multi-class corpus would be a separate, declared extension.

## D-009 Fang UNSW-NB15 subset and split — OPEN

- **Fang's counts:** 92,998 normal and 16,353 DoS records. Train 55,998 + 12,264; test 37,000 + 4,089 (p.22). That is about a 62/38 split, not the stated stratified 70/30.
- **Measured:** the official partition holds:

  | File | DoS | Normal |
  |---|---|---|
  | `UNSW_NB15_training-set.csv` | 12,264 | 56,000 |
  | `UNSW_NB15_testing-set.csv` | 4,089 | 37,000 |

  Fang's DoS counts and test Normal count match exactly; train Normal is 2 short. Fang evidently used the official partition. The 2 missing rows are unexplained.
- **Leakage in that partition (Normal/DoS only):**
  - 202 of 4,089 DoS test rows (4.9%) and 1,193 of 37,000 Normal test rows (3.2%) have an exact Normal/DoS training twin.
  - Against the whole training set, 49% of DoS test rows have a twin, mostly labelled as other attack classes.
- **Polarity:** Fang names normal as the *positive* class (p.14), so metric polarity must be fixed explicitly.
- **Author repository:** `github.com/ZHF123775838/WSN-DCNN-SHAP` claims to include the splits and code. It has not been accessed.

**Decision required:** which split (official partition, the author's, or ours), and whether to inspect the author repository first.

## D-010 MES-DNN scale and the five NetFlow datasets — OPEN

- MES-DNN needs five networks: NF-UNSW-NB15-v2, NF-ToN-IoT-v2, NF-BoT-IoT-v2, NF-CSE-CIC-IDS2018-v2 and NF-UQ-NIDS-v2.
- The official totals are about 2.4M, 16.9M, 37.8M, 18.9M and 76.0M flows (UQ page). Only NF-UNSW-NB15-v2 is in the manifest.
- Wardana's Table 3 counts are below the official totals for every network (e.g. N1 is 1,986,745 vs 2,390,275). No filtering step is described.

**Decision required:** reduced scope (single network or fixed subsamples, with declared hardware limits) or acquisition of all five. Acquiring all five needs storage/RAM sizing and, under D-015, a storage decision.

## D-011 Invalid row handling — APPROVED for the initial DDoS experiment (2026-11-08)

**Decision (D-008 scope):**

1. **Rules:** exclude rows matching these explicit rules, applied with `preprocess.invalid_row_mask(df, nonnegative_cols=("Flow Duration",))`:
   - any missing value;
   - any infinite value;
   - negative `Flow Duration`.
2. **Logging:** log the count per rule, the class counts before and after, and the excluded source row positions in the run record.
3. **Provenance:** keep original source row positions (the DataFrame index, carried as `source_row`).
4. **Sentinels:** `Init_Win_bytes_forward/backward = -1` is a documented "not observed" sentinel and is **not** a rule. Rows are never removed because of it.
5. **Constant columns:** detected on the **training partition only** (`TrainOnlyPreprocessor`).
6. **No silent removal:** any further removal needs a new, logged rule recorded here first.

**Measured effect** (asserted in `tests/test_real_data_smoke.py`):

| Rule | Rows |
|---|---|
| missing | 4 |
| infinite | 34 (30 `Flow Bytes/s` + 34 `Flow Packets/s` cells) |
| negative `Flow Duration` | 2 |
| **any rule (unique rows)** | **36**: 34 BENIGN, 2 DDoS |

- **Before → after:** DDoS 128,027 → 128,025; BENIGN 97,718 → 97,684; total 225,745 → 225,709.
- **Sentinels kept:** all 32,925 forward `-1` sentinels. Of the 88,299 backward `-1` sentinels, 88,274 are kept; the other 25 sit in rows removed by the missing/infinite/negative rules, not because of the sentinel.

**Other datasets (still OPEN):** the same question for full CICIDS2017, Engelen, UNSW-NB15 and NF-UNSW-NB15-v2 is decided per dataset when their experiments start. Measured facts:

- **CICIDS2017, all 8 days:**
  - constant in every day file: `Bwd PSH Flags`, `Bwd URG Flags` and the six bulk-rate columns; `Fwd URG Flags` is **not** constant, contrary to Phase II;
  - Infinity in `Flow Bytes/s` (1,509) and `Flow Packets/s` (2,867);
  - `Init_Win_bytes_*` = -1 in 1,001,189 / 1,441,552 rows;
  - negative `Flow Duration` in 115 rows; negative `Fwd Header Length` / `min_seg_size_forward` in 35 rows (registry candidates, D-012).
- **UNSW-NB15 full CSVs:** `ct_flw_http_mthd` and `is_ftp_login` are mostly empty in files 2–4; `attack_cat` needs whitespace and Backdoor/Backdoors normalization.

## D-012 Artifact registry status of candidate features — OPEN

- Phase II's registry treats `Destination Port`, `Init_Win_bytes_*`, `Fwd Header Len`, `SYN Flag Count`, `Bwd Pkt Len Mean`, `Flow IAT Min`, `Flow Packets/s` and `Bwd Packets/s` as artifacts.
- The paper audit (§D2) shows the evidence is specific to a dataset and a mechanism:
  - Engelen: TCP-appendix shortcuts;
  - Lanvin: duplicated-packet effects;
  - `Destination Port` is a hypothesis only.
- No UNSW-NB15 artifact has been established by the uploaded papers.
- **Decision required:** registry schema and evidence levels (`direct_error` / `shortcut_indicator` / `hypothesis`). Build the registry before any ARR@K is computed.
- **Interaction with D-007:** removing a column from the model input changes the duplicate groups.

## D-013 Unverifiable Phase II citations — OPEN

- No full text was available for Bilal et al. [4], Wang et al. [5] or Ebrahimi et al. [6].
- Their reported numbers (e.g. "30 percentage-point Macro-F1 drop", "99.47% F1") and the claim that Wang's UNSW-NB15 SHAP flagged `Init_Win_bytes` are uncertified.
- `Init_Win_bytes` is a CICFlowMeter name; UNSW-NB15 uses `swin`/`dwin`.
- **Decision required:** obtain the PDFs or drop or soften these claims in Phase IV.

## D-014 Python environment — DECIDED (2026-11-07)

- Standard python.org CPython 3.11.9 (per-user install).
- Venv at `.venv` in the project folder, created by `scripts/setup_env.ps1`, which installs `requirements.txt` and the package in editable mode and runs the tests.
- Windows commands go through `run.cmd`, which needs no activation.
- The embeddable Python, whose `._pth` file blocked imports, is left untouched.
- For Linux/Colab see D-016 and `docs/COLAB_EXECUTION_PLAN.md`.

## D-015 Storage location — DECIDED (2026-11-07)

**Decision (user).** Everything stays local, inside the project folder:

- datasets in `data/raw/<dataset id>/`, matching `local_dir` in `configs/datasets.yaml`;
- prepared data in `data/processed/`;
- the environment in `.venv/`.

All three are Git-ignored. **No dataset, checkpoint or private file is uploaded to any cloud service.**

**Note.** The folder's path is under `OneDrive\Desktop`. Whether OneDrive syncs it depends on the user's OneDrive settings, which are outside this repository.

**Amendments:** none.

- `docs/COLAB_EXECUTION_PLAN.md` §5 proposes a Google Drive arrangement for Colab runs. It takes effect only when the user authorizes it and records it here as **D-015 Amendment 1**: what is stored, where, who can access it, and the date.

## D-016 Compute architecture: local CPU development + Google Colab GPU — DECIDED (2026-11-08, team requirement)

**Decision.**

- **Local machine:** code is developed and tested locally on Windows 11 with CPU only (Dell Latitude 7430, i7-1265U, 16 GB RAM, Intel Iris Xe; no CUDA).
- **Colab:** computationally expensive training and evaluation run on Google Colab GPU runtimes from Milestone 1 onward.
- **Design constraints:**
  - free-tier Colab;
  - no guaranteed GPU;
  - sessions may disconnect;
  - a thin notebook that calls the repository's Python modules; no science in notebook cells.

**Status:**

- The plan is written (`docs/COLAB_EXECUTION_PLAN.md`).
- An environment recorder exists (`src/env.py`, tested locally).
- A notebook scaffold exists (`notebooks/colab_runner.ipynb`).
- **Colab execution has not been run or verified.**
