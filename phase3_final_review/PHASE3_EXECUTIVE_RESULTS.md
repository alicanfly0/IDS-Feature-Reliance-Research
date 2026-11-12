# Phase III executive results

**Project:** "How Real Is 99% Accuracy? Auditing Feature Reliance in Network Intrusion Detection" (CNET, FAST-NUCES; Ali Waseem Abbasi i232630, Muhammad Mudassir i232562). Evidence state: 2026-11-12, repository commit `85a2ed2` plus this review package.

**Status vocabulary:**
- **Observed:** a measured number.
- **Statistical:** a pre-registered test or interval.
- **Descriptive:** measured but not tested.
- **Literature:** an explanation from the cited literature.
- **Hypothesis:** not established here.

Every number below is traceable to `PHASE3_ALL_METRICS.csv` / `PHASE3_STATISTICAL_FINDINGS.csv` and was recomputed from saved predictions (see `PHASE3_EXPERIMENT_AUDIT.md`).

## 1. Completion

- **All planned experiments are complete:**
  - 195 model fits: 110 AE-XGBoost r1, 70 R4a-ii, 5 DCNN, 10 MES-DNN ensembles;
  - 220 inference evaluations: 110 Monday, 110 R4a-i.
- **All are verified.** No missing, failed, duplicate or numerically inconsistent run remains.
- **Remaining issues are about reporting, not results:** two interval-label errors, one pooled-population comparison, and one source-paper scenario check. See `PHASE3_OPEN_ISSUES.md`.

## 2. AE-XGBoost main experiment (r1, design D)

**Data and seeds:** CICIDS2017 Friday DDoS file, duplicate-aware track-B split. The test population is family-common: 33,038 rows (19,233 DDoS), with 839 benign test rows excluded because they twin a training row in some view. Seeds 0–9.

### Full model (10 seeds), observed

| Metric | Mean ± SD | Range |
|---|---|---|
| Errors (count) | 5.8 ± 1.6 | 3–8 (FP 1–6, FN 2–3) |
| Accuracy | 0.999824 | 0.999758–0.999909 |
| Precision (DDoS) | 0.999823 | 0.999688–0.999948 |
| Recall (DDoS) | 0.999875 | 0.999844–0.999896 |
| F1 | 0.999849 | 0.999792–0.999922 |
| MCC | 0.999639 ± 0.000101 | 0.999502–0.999813 |
| AUROC | 0.999996 | 0.999994–0.999998 |
| Log loss | 0.000848 | 0.000648–0.001070 |
| Balanced error rate | 0.000186 | 0.000088–0.000269 |

**Training:**
- The autoencoder early-stopped at epochs 41–97 (best epochs 30–86).
- XGBoost best iterations 136–346 of 2,000.

### Group removal (pre-registered primary family, 10 tests)

**Definitions:**
- Δ = ablated − full.
- d = Δ_group − Δ_matched-random-control. d > 0 means removing the group hurts more.
- Exact sign-flip test, Holm over 10 tests, 99.5% t-intervals, TOST at 99%, SESOI 0.001.

| Group (inputs) | Mean errors: group / control / full | Mean d, error rate (×10⁻³) [99.5%] | p (exact) | p (Holm) | Pre-registered reading |
|---|---|---|---|---|---|
| A flag-count defects (8) | 8.3 / 5.1 / 5.8 | +0.097 [+0.023, +0.171] | 0.0020 | 0.020 | difference, below SESOI |
| B TCP appendix (10) | 4.6 / 5.0 / 5.8 | −0.012 [−0.112, +0.088] | 0.74 | 1.0 | practical equivalence |
| C duplicated packets (4) | 5.0 / 3.7 / 5.8 | +0.039 [−0.065, +0.143] | 0.23 | 1.0 | practical equivalence |
| D metadata hypotheses (2) | 10.5 / 5.6 / 5.8 | +0.148 [+0.025, +0.271] | 0.0059 | 0.047 | difference, below SESOI |
| U union A∪B∪C (20) | 10.9 / 4.9 / 5.8 | +0.182 [+0.079, +0.284] | 0.0020 | 0.020 | difference, below SESOI |

**Reading:**
- Removing A, D or U costs about 3, 5 and 6 extra errors on 33,038 rows (statistical, Holm-significant). Every interval lies inside ±1×10⁻³ (SESOI = 33 errors).
- The near-perfect accuracy does **not** depend on the documented artifact groups *within this capture*.
- The A, D and U contrasts all reached the smallest attainable p (≈ 2/2¹⁰) or close to it. **Group D (destination port, backward init window) is as influential as the documented defect groups.**

### Monday benign traffic (H2)

**Population:** 494,940 benign-only rows. Built from 529,918 raw rows, minus 452 invalid rows, minus 34,526 rows that twin a training row in any of the 63 views.

**Full models:** 334–966 false positives (FPR 0.068–0.195%, mean 0.108%).

**Group contrasts:**
- No Monday-FPR contrast is Holm-significant.
- C reads as practical equivalence.
- A, B, D and U are **inconclusive**: their 99.5% intervals exceed ±SESOI because of large seed-to-seed FPR variation.
- Monday establishes **only** false-positive behaviour on unseen benign traffic of another day. It cannot establish attack recall or generalisation to unseen attacks.

## 3. Corrected CICIDS2017 (Engelen WTMC2021, R4a, D-024)

**Data:**
- Original DDoS window 15:30–17:03, mapped by an **empirically estimated +5:00 clock offset** (an assumption, not a confirmed time-zone correction).
- 146,643 corrected flows (95,123 DDoS / 51,520 benign), versus 225,745 original flows (128,027 DDoS).
- Family-common test: 22,049 rows (14,168 DDoS); 62 benign twins excluded.
- Groups were re-frozen on the corrected training partition: A has 9 inputs, B 8, U 20.

### R4a-ii (within corrected data, 70 fits)

**Full model:**
- 1.8 ± 0.6 errors per seed (1–3; FP 1–2, FN 0–1).
- MCC 0.999822, AUROC 1.000000 (min 0.999998), log loss 0.000403.

**All three primary contrasts read as practical equivalence** (Holm p = 1.0 for each; 98.33% intervals):

| Group | Mean d (×10⁻³) | 98.33% interval |
|---|---|---|
| A | −0.005 | [−0.051, +0.042] |
| B | +0.014 | [−0.021, +0.048] |
| U | −0.018 | [−0.085, +0.048] |

**Floor effect:** the corrected task is even easier (about 1–2 errors per model). The equivalence verdict therefore holds near a zero-error floor and has limited power to show a *harmful* effect smaller than about 1×10⁻³.

### Original vs corrected (observational, Welch 95%, descriptive)

| Group | Mean d original → corrected | Corrected − original |
|---|---|---|
| A | +0.097 → −0.005 | −0.101 [−0.155, −0.048] |
| B | −0.012 → +0.014 | +0.026 [−0.039, +0.090] |
| U | +0.182 → −0.018 | −0.200 [−0.275, −0.124] |

The small A and U effects of r1 are absent in the corrected data. This is consistent with them being tied to the original extraction, but the datasets also differ in segmentation, label windows, populations and definitions (≥ 16 inputs), so **the difference is not attributable to the defects alone**.

### R4a-i (descriptive transfer)

The 110 r1 models (trained on original data) were scored on the same 22,049 corrected rows. All-benign prediction would give error 0.643.

| r1 view | DDoS recall mean [range] | Benign FPR | MCC |
|---|---|---|---|
| Full models | 0.088 [0.000, 0.879] | 0.023 | 0.017 |
| Without A | **0.957** [0.800, 0.999] | 0.048 | 0.909 |
| Without U | **0.994** [0.981, 1.000] | 0.0007 | 0.991 |
| Without B / C / D, and every random-control view | ≤ 0.158 (B: 0.000) | | |

Only models trained **without the TCP flag-count features** transfer. This is the clearest evidence in the project that the original models' decision rules depend on inputs whose definitions the corrected extractor changed. It stays **descriptive**:
- the flag definitions changed with the correction;
- other inputs (subflow, init-window encoding) changed too;
- no causal estimate of defect reliance is claimed.

## 4. DCNN + self-attention adaptation (Fang et al., D-009)

**Setup:** UNSW-NB15 official partition, Normal vs DoS (DoS positive), 22 LightGBM-SHAP-selected inputs (cover 90.5%; the 95% rule would select 30), 5 seeds.

| Population | MCC mean [range] | DoS precision | DoS recall | FPR | AUROC | Errors |
|---|---|---|---|---|---|---|
| Official test (41,089; 4,089 DoS) | 0.784 [0.763, 0.801] | 0.669 | 0.975 | 0.053 | 0.995 | 2,078 |
| Model-visible duplicate-filtered (37,759; 2,621 DoS) | 0.719 [0.696, 0.740] | 0.572 | 0.961 | 0.054 | 0.992 | 1,990 |

**Paired over seeds (filtered − official), descriptive:** MCC −0.065 [−0.068, −0.062].

**Error structure:**
- False negatives are identical in both populations for every seed (95, 109, 92, 112, 100).
- All 1,468 removed duplicate DoS rows were detected by all five models.
- 94–96% of official-test errors are false positives.

**Reading:** duplicated test rows are easy positives that inflate precision, recall and MCC. The filter changes the population, not the model, so this is a measurement-inflation result, not proof of leakage-driven learning.

## 5. MES-DNN two-network adaptation (Wardana et al., D-010)

**Setup:** N1 NF-UNSW-NB15-v2 (2,390,275 flows; 4.0% attack) and N2 a fixed NF-ToN-IoT-v2 subsample (2,390,275; 64.0% attack). 39 inputs, fixed log1p. Random vs duplicate-aware split, 5 seeds each.

### Ensemble MCC on each network's test partition (645,374 rows), mean [range]

| Split | N1 | N2 |
|---|---|---|
| Random | 0.658 [0.166, 0.938] | 0.625 [0.412, 0.884] |
| Duplicate-aware | 0.001 [−0.101, 0.134] | 0.242 [0.061, 0.890] |

### Own-network base models

| Split | N1 MCC | N2 MCC | N2 AUROC | N2 FPR |
|---|---|---|---|---|
| Random | 0.939 | 0.906 | 0.979 | |
| Duplicate-aware | 0.940 | **0.150** | 0.711 | 0.888 |

**Duplication:**
- 93.7% of N1 random-split test rows and 81.0% of N2's repeat a training/meta/validation vector.
- One N2 benign vector makes up 17.7% of the data.

**Reading:** the ensemble is unstable across seeds, and duplicate-aware splitting removes most of its apparent skill. No unseen-network generalisation was evaluated, so none is claimed.

## 6. Attribution (SHAP / ARR)

**AE-XGBoost (permutation SHAP, M1A seed-0 model, 6 explainer variants; descriptive):**
- ACK Flag Count ranks first in all 6 variants. Rankings are stable (pairwise Spearman ≥ 0.994).
- Registry v2 ARR:
  - all 23 registered features: ARR@2 55.0–60.8%, ARR@20 34.7–36.8%;
  - direct extraction-defect tier: ARR@20 21.3–22.2%;
  - shortcut tier: 7.4–8.7%;
  - hypothesis tier: 5.6–6.2%.

**Attribution versus reliance:**
- Attribution concentrates on defect features, yet retraining without them costs about 3 errors in-domain (§2). **Attribution concentration is not reliance.**
- R4a-i shows these same features matter for out-of-capture behaviour (§3).

**DCNN pilot:** GradientExplainer rankings are stable across seeds (mean Spearman 0.91), led by TTL features (sttl, ct_state_ttl, dttl), sloss and swin. They agree only weakly with the LightGBM selector (Spearman 0.28–0.48), which explains LightGBM, not the DCNN.

**MES-DNN pilot:** rankings are less stable (mean Spearman 0.69–0.87; top-5 overlap 44–50%). No ARR is computed for these two models: no artifact registry exists for UNSW-NB15 or NetFlow-v2.

## 7. Conclusions (scientifically defensible)

1. **In-domain saturation.**
   - The CICIDS2017 Friday DDoS benchmark is saturated for AE-XGBoost: 99.98% accuracy, MCC 0.9996.
   - Removing any documented artifact group changes errors by at most about 6 per 33,038.
   - **Statistical:** A, D and U are Holm-significant but below the SESOI; B and C are practically equivalent.
2. **Transfer depends on the flag-count features** (descriptive). Models trained on the original extractor's features do **not** transfer to the corrected extractor's flows (DDoS recall 0.09) unless the TCP flag-count group is excluded (0.96–0.99). High in-domain accuracy coexists with dependence on extractor-specific feature definitions.
3. **Corrected data shows no group dependence.** Within the corrected data the task stays near-perfect and no group shows any dependence (equivalence within ±SESOI, near a zero-error floor).
4. **Duplicates inflate scores.** Duplicate rows inflate reported scores in UNSW-NB15 (DCNN MCC 0.784 → 0.719, measured on the same models) and NetFlow-v2 (MES-DNN collapses under duplicate-aware splits).
5. **Attribution is not reliance.** SHAP concentration on defect features did not predict the in-domain cost of removing them. Interventions and cross-extractor tests are needed to support reliance claims.

## 8. Main limitations

- One capture day and one attack family for AE-XGBoost.
- The test population was inspected during protocol design; H1 is a pre-registered estimate, not a fresh confirmatory test.
- Seeds are the experimental unit: inference is conditional on one test set, and ten seeds give a minimum p of 2/1024.
- The +5:00 alignment is an assumption.
- R4a-i confounds defect correction with other definition changes.
- 19 autoencoder fits stopped at the 100-epoch cap (2 in r1, 17 in R4a).
- All three models are adaptations, not reproductions.
- MES-DNN uses 2 of 5 networks.
- SHAP was computed for one AE-XGBoost model only.
