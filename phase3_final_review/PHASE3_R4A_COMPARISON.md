# R4a: original vs corrected CICIDS2017 (Engelen et al. WTMC 2021), full evidence

**Protocol:** D-024 (approved 2026-11-11); D-005 defines the window.

**What R4a contains:**
- **R4a-ii (primary):** the r1 design rebuilt *within* the corrected data.
- **R4a-i (secondary, descriptive):** the original-trained r1 models scored on corrected rows.

**Sources:**
- `results/protocol/r4a/r4a_feasibility_v1.json` and `eval_population_r4a_v1.json`
- `configs/protocol/r4a_groups_v1.yaml` and `r4a_column_map_v1.yaml`
- `results/r4a/*.json`
- `evidence/verification/verify_r4a.json` and `r4a_predictions_colab_check.json`
- `docs/MILESTONE_3B0_READINESS.md` §4

## A. Corrected-data preparation

| Item | Original (r1) | Corrected (R4a) |
|---|---|---|
| Source | CIC `MachineLearningCSV.zip` (SHA-256 `c3f26274…`), `Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv` | Engelen WTMC2021 `dataset.zip` (SHA-256 `4d535da1…`), `Friday-WorkingHours.csv` (CRC `5bbc54cc`, SHA-256 `8bf5a792…`), 547,915 rows |
| Recording window used | Whole DDoS afternoon file | Original-clock window 2017-07-07 15:30–17:03, mapped with an **empirically estimated +5:00 offset**. DDoS onset and end differ by exactly 5 h (15:56→20:56, 16:16→21:16). This is an assumption, not a confirmed time-zone correction. |
| Labels | BENIGN → 0, DDoS → 1 | Same mapping. Inside the window only DDoS and BENIGN occur. Outside it, 239,913 BENIGN, 159,151 PortScan, 1,470 Bot-Attempted and 738 Bot rows are out of scope. |
| Raw rows (DDoS / benign) | 225,745 (128,027 / 97,718) | 146,643 (95,123 / 51,520) |
| Invalid rows (D-011) | 36 | 3 |
| Kept | 225,709 | 146,640 |
| Split fingerprint | `50bd9948…` | `acd52bd8…` |
| Train / val / test rows | 157,998 / 33,834 / 33,877 | 102,496 / 22,033 / 22,111 |
| Model-visible twin exclusion (test) | 839 benign | 62 benign |
| Family-common test | **33,038** (19,233 DDoS; prevalence 58.2%) | **22,049** (14,168 DDoS; prevalence 64.3%) |
| Model inputs | 68 (full view) | 74 (full view); constant on train: URG flags ×3, Subflow Bwd Packets |
| DDoS flows per minute | about 6,300 | about 4,870. Segmentation differs: Engelen's extractor yields fewer flows per minute for the same attack (why is not established here). |

**Feature mapping:**
- All 78 original columns map to Engelen columns: 21 renames, 6 Engelen-only identifier columns unused.
- `CWE Flag Count` ← `CWR Flag Count` (name only); `Fwd Header Length.1` ← `Fwd Header Length` (its documented duplicate).

**Definition and encoding changes** (≥ 16 of 68 inputs; readiness §4):

| Status | Inputs | Change |
|---|---|---|
| Confirmed (documented) | 8 group-A flag fields | Counted per packet instead of first packet only |
| Confirmed (label-free evidence) | `Subflow Fwd Packets` | The relation `Subflow Fwd Packets` = `Total Fwd Packets` holds in 100% of original rows and 0% of corrected rows |
| Suspected | 3 other subflow fields | Same collapse in descriptive comparison only |
| Encoding change | 2 init-window fields | "Not observed" coded −1 → 0 |
| Value-set change | `min_seg_size_forward` | Different set of observed values |
| Logged fix | Down/Up Ratio | Fixed by the dataset maintainers |

Descriptively, 24 inputs have KS ≥ 0.5 between original and corrected DDoS flows.

**Frozen groups:** generated from the corrected training partition before any R4a training, by the same algorithm as r1.

| Group | r1 (original) | R4a (corrected) | Why they differ |
|---|---|---|---|
| A | 8: ACK, ECE, FIN, Fwd PSH, PSH, RST, SYN, URG | 9: ACK, Bwd PSH, CWE, ECE, FIN, Fwd PSH, PSH, RST, SYN | URG is constant in the corrected train. Bwd PSH and CWE are constant in the original train. |
| B (closed) | 10 | 8 | The proxy twins Fwd PSH↔SYN and Subflow Fwd Packets↔Total Fwd Packets exist only in the original data |
| U | 20 | 20 | Different members, as above |
| C, D | Run | Not part of R4a (D-024) | |

Controls are 10 random draws per group, size-matched, from the control pool. Seed rule: RandomState(7000 + 100·g + d).

## B. Corrected-data model performance (R4a-ii full model, 10 seeds)

| Seed | TN | FP | FN | TP | Errors | Accuracy | F1 | MCC | AUROC | FPR | FNR | BER | Log loss | AE best / run | XGB best iteration |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0 | 7879 | 2 | 0 | 14168 | 2 | 0.999909 | 0.999929 | 0.999803 | 1.000000 | 0.000254 | 0 | 0.000127 | 0.000344 | 53/64 | 258 |
| 1 | 7880 | 1 | 1 | 14167 | 2 | 0.999909 | 0.999929 | 0.999803 | 0.999998 | 0.000127 | 0.000071 | 0.000099 | 0.000680 | 77/88 | 154 |
| 2 | 7879 | 2 | 0 | 14168 | 2 | 0.999909 | 0.999929 | 0.999803 | 1.000000 | 0.000254 | 0 | 0.000127 | 0.000445 | 30/41 | 141 |
| 3 | 7880 | 1 | 0 | 14168 | 1 | 0.999955 | 0.999965 | 0.999901 | 1.000000 | 0.000127 | 0 | 0.000063 | 0.000339 | 61/72 | 256 |
| 4 | 7879 | 2 | 1 | 14167 | 3 | 0.999864 | 0.999894 | 0.999704 | 0.999999 | 0.000254 | 0.000071 | 0.000162 | 0.000655 | 69/80 | 225 |
| 5 | 7880 | 1 | 0 | 14168 | 1 | 0.999955 | 0.999965 | 0.999901 | 0.999999 | 0.000127 | 0 | 0.000063 | 0.000468 | 72/83 | 129 |
| 6 | 7879 | 2 | 0 | 14168 | 2 | 0.999909 | 0.999929 | 0.999803 | 1.000000 | 0.000254 | 0 | 0.000127 | 0.000476 | 62/73 | 111 |
| 7 | 7879 | 2 | 0 | 14168 | 2 | 0.999909 | 0.999929 | 0.999803 | 1.000000 | 0.000254 | 0 | 0.000127 | 0.000289 | 58/69 | 110 |
| 8 | 7880 | 1 | 0 | 14168 | 1 | 0.999955 | 0.999965 | 0.999901 | 1.000000 | 0.000127 | 0 | 0.000063 | 0.000129 | 35/46 | 200 |
| 9 | 7880 | 1 | 1 | 14167 | 2 | 0.999909 | 0.999929 | 0.999803 | 1.000000 | 0.000127 | 0.000071 | 0.000099 | 0.000207 | 47/58 | 104 |

Mean errors 1.8 ± 0.6; MCC 0.999822 ± 0.000062. All full-model autoencoders early-stopped.

**Convergence across all 70 fits:** 17 autoencoders reached the 100-epoch cap (A s5, s7; B s0, s1, s8, s9; Bctl s0, s2, s3, s6, s7, s8; U s0, s5, s6, s7, s8). XGBoost always early-stopped. The capped fits' errors are 0–4, like the rest.

## C. Corrected-data ablations (primary family of 3: error rate, Holm)

| Group | Errors per seed, group | Errors per seed, control | Mean Δ group | Mean Δ control | Mean d | 98.33% difference interval | 96.67% TOST interval | p exact (non-zero pairs) | p Holm | Reading |
|---|---|---|---|---|---|---|---|---|---|---|
| A (9) | 1,3,0,2,4,2,2,1,2,2 | 2,2,1,1,2,3,2,2,2,3 | +0.000005 | +0.000009 | −0.000005 | [−0.000051, +0.000042] | [−0.000044, +0.000035] | 1.000 (8) | 1.000 | practical equivalence |
| B (8) | 0,2,2,2,3,2,1,2,2,2 | 1,1,1,2,2,1,1,2,3,1 | +0.000000 | −0.000014 | +0.000014 | [−0.000021, +0.000048] | [−0.000016, +0.000043] | 0.453 (7) | 1.000 | practical equivalence |
| U (20) | 2,2,2,2,0,2,1,1,1,1 | 1,2,1,1,4,1,2,2,2,2 | −0.000018 | −0.000000 | −0.000018 | [−0.000085, +0.000048] | [−0.000075, +0.000039] | 0.641 (9) | 1.000 | practical equivalence |

**Secondary endpoints (descriptive):** sign-flip p ≥ 0.22 for MCC and for log loss (`PHASE3_STATISTICAL_FINDINGS.csv`).

**Practical interpretation:**
- On corrected flows no documented group carries measurable weight relative to random features.
- The near-zero error floor (SESOI 0.001 = 22 errors versus 1–4 observed) means the test can rule out *large* harms. It cannot resolve harms of a few errors either way.

## D. Original vs corrected (observational)

| Group | r1 mean d | R4a-ii mean d | Corrected − original, Welch 95% |
|---|---|---|---|
| A | +0.000097 (Holm p 0.020) | −0.000005 | −0.000101 [−0.000155, −0.000048] |
| B | −0.000012 | +0.000014 | +0.000026 [−0.000039, +0.000090] |
| U | +0.000182 (Holm p 0.020) | −0.000018 | −0.000200 [−0.000275, −0.000124] |

**Full-model error rate:** 0.000176 on the original (33,038 rows) vs 0.000082 on the corrected data (22,049 rows).

**Answers to the brief:**
- **Did the artifact groups become less or more important?** Less. The small r1 effects of A and U are absent in the corrected data. B was null in both.
- **What causes the change?** Unresolved.
  - The change is consistent with A's original-data importance being tied to the defective flag counting.
  - Equally compatible explanations: a different flow segmentation (fewer flows per minute), a different label window, different populations and prevalence (58% vs 64%), ≥ 16 changed definitions, and a different group composition (A has 9 vs 8 members; B has 8 vs 10).
  - Classification errors cannot explain it either way: both sides have only a handful of errors.
- **Limits of comparing independently segmented flows.** The rows are not the same flows, so no row-level pairing exists. The comparison is between two separate experiments on two separate captures of the same traffic.
- **Seeds as experimental units.**
  - Each side's inference is conditional on its own fixed test set.
  - Seeds capture training variability only, not sampling variability of the capture.
  - The Welch interval treats the two sets of 10 contrasts as independent samples of a common quantity, which they are not. It is descriptive only.
- **Do the results support the central hypothesis?**
  - The question was whether near-perfect accuracy rests on extractor artifacts.
  - **Within either capture: no.** Accuracy survives removal of every documented group (r1: at most about 6 extra errors; R4a-ii: equivalence).
  - **Across captures: partly** (R4a-i, below). This is **the main finding that contradicts a simple "no reliance" reading**, and also the main finding that contradicts a simple "the 99% is an artifact" reading. Both readings must be qualified.

## E. R4a-i: original-trained models on corrected rows (descriptive, not causal)

Same 22,049 rows (14,168 DDoS). Recall and FPR are means over 10 models per view; an all-benign classifier has error 0.643.

| r1 view | DDoS recall mean [min, max] | Benign FPR mean [min, max] | Error rate | MCC |
|---|---|---|---|---|
| Full | 0.088 [0.000, 0.879] | 0.023 [0.000, 0.093] | 0.594 | 0.017 |
| Without A | **0.958** [0.800, 0.999] | 0.048 [0.000, 0.381] | 0.044 | 0.909 |
| Without B | 0.000 [0.000, 0.000] | 0.000 | 0.643 | −0.007 |
| Without C | 0.158 [0.000, 0.830] | 0.041 | 0.555 | 0.068 |
| Without D | 0.132 [0.000, 0.736] | 0.030 | 0.568 | 0.082 |
| Without U | **0.994** [0.981, 1.000] | 0.0007 [0.000, 0.002] | 0.004 | 0.991 |
| Controls A / B / C / D / U | 0.114 / 0.054 / 0.049 / 0.000 / 0.031 | 0.072 / 0.038 / 0.035 / 0.012 / 0.081 | 0.595–0.652 | −0.084 to 0.031 |

**Reading:**
- Models that kept the flag-count fields (full, without B/C/D, and all controls, which are drawn from the non-registered pool) nearly all classify corrected DDoS as benign.
- Models trained without A or U transfer almost perfectly. Those without A still contain the suspected-changed subflow inputs.
- This is the pattern expected if the original decision rules key on flag counts whose definitions the correction changed.

**Not claimed:**
- that this measures reliance on the *defect*: the definition change is the correction itself, and other inputs changed too;
- that it is causal: there is no controlled intervention on the test side.

The seed-level spread (full models 0.00–0.88) shows the transfer outcome is unstable for models that keep A.
