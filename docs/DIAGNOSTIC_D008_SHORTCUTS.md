# Shortcut diagnostics — CICIDS2017 Friday DDoS (D-008 scope), 2026-11-08

**Source:** `python -m src.experiments.shortcut_diagnostics --config configs/experiments/ae_xgb_d008_trackB.yaml --baseline-run results/runs/ae_xgb_d008_trackB-seed0-cpu-565a8b9e` → `results/diagnostics/ae_xgb_d008_trackB-shortcuts.json`.

**Method:**

- Verified data (archive sha256 + MD5, member CRC); D-011 rules; the pinned track-B split (fingerprint `50bd9948…`).
- Simple models are fitted on the **training** partition only, ranked on validation, and reported on test. No AE-XGBoost model was trained.
- **Everything below is association, not proof of an artifact (D-012).**

## 1. Destination Port

| | Rows | Port 80 | Distinct ports | Top ports |
|---|---|---|---|---|
| DDoS | 128,025 | **128,022 (99.998%)** | 4 | 80; single flows to 64869, 64873, 27636 |
| BENIGN | 97,684 | 8,923 (9.13%) | 23,943 | 53 (31,950), 443 (13,479), 80 (8,923), 8080, 123 |

**Within partitions** (consistent across all three):

| | DDoS on port 80 | DDoS elsewhere | BENIGN on port 80 | BENIGN elsewhere |
|---|---|---|---|---|
| Train | 89,575 | 2 | 6,288 | 62,133 |
| Validation | 19,215 | 0 | 1,335 | 13,284 |
| Test | 19,232 | 1 | 1,300 | 13,344 |

**Port-only classifiers:**

| Classifier | Partition | Accuracy | MCC | Confusion (TN / FP / FN / TP) |
|---|---|---|---|---|
| Rule "port = 80 → DDoS" (no fitting) | Test | 0.9616 | 0.9238 | 13,344 / 1,300 / 1 / 19,232 |
| Rule "port = 80 → DDoS" (no fitting) | Validation | 0.9605 | 0.9218 | — |
| Port lookup fitted on train | Test | 0.8817 | 0.7752 | 2,710 test rows have ports never seen in train |

**Reading:** the port is an almost perfect *necessary* condition for DDoS in this capture, but it alone explains only MCC ≈ 0.92. The 1,300 benign port-80 test flows must be separated by other features.

## 2. Other single-feature separation patterns

| Analysis | Result |
|---|---|
| One threshold per feature (depth-1), all 78 features | **No feature exceeds validation MCC 0.90.** Best: `Fwd Packet Length Max` 0.763, `Fwd Packet Length Mean` / `Avg Fwd Segment Size` 0.762, `Init_Win_bytes_forward` 0.737 |
| Two thresholds per feature (depth-2) | Only `Destination Port` exceeds 0.90 (0.922 validation / 0.924 test, i.e. the port-80 band). Next: byte totals (`Total Length of Bwd/Fwd Packets`, `Subflow * Bytes`) about 0.89 |
| Port-80 flows only (train 95,863 / test 20,532 rows), one other feature | Best validation MCC 0.710 (`Total Length of Fwd Packets`, `Fwd Packet Length Max`, `Fwd Packet Length Std`). On test: all 19,232 DDoS caught, but only 660 of 1,300 benign (640 false positives) |

**Reading:**

- "Port 80 + one size feature" gives about 98% accuracy.
- The baseline's 99.985% (5 test errors) requires **multi-feature combinations**.
- So there is no single-feature shortcut that explains the result by itself.
- The classes are nevertheless *very* simply separable: one port value plus packet-size and window features.

## 3. The baseline's errors (saved predictions; nothing retrained)

| Partition | Source row | True class | Destination Port | P(DDoS) |
|---|---|---|---|---|
| Test | 5245, 5246, 155712 | BENIGN | **443** | 0.99, 0.99, 0.9999 (false positives) |
| Test | 99515 | DDoS | 80 | 0.001 (missed) |
| Test | 110943 | DDoS | **64869** | 0.00003 (missed: one of the 3 non-port-80 DDoS flows) |

- Benign port-443 flows classified as DDoS show the model does **not** simply read the port.
- The non-port-80 DDoS flow is missed. That is consistent with port being informative, but it is one row.

## 4. Correlation vs leakage vs extraction defect

| Category | Evidence here | Status |
|---|---|---|
| **Correlation / capture confound** | DDoS ≈ port 80 (99.998%); benign port 80 only 9.1%. In this capture the attack targets one web service. Whether that is a legitimate signal (HTTP flood → port 80) or a dataset-specific shortcut depends on the deployment it should generalize to | **Measured association; candidate shortcut (D-012). Not established as an artifact** |
| **Exact-duplicate leakage** | 0 shared feature vectors across all three partition pairs (raw and preprocessed) | Excluded by design (D-007 track B) |
| **Near-duplicate / session leakage** | Not measured. The DDoS is one continuous attack session; content grouping keeps exact duplicates apart but not near-identical flows from the same session, so train and test likely share session context | **Open limitation.** A time- or session-grouped split needs the `TrafficLabelling` identifiers |
| **Confirmed extraction defects** | None confirmed in our data. Literature: Engelen et al. document flow-construction defects (TCP appendices, direction reversals). Their regenerated Friday file has 95,123 DDoS flows vs 128,027 here (25.7% fewer); rows cannot be mapped one to one (D-005). The 3 DDoS flows to ephemeral destination ports *would be consistent with* a reversed direction, but that is unverified | **Not established** for any feature in this file |

## 5. Consequence for the Destination Port ablation

Removing the port merges flows that differ only by port. Under the **original** split:

| Effect | Rows |
|---|---|
| New cross-partition duplicates: train–val / train–test / val–test | 357 / 364 / 163 |
| Classes of those rows | all BENIGN (0 DDoS) |
| Conflicting labels | 0 |
| Excluded from evaluation (`exclude_eval_twins`): validation / test | 357 / 391 (test = 364 train twins + 27 val-only twins) |
| Excluded test rows by port | mostly 137, 80, 443 |

**Common test population:** 33,486 rows (19,233 DDoS / 14,253 BENIGN), evaluation fingerprint `0435302b…`. Design: D-018 in the decision log.

## 6. Limitations

- One model seed.
- Simple single-feature and depth-2 models only. No multi-feature shortcut search, and no SHAP (deferred, D-002).
- Near-duplicate and session leakage are not assessed.
- No row-level link to the corrected (Engelen) data.
