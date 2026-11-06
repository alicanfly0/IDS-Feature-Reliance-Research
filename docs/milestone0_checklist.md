# Milestone 0 validation checklist

Milestone 0 covers the repository, provenance and data tooling only. **No
dataset has been downloaded, no model has been trained, and no experimental
result exists.**

Status values: PASS (checked, with the command) · BLOCKED (needs data or a
decision) · TODO.

Last run: 2026-11-07, Python 3.11.9 (embeddable build, see D-014).

## Repository

| # | Check | Status | Evidence |
|---|---|---|---|
| R1 | Working directory inspected before changes; existing files preserved | PASS | Directory was empty at start; no files overwritten |
| R2 | Layout matches the agreed structure (`configs/ data/ src/{data,models,audit,evaluation} tests/ results/ paper/`) plus `docs/` | PASS | `ls -R` |
| R3 | Raw/processed data, CSV/PCAP/ZIP, model weights Git-ignored | PASS | `git check-ignore` on sample paths (see commit) |
| R4 | Dependencies pinned to validated versions | PASS | `requirements.txt`; Milestone 1 packages listed but not pinned |
| R5 | Isolated environment (`.venv`) | BLOCKED | D-014: embedded Python has no `venv` |

## Provenance

| # | Check | Status | Evidence |
|---|---|---|---|
| P1 | Manifest covers the 4 datasets with official source, version, files, license, citation, schema, labels, experiments | PASS | `tests/test_manifest.py` |
| P2 | No mirror listed as a source | PASS | `test_no_mirror_used_as_source` |
| P3 | Official pages checked; unconfirmed facts marked UNCONFIRMED/null | PASS | `configs/datasets.yaml`, checked 2026-11-07 |
| P4 | File sizes and sha256 recorded | BLOCKED | No publisher checksums; compute with `src.data.manifest --hash` after download |
| P5 | Download destinations confirmed | BLOCKED | `local_dir` proposed per dataset; awaiting approval and manual download (registration form for CICIDS2017; browser-only links for UNSW and UQ) |
| P6 | License/redistribution terms confirmed for Engelen and NF-UNSW-NB15-v2 | BLOCKED | Not stated on the official pages |

## Data tooling (synthetic tests only)

| # | Check | Status | Evidence |
|---|---|---|---|
| T1 | Inspection reports schema, shape, labels, missing/inf/negative, duplicates, conflicting-label duplicates, types, leakage candidates | PASS | `tests/test_inspection.py` |
| T2 | Reader handles stripped/duplicated column names, `Infinity`, cp1252 label bytes | PASS | `test_reader_handles_cicids_style_quirks` |
| T3 | Preprocessing statistics come from the training partition only | PASS | `test_statistics_come_from_train_only`, `test_test_set_extremes_do_not_change_fit` |
| T4 | Source frames are never mutated | PASS | `test_source_frame_is_not_mutated` |
| T5 | Unseen test categories do not create columns | PASS | `test_unseen_category_encodes_as_zeros` |
| T6 | Row-validity rules report, never drop silently | PASS | `test_invalid_row_mask_reports_without_dropping` |
| T7 | Splits are deterministic per seed, disjoint and complete | PASS | `tests/test_split.py` |
| T8 | Group / temporal / predefined splits available; random split shown to leak groups | PASS | `test_random_split_leaks_groups_that_group_split_does_not` |
| T9 | Cross-split duplicate feature vectors detectable | PASS | `test_cross_split_duplicates_detects_identical_vectors` |
| T10 | Saved splits carry a fingerprint; tampering detected | PASS | `test_save_load_roundtrip_and_tamper_detection` |
| T11 | Full suite | PASS | `python -m pytest`: 32 passed |
| T12 | CLIs run end to end | PASS (with workaround) | Ran via `sys.path.insert(0, '.')` because of D-014; manifest lists all files as missing; inspection on a synthetic CSV |

## Blocked until data is present

| # | Check | Status |
|---|---|---|
| B1 | Run inspection on every dataset; save JSON reports under `results/inspection/` | BLOCKED |
| B2 | Confirm column names, label columns, feature counts (D-001, D-006) | BLOCKED |
| B3 | Measure duplicate and cross-split duplicate rates per split strategy (D-007) | BLOCKED |
| B4 | Confirm Paper 1 DDoS subset = Friday-afternoon file (D-008); Fang counts = official partition (D-009) | BLOCKED |
| B5 | Confirm which columns are constant on train (D-011) | BLOCKED |

## Decisions required before Milestone 1

D-001, D-002, D-004, D-005, D-007, D-008, D-009, D-010 and D-014 (see
`docs/decision_log.md`). D-003, D-006, D-011, D-012 and D-013 can be decided
during Milestone 1, but before the experiments that depend on them.
