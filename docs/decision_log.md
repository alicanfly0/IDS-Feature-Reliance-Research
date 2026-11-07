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
| D-007 | Evaluation design | **PARTIALLY APPROVED**; track-B split approved and implemented; statistics and track A pending |
| D-008 | First baseline dataset | **APPROVED** |
| D-009 | Fang subset and split | OPEN |
| D-010 | MES-DNN scale | OPEN |
| D-011 | Invalid rows | **APPROVED** for the initial DDoS experiment |
| D-012 | Artifact registry evidence levels | OPEN; Destination Port retained in the first baseline |
| D-013 | Unverifiable Phase II citations | OPEN |
| D-014 | Python environment | DECIDED |
| D-015 | Storage location (local only) | DECIDED; Amendment 1 PROPOSED, not authorized |
| D-016 | Compute: local CPU + Google Colab GPU | DECIDED (team requirement); benchmark note added |
| D-017 | AE-XGBoost adaptations vs the paper | DOCUMENTED (Milestone 1A) |

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

**Status of the parts (2026-11-08):**

- **Track B split: APPROVED and IMPLEMENTED** (Milestone 1A brief: fixed, reproducible, duplicate-aware 70/15/15, seed 42, zero duplicates across all three partition pairs).
- **Track B statistics** (seed count, bootstrap) and **track A**: still proposals. One model seed is run first; more seeds, track A and ablations come after the first results are reviewed.

### Track B (leakage-resistant) — exact procedure

1. **Rows:** the D-008 scope after the D-011 row rules, original CSV row positions kept as `source_row`.
2. **Feature set for duplicate detection:** exactly the columns the model receives. For the first baseline that is all 78 CICFlowMeter features, **including `Destination Port`** (D-012). If a later experiment removes a column, the groups must be recomputed, because fewer columns can make more rows identical.
3. **Duplicate policy:** keep all rows, but give identical feature vectors one group id (`split.content_groups`).
   - The id is the row's rank among the sorted distinct rows: exact (no hashing) and independent of library versions; `-0.0` is treated as `0.0`.
   - Every vector lives in exactly one partition; duplicates within a partition are kept, which preserves frequencies.
   - Within-partition deduplication is a sensitivity analysis, not the primary result.
4. **Conflicting labels:** groups whose identical vectors carry different labels are excluded from all partitions, with the count logged (`split.conflicting_groups`). The D-008 scope has none.
5. **Splitting algorithm:** `split.group_split(groups, fractions=(0.70, 0.15, 0.15), seed=42)`.
   - Distinct groups are shuffled with NumPy's legacy `RandomState(42).permutation` (stream frozen across NumPy versions).
   - The first 70% of groups go to train, the next 15% to validation, the rest to test.
   - Fractions apply to groups; row and class shares are measured and reported.
   - This replaced an earlier scikit-learn `GroupShuffleSplit` version, whose output is not guaranteed across library versions. Local and Colab runs must see the same test population.
6. **Leakage checks per run:**
   - `split.partition_overlap` must be 0 for train–val, train–test **and** val–test, on the raw features and again on the preprocessed model inputs.
   - The runner refuses to continue otherwise.
7. **Pinning:** the split fingerprint is fixed in `configs/experiments/ae_xgb_d008_trackB.yaml` (`expected_fingerprint`), and the split file is saved once per storage location (`<storage>/splits/`). Every later run and ablation must reproduce it exactly.
8. **Grouping strategy:** content groups, because MachineLearningCVE has no host, session or time keys. Host/session/time grouping via `TrafficLabelling` is a later sensitivity analysis.
9. **Seeds (proposal for later runs):**
   - partition seed 42, fixed;
   - model seeds {0, 1, 2, 3, 4}; the first run uses seed 0 only.
10. **Statistical comparison (proposal):**
    - mean ± SD across model seeds, descriptively;
    - paired differences on the fixed test set per seed, with a 95% CI from a cluster bootstrap over test content groups (2,000 resamples);
    - no Wilcoxon test over folds or seeds treated as independent samples.

**Measured on the real file** (`ddos.prepare`, asserted in `tests/test_real_data_smoke.py`):

- **Before the split:**
  - 225,745 rows → 36 invalid → 225,709 kept (DDoS 128,025 / BENIGN 97,684);
  - 223,080 distinct vectors (3,934 rows in duplicate groups);
  - 0 conflicting-label groups.
- **Partitions:**

  | | Train | Validation | Test |
  |---|---|---|---|
  | Rows | 157,998 (70.0%) | 33,834 (15.0%) | 33,877 (15.0%) |
  | DDoS | 89,577 | 19,215 | 19,233 |

  - Shared feature vectors: **0 / 0 / 0** for train–val / train–test / val–test.
  - Fingerprint: `50bd994880abbe151738993e299b90a6e50fb5ffae235a72677bb7813c447f44`.
- **Contrast:** a row-stratified random split of the same rows shares 900+ exact vectors between partitions (asserted).

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
- **First baseline (team instruction, 2026-11-08):** `Destination Port` is **retained** in the AE-XGBoost input as a candidate shortcut feature. Removing it is a later controlled experiment, not an established correction.

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

**Amendments:** none in effect.

### D-015 Amendment 1 — PROPOSED, NOT AUTHORIZED

To run the first AE-XGBoost baseline on Google Colab Free, the following would be transferred. **Nothing has been uploaded.**

| What | Size | Where | Purpose |
|---|---|---|---|
| `MachineLearningCSV.zip` (CICIDS2017 original; sha256 `c3f26274…727928`) | 235,102,953 B | your Google Drive, private, unshared folder `MyDrive/cnet-data/` | copied to the Colab VM each session, verified, Friday DDoS member extracted there |
| Code bundle `cnet_code_<hash>.zip` (`git archive` of one commit; no data) | < 1 MB | same folder | exact code for the run |
| Run outputs: split file, checkpoints, latent codes, models, predictions, metrics, logs | tens of MB per run | `MyDrive/cnet-runs/` | survive Colab disconnections |

**Effects:**

- The dataset is processed on Google's Colab VMs and stored in your Drive.
- No other dataset, no GeneratedLabelledFlows/PCAPs, and no personal files are transferred.
- Nothing is shared or re-hosted. CIC's terms ask for citation and do not permit re-hosting, so the folder must stay private.

**To authorize:** change this heading to "AUTHORIZED", add the date and who authorized it, and commit. Then set `D015_AMENDMENT_1_RECORDED = True` in the notebook.

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
- A notebook exists (`notebooks/colab_runner.ipynb`); Milestone 1A made it a runnable workflow.
- **Colab execution has not been run or verified.**

**Benchmark note (Milestone 1A, measured 2026-11-08 on the laptop CPU, real 157,998-row training partition):**

| Measured | Projected upper bound |
|---|---|
| AE: 0.92 s per epoch (618 batches of 256, input dimension 68) | 100 epochs ≈ 1.5 min |
| XGBoost: 9 ms per round on 40 latent features | 2,000 rounds ≈ 0.3 min |
| Data verify + rules + split + preprocessing: 12.8 s | — |

- **The full single-seed baseline therefore costs minutes of CPU.** The GPU benefit for this baseline is likely small, and session start-up plus transfer may dominate.
- **Decision for the team:** keep Colab as instructed, or authorize full runs of small baselines on the laptop CPU. The latter needs no cloud transfer, so no D-015 amendment.
- **Not changed unilaterally:** no full run has been made locally.

## D-017 AE-XGBoost reproduction: adaptations and gaps vs Nezhadsistani et al. 2026 — DOCUMENTED (2026-11-08)

**Wording.** Our model is a **documented adaptation**, not an exact reproduction. It differs in scope (one CICIDS2017 file, binary), input width and evaluation protocol.

| Element | Paper (section) | Ours | Type |
|---|---|---|---|
| Data scope | CIC-IDS2017 DDoS subset of 225,745 samples, trained jointly with 5G-NIDD and a 5G dataset (§4.1, Table 6) | Friday DDoS file only; 36 invalid rows removed (D-011) | Scope deviation |
| Preprocessing | Min-max scaling; one-hot/label encoding; missing values removed or imputed (§3.1) | D-011 row rules; train-only median imputation (no NaN remains after the rules), constant removal and min-max scaling | Consistent; train-only fitting is ours |
| AE input | 120 (numeric + one-hot, three datasets) (§4.2.1) | 68 = 78 features − 10 constant-on-train columns (measured on the full training partition) | Required adaptation (D-003) |
| AE widths | 120 → 80 → 40 → 80 → 120 | 68 → 80 → 40 → 80 → 68 (first layer widens, not compresses) | Paper hidden/latent widths kept |
| Activations | ReLU "in all layers" | ReLU hidden and latent; **linear output** | Gap: output activation unstated (test values can fall outside [0, 1]) |
| Optimizer | Adam, lr 0.001, batch 256 | Same | Paper |
| Epochs and stopping | "50–100 epochs", early stopping (§4.2.1) | max 100, patience 10 on validation reconstruction MSE, best weights restored | Gap: patience/monitor unstated |
| Loss | squared reconstruction error (Eq. 3) | MSE | Paper |
| Latent augmentation | Eq. 4 for minority-class **attacks**; σ, count and acceptance threshold unstated (§3.3) | Implemented, training-only, σ = 0.1 × per-dimension latent std, balance to 1:1, keep within the 95th percentile of real reconstruction errors, latent = E(x̃). **Disabled**: DDoS is the majority class (56.7% of training rows), so the paper's rule selects nothing | Gaps filled with labelled choices; not applied |
| XGBoost | Grid search over Table 5 ranges; selected values and tree count not reported | Fixed a priori inside Table 5: lr 0.11 (on the paper's grid), depth 6, α 0, λ 1, subsample 0.8, colsample 0.8; trees by validation early stopping (50 rounds, cap 2,000) | Gap: no grid search (compute and leakage-risk minimisation) |
| Validation | 5-fold CV (Table 7), also testing on synthetic samples (Table 6) | Track B: duplicate-aware 70/15/15 hold-out; validation for early stopping only; test untouched until evaluation; no synthetic test data | Deliberate deviation (D-007) |
| Threshold / positive class | not stated | 0.5 fixed a priori; DDoS = 1 | Ours |
| Metrics | Accuracy, precision, recall, F1, AUC | Plus macro-F1, MCC, confusion matrix, per-partition class counts | Superset |

**Comparisons:** author-reported numbers (e.g. CIC-IDS2017 F1 0.9993, Table 6) are quoted only as author-reported and are not directly comparable to track-B results.
