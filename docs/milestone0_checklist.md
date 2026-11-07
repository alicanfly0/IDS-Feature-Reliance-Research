# Milestone 0 validation checklist

Milestone 0 covers the repository, provenance, data acquisition and data
tooling. **No model has been trained and no experimental result exists.** The
numbers below are descriptive facts about the released files, measured by
`src.data.inspection`. Reports are in `results/inspection/`.

Status values: PASS (checked, with the command) · BLOCKED (needs data or a
decision) · TODO.

Last run: 2026-11-08, Python 3.11.9 (python.org build in the project venv, see D-014). **Milestone 0: complete.**

## Repository

| # | Check | Status | Evidence |
|---|---|---|---|
| R1 | Working directory inspected before changes; existing files preserved | PASS | Directory was empty at start; no files overwritten |
| R2 | Layout matches the agreed structure (`configs/ data/ src/{data,models,audit,evaluation} tests/ results/ paper/`) plus `docs/`, `scripts/` | PASS | `ls -R` |
| R3 | Raw/processed data, CSV/PCAP/ZIP, model weights Git-ignored | PASS | `git check-ignore`; `git status` shows no data files |
| R4 | Dependencies pinned to validated versions | PASS | `requirements.txt`; Milestone 1 packages listed but not pinned |
| R5 | Isolated environment | PASS | D-014: python.org CPython 3.11.9 + `.venv` in the project folder via `scripts/setup_env.ps1` |

## Provenance and acquisition

| # | Check | Status | Evidence |
|---|---|---|---|
| P1 | Manifest covers the 4 datasets with official source, version, files, license, citation, schema, labels, experiments | PASS | `tests/test_manifest.py` |
| P2 | No mirror used; every download from the official host | PASS | `test_no_mirror_used_as_source`; URLs in `configs/datasets.yaml` |
| P3 | Download destinations confirmed | PASS | D-015: `data/raw/<dataset id>/` |
| P4 | CICIDS2017 original downloaded (MachineLearningCSV.zip, GeneratedLabelledFlows.zip) | PASS | Sizes, sha256 recorded; **publisher MD5 verified** for both |
| P5 | UNSW-NB15 downloaded (9 CSVs from the official SharePoint) | PASS | Sizes match the server, sha256 recorded |
| P6 | NF-UNSW-NB15-v2 downloaded (UQ RDM) | PASS | Size, sha256 recorded; **publisher BagIt SHA-1 verified** |
| P7 | Engelen WTMC2021 `dataset.zip` downloaded | PASS | Exact server size, sha256 recorded, every zip member CRC verified. A first attempt was corrupted by two overlapping downloads and replaced |
| P8 | All files re-verifiable without assistance | PASS | `.\run.cmd -m src.data.acquire verify all` |
| P9 | License terms | PASS (3) / BLOCKED (1) | CIC: cite paper; UNSW: academic use granted; UQ: "Permitted Re-Use with Commercial Use Restriction"; Engelen: no licence text on the pages or in the zip (cite the paper, do not re-host; ask the authors if redistribution is ever needed) |

## Data tooling

| # | Check | Status | Evidence |
|---|---|---|---|
| T1 | Inspection: schema, shape, labels, missing/inf/negative, duplicates (incl. identifier-free content duplicates), conflicting labels, types, leakage candidates | PASS | `tests/test_inspection.py` |
| T2 | Reader handles real release quirks: whitespace and repeated column names, `Infinity`, cp1252 and U+FFFD labels, UTF-8 BOM, header-less files with a names file | PASS | inspection tests + real runs |
| T3 | Preprocessing statistics from the training partition only; source never mutated; unseen categories safe; row rules report only | PASS | `tests/test_preprocess.py` |
| T4 | Splits deterministic, disjoint, complete; group / temporal / predefined; cross-split duplicate and group-overlap checks; fingerprinted save/load | PASS | `tests/test_split.py` |
| T5 | Download/verify/extract: size, sha256 and publisher MD5 checks; zip path-traversal refused; Windows-unsafe names (trailing spaces) sanitized and logged | PASS | `tests/test_acquire.py` |
| T6 | Full suite | PASS | `.\run.cmd -m pytest -q -rs -W default`: **79 passed** (77 unit tests + 2 real-data tests), 0 skipped, 0 warnings. On a copy without data: 77 passed, 2 skipped. Independent reviewer, before finalization: 72 passed, 1 skipped |
| T7 | Setup and every step reproducible without assistance | PASS | `scripts\setup_env.ps1`, `run.cmd`, `src.data.acquire`, `scripts\inspect_all.ps1` |

## Independent audit corrective pass (2026-11-07)

Findings from `CNET_MILESTONE_0_INDEPENDENT_AUDIT.md` (verdict: pass with conditions):

| # | Finding | Status | Fix and evidence |
|---|---|---|---|
| F1 | Undeclared text feature silently became an all-NaN column | FIXED | `TrainOnlyPreprocessor` raises `TypeError` naming the column, at fit and at transform; `transform` refuses non-finite output. 4 regression tests in `tests/test_preprocess.py` |
| F2 | `load_split` accepted edited seed/source metadata | FIXED | Saved splits carry a digest over the whole record; `load_split(expected_source=…, n_rows=…)` also checks dataset identity and row count. 3 regression tests in `tests/test_split.py`. Integrity check, not authenticity |
| F3 | `configs/base.yaml` not connected to execution | FIXED | `src/config.py` overlays an experiment file on `base.yaml`, rejects unimplemented settings, builds the preprocessor, asserts no label/identifier reaches the input, writes a run record. `tests/test_config.py` (10) |
| F4 | Real-data smoke check not in the repository | FIXED | `tests/test_real_data_smoke.py` + `configs/experiments/smoke_unsw_official.yaml`: checksum-verified UNSW official partition → saved/reloaded split → train-only fit → transform → finite/schema/leakage assertions; skips without data |
| F5 | Absolute local paths in reports; personal registration metadata in manifest | FIXED | Inspection writes repo-relative paths and its own UTF-8 `.txt` (`--txt`). The 28 existing reports were rewritten in place; only path lines changed, no data re-read. Registrant name removed from `configs/datasets.yaml` |

## Finalization (2026-11-08)

| # | Check | Status | Evidence |
|---|---|---|---|
| Z1 | Approved decisions recorded (D-001, D-003, D-008, D-011 APPROVED; D-007 PARTIALLY APPROVED; D-002 DEFERRED; D-016 added) | PASS | `docs/decision_log.md` summary table |
| Z2 | D-011 rules on the D-008 scope: 36 rows excluded with logged counts, source positions kept, `-1` sentinels kept | PASS | `test_friday_ddos_row_rules_and_duplicate_aware_split` |
| Z3 | D-007 track B: duplicate-aware split gives 0 cross-split duplicates (random split: 498 / 486) | PASS | same test; `split.content_groups` + `group_split` |
| Z4 | Environment, device and seed recording works on Windows CPU; no Windows-only requirement for Colab | PASS | `tests/test_env.py`; `python -m src.env` |
| Z5 | Colab execution plan and notebook scaffold | PASS (written) / **NOT VERIFIED on Colab** | `docs/COLAB_EXECUTION_PLAN.md`, `notebooks/colab_runner.ipynb` (Drive/data cells disabled pending D-015 Amendment 1) |
| Z6 | All 13 data files re-verified (size, sha256, publisher MD5); manifest valid | PASS | `src.data.acquire verify all`, `src.data.manifest` (0 problems) |
| Z7 | Committed/zipped files contain no datasets, binaries, secrets, registration details or local absolute paths | PASS | Scan of 98 files: 0 problems; largest file 36 KB |

## Checks on the real data

| # | Check | Status | Result |
|---|---|---|---|
| B1 | Inspection reports saved for every downloaded file | PASS | 28 file reports (×2: `.txt` + `.json`) in `results/inspection/` |
| B2 | Column names, label columns, feature counts confirmed | PASS | See below and the manifest's measured blocks |
| B6 | Engelen counts reconcile with the publisher's table | PASS | Measured minus the 793 Inf/NaN rows = landing-page table, class by class (D-005) |
| B3 | Duplicate rates; official-split cross-duplicates | PASS | D-007 table |
| B4 | Paper 1 subset = Friday DDoS file; Fang counts = official partition | PASS | D-008, D-009 |
| B5 | Constant columns, infinities, negatives measured | PASS | D-011 |

**What the data confirmed or corrected:**

- **NF-UNSW-NB15-v2 (D-001):**
  - 45 columns: 43 features + Label + Attack; 2,390,275 rows.
  - Wardana's 39 inputs = the 43 features minus the 4 IP/port fields (exact match).
- **CICIDS2017 (D-008):**
  - The full release has 2,830,743 rows and 15 labels.
  - MachineLearningCVE has 78 features + Label.
  - The Friday-afternoon DDoS file has exactly Paper 1's 225,745 rows.
- **Fang's split (D-009):** the official UNSW-NB15 partition contains Fang's DoS counts (12,264 / 4,089) and test Normal count (37,000) exactly. Train Normal is 56,000 vs Fang's 55,998.
- **Duplication (D-007):**
  - NF-UNSW-NB15-v2: 90.1% of rows repeat another row on Wardana's 39 inputs.
  - UNSW-NB15 training/testing sets: 42.4% / 34.5% duplicated once `id` is ignored.
  - 10.4% of the official UNSW test rows have an exact training twin.
- **Phase II constant-column claim (D-011):** `Fwd URG Flags` is not constant in CICIDS2017; 8 other columns are constant in every day file.
- **Engelen corrected CICIDS2017 (D-005):**
  - 2,100,814 rows (25.8% fewer than the original) and 25 labels including 10 "Attempted" classes.
  - Many columns are renamed relative to the original release, so a hand-checked column map is required.

## Remaining before the first Milestone 1 run (AE-XGBoost, D-008 scope)

1. **D-007 sign-off.** The exact track-A/B procedure is documented and demonstrated, but not yet approved.
2. **D-015 Amendment 1.** Any data on Colab/Drive needs it. **GitHub remote** configured by the team.
3. **D-012 decision on `Destination Port`** in the model input. It changes the duplicate groups (D-007).
4. **Packages:** pin and install xgboost and torch locally (CPU). Run the test suite on Colab once (first real Colab verification).

Still OPEN for later experiments: D-004, D-005, D-006, D-009, D-010, D-012, D-013. D-002 is deferred to the SHAP milestone.
