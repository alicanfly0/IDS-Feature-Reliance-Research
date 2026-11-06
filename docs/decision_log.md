# Research decision log

Each entry records an ambiguity, the evidence, the options, and the decision. An
entry stays **OPEN** until the project team decides it. Nothing in Milestone 1
that depends on an open entry should start.

Evidence sources:

- Phase II submission `i232630_i232562_PHASE_II_CNET.pdf`
- `CNET_FULL_PAPER_AUDIT.md` (7 Nov 2026)
- the anchor PDFs in `../project/`, cited by physical page
- official dataset pages, checked 2026-11-07 (see `configs/datasets.yaml`)

Status values: OPEN · DECIDED · SUPERSEDED.

---

## D-001 NetFlow feature count: 43 vs 40 vs 39 — OPEN

**Evidence**

- Phase II (Step 2, Table II) calls NF-UNSW-NB15-v2 a "43-feature" schema and says Wardana used "uniform 43-feature NetFlow schema mapping".
- The UQ landing page says NF-UNSW-NB15-v2 has "43 extended NetFlow features".
- Wardana §4.1 (p.5) says "45 different features, but only 40 were used".
- Wardana Table 2 (p.5) lists exactly 39 NetFlow fields plus `Label`. We counted this from the PDF text. The list contains no IP or port fields.
- Wardana Table 6 (p.9) gives an input dimension of 39.

**Working hypothesis (unverified)**

- The CSV has 45 columns: 43 features plus `Label` plus `Attack`.
- Wardana dropped 5 of them: `IPV4_SRC_ADDR`, `L4_SRC_PORT`, `IPV4_DST_ADDR`, `L4_DST_PORT` and `Attack`.
- That leaves 39 inputs plus `Label`, which is 40 columns "used".
- If so, all three numbers are consistent and "43-feature mapping" in Phase II is wrong only as a description of the *model input*.

**Needed**

- The real CSV header.
- The list of 43 features on the UQ page or in the Sarhan et al. paper.

**Decision required**

- Which input set the MES-DNN reproduction uses. Wardana's 39 is the faithful choice.
- Whether Phase II's "43-feature" wording is corrected in Phase IV.

## D-002 SHAP on AE-XGBoost: latent codes vs original features — OPEN

**Evidence**

- Nezhadsistani's XGBoost is trained on the 40-dimensional AE latent codes (120→80→40; §3 and §4.2.1, pp. 3–5).
- Fig. 5 nevertheless shows SHAP plots labelled with raw CICFlowMeter names such as `min_seg_size_forward`, ACK Flag Count and Min Packet Length.
- The paper does not explain how attributions reach raw features.

**Options**

- **(a)** Explain the composite function `raw → encoder → XGBoost` with a model-agnostic explainer such as KernelExplainer or a permutation explainer. This is faithful but costly, and the background set matters.
- **(b)** Train a raw-feature XGBoost as a separate, declared proxy model and use TreeExplainer on it.
- **(c)** Report latent-code SHAP only, with no raw-feature claims.

**Rule regardless of the choice:** latent SHAP values must never be relabelled with raw feature names.

**Also open: Phase II's description of Paper 1's findings.**

- Phase II says `min_seg_size_forward` dominates "overwhelmingly". In the paper it appears in the *local* explanation. The global CICIDS2017 plot is led by ACK Flag Count and Min Packet Length.
- Phase II says Paper 1 "degraded substantially" across datasets. Paper 1 reports a leave-one-dataset-out F1 of 0.9089 and calls its generalization promising.
- Both are our interpretation, not the paper's, and must be worded that way.

## D-003 Input dimension of AE-XGBoost (120) — OPEN

- The AE input is 120-dimensional and includes one-hot categories (p.5).
- The CICIDS2017 DDoS subset has 78 features plus the label.
- The paper does not show how the 120 dimensions are composed across 5G-NIDD, CICIDS2017 and the 5G dataset.
- **Decision required:** reproduce on CICIDS2017 alone, with an input dimension set by our own preprocessing (declared as a deviation), or attempt the multi-dataset schema. The latter needs 5G-NIDD and the 5G dataset, which are not in this manifest.

## D-004 Engelen WTMC2021 corrected CICIDS2017 vs the CNS2022 update — OPEN

**Evidence**

- The project specification names Engelen's corrected CICIDS2017, which is the WTMC2021 paper [10].
- The WTMC2021 page (update dated 18/11/2022) points to a newer release at `.../CNS2022/index.html` as "the most recent version".
- Lanvin et al. [11] built further fixes on Engelen's extractor, at `gitlab.inria.fr/mlanvin/crisis2022`.

**Manifest status:** the manifest lists only WTMC2021. Adopting CNS2022 or Lanvin's version would be a substitution and needs a decision here first.

**Decision required:** which corrected version, or more than one as separate, labelled experiments.

## D-005 Correction-induced record and label changes — OPEN

**Evidence**

- Engelen's data is re-extracted from PCAP. Flows are re-segmented after the TCP appendix and RST fixes, and labels are revised, including new `X - Attempted` classes.
- There is no row-level key linking corrected rows to original rows.
- Engelen's own row counts exclude corrupted rows and rows with NaN features.
- The effective-flow sum in the page table is about 2.09M, against roughly 2.8M originally (our sum, not stated on the page).

**Consequences**

- "Same flows, corrected label" comparisons are impossible at row level.
- R4 (train on original, test on corrected) needs:
  - a shared column schema, because the modified CICFlowMeter may change columns;
  - a policy for `Attempted` classes: benign, a separate class, or excluded;
  - per-class reporting, because class totals change.
- Phase II R4 merges two questions. They are split here:
  - **R4a:** corrected-capture evaluation.
  - **R4b:** cross-dataset transfer.

**Decision required:** the `Attempted` policy, the column alignment rule, and whether R4a also retrains on corrected data.

## D-006 Incompatible cross-dataset schemas — OPEN

The four datasets use three different feature definitions:

| Dataset | Feature definition |
|---|---|
| CICIDS2017 (original and Engelen) | CICFlowMeter, roughly 78–80 features |
| UNSW-NB15 | Argus/Bro, 49 columns including labels |
| NF-UNSW-NB15-v2 | NetFlow v2, 43 features |

- Phase II Step 1 gives `d ∈ [43, 78]` as if the datasets shared one feature space. They do not.
- A model trained on one schema cannot be evaluated on another without explicit feature engineering, unit harmonization and label harmonization.
- NF-UNSW-NB15-v2 and UNSW-NB15 come from the same traffic in two representations. That makes a within-traffic schema comparison possible, but it is not cross-domain transfer.

**Decision required:** which cross-dataset pairs, if any, are in scope. The default proposal is to keep R4 to CICIDS2017 original→corrected (R4a) and add R4b only after a written field mapping.

## D-007 Split protocol: repeated splits vs 10-fold CV vs paper protocols — OPEN

**Phase II is internally inconsistent**

- Step 7 specifies a stratified 70/15/15 split.
- Step 9 runs Wilcoxon tests "across 10-fold cross-validation".

**The papers use different protocols**

| Paper | Protocol |
|---|---|
| Nezhadsistani | 5-fold CV |
| Wardana | 70/30, with 10% of train for meta-sampling and 10% of test for validation |
| Fang | 70/30 stated, plus 5-fold CV for tuning; the printed counts contradict the 70/30 (see D-009) |
| Engelen | 75/25 |

**Leakage risk:** random row splits leak in these datasets.

- CICIDS2017 has many exact duplicate rows and duplicated packets (Lanvin, about 5%).
- Flows from one attack session or host pair are near-identical.
- Fold scores from CV are not independent samples, which makes a plain Wilcoxon test over them optimistic.

**Implemented in `src/data/split.py`:**

- stratified random, group, temporal and predefined splits;
- disjointness checks;
- counts of exact feature-vector duplicates across splits;
- group-overlap counts.

**Proposed for decision**

- Reproduce each baseline under its own paper's protocol first (faithfulness).
- Run the audit comparisons (R1–R3) under one common protocol: repeated stratified splits over several seeds.
- Add a duplicate-aware or group-aware sensitivity check.
- Use paired differences with confidence intervals.

**Open choices:** the number of seeds, the grouping key (e.g. capture day, host pair, flow 5-tuple), and whether exact duplicates are removed before splitting.

## D-008 CICIDS2017 scope for each baseline — OPEN

- Nezhadsistani uses a 225,745-row DDoS subset with 78 features.
  - This row count is consistent with the Friday-afternoon DDoS file of the CSV release. That is a hypothesis to verify after download.
- Phase II cites [1] for "2.83 million flows across 15 classes", which is a misattribution.
- **Decision required:** reproduce on the DDoS subset (faithful), and/or extend to the full multi-class corpus as a declared extension.

## D-009 Fang UNSW-NB15 subset and split — OPEN

- Fang reports 92,998 normal and 16,353 DoS records.
  - Train: 55,998 + 12,264. Test: 37,000 + 4,089 (p.22).
  - That is about a 62/38 split, not the stated stratified 70/30.
- These counts closely resemble the Normal and DoS rows of the official `UNSW_NB15_training-set.csv` / `UNSW_NB15_testing-set.csv` partition. This is a hypothesis; the class counts must be measured after download.
- Fang names normal as the *positive* class (p.14), so metric polarity must be fixed explicitly.
- The author repository `github.com/ZHF123775838/WSN-DCNN-SHAP` claims to include the splits and code. It has not been accessed.

**Decision required:**

- whether to use the official partition (`predefined_split`), the author's released split, or our own split;
- whether to inspect the author repository before reimplementing.

## D-010 MES-DNN scale and the five NetFlow datasets — OPEN

- MES-DNN needs five networks: NF-UNSW-NB15-v2, NF-ToN-IoT-v2, NF-BoT-IoT-v2, NF-CSE-CIC-IDS2018-v2 and NF-UQ-NIDS-v2.
- The official totals are about 2.4M, 16.9M, 37.8M, 18.9M and 76.0M flows (UQ page).
- Only NF-UNSW-NB15-v2 is in the current manifest.
- Wardana's Table 3 counts are below the official totals for every network (e.g. N1 is 1,986,745 vs 2,390,275). No filtering step is described.

**Decision required:**

- a reduced scope (e.g. a single-network base model, or a fixed subsample) with declared hardware limits;
- or acquisition of all five, which needs storage and RAM sizing first.

## D-011 Row sanitization and constant columns — OPEN

- Phase II purges NaN/Infinity rows and rows with negative duration, and removes `Fwd URG Flags` / `Bwd URG Flags` as constant.
- Whether those columns are actually constant must be measured. The preprocessor drops columns that are constant **on the training partition**, rather than using a hard-coded list.
- Row filters are reported by `invalid_row_mask` and never applied silently.
- **Decision required:** drop vs impute for each rule, decided per dataset after inspection. Record the row counts removed.

## D-012 Artifact registry status of candidate features — OPEN

- Phase II's registry treats `Destination Port`, `Init_Win_bytes_*`, `Fwd Header Len`, `SYN Flag Count`, `Bwd Pkt Len Mean`, `Flow IAT Min`, `Flow Packets/s` and `Bwd Packets/s` as artifacts.
- The audit (§D2) shows the evidence is specific to a dataset and a mechanism:
  - Engelen: TCP-appendix shortcuts;
  - Lanvin: effects of duplicated packets;
  - `Destination Port` is a hypothesis only.
- No UNSW-NB15 artifact has been established by the uploaded papers.
- **Decision required:** registry schema and evidence levels (audit §D2 proposes `direct_error` / `shortcut_indicator` / `hypothesis`). Build the registry in Milestone 1 before any ARR@K is computed.

## D-013 Unverifiable Phase II citations — OPEN

- No full text was available for Bilal et al. [4], Wang et al. [5] or Ebrahimi et al. [6].
- Their reported numbers (e.g. "30 percentage-point Macro-F1 drop", "99.47% F1") and the claim that Wang's UNSW-NB15 SHAP flagged `Init_Win_bytes` are uncertified.
- `Init_Win_bytes` is a CICFlowMeter name. UNSW-NB15 uses `swin`/`dwin`, which is an extra inconsistency to check.
- **Decision required:** obtain the PDFs or drop or soften these claims in Phase IV.

## D-014 Python environment — OPEN

- The only Python on this machine is an embeddable CPython 3.11.9 build (`python311-embed`).
- Its `python311._pth` file disables `PYTHONPATH` and the working directory, and it has no `venv` module.
- `pytest` works because of `pyproject.toml`'s `pythonpath` setting. `python -m src.data.inspection` does not.

**Options**

- **(a)** Install standard CPython 3.11 and create `.venv`. This is recommended.
- **(b)** Run `pip install -e .` into the embedded interpreter, which changes the global environment.
- **(c)** Add `..\cnet project implementation` to `python311._pth`.

**Decision required** before Milestone 1, which also needs extra packages (xgboost, lightgbm, shap).
