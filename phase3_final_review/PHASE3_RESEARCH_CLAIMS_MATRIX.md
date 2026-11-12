# Research claims matrix

**Status values:**
- **supported:** evidence matches the claim as worded.
- **qualified:** supported only with the stated wording or limits.
- **inconclusive:** evidence cannot decide.
- **unsupported:** evidence contradicts the claim or does not exist.

**Evidence type:** O = observed, S = pre-registered statistical, D = descriptive, L = literature, H = hypothesis.

## Research questions

**RQ1 (H1).** Does AE-XGBoost's near-perfect CICIDS2017 DDoS accuracy depend on documented artifact features?
- Hypothesis: removing a documented group hurts more than removing a size-matched random set, by more than the SESOI.
- Answer: **no practically relevant dependence within the capture.** A, D and U show detectable but sub-SESOI differences (S); B and C are practically equivalent (S).

**RQ2 (H2).** Does removal change false positives on unseen benign traffic (Monday)?
- Answer: **inconclusive** for A, B, D and U (intervals exceed the SESOI); C is practically equivalent (S).

**RQ3 (R4a).** Does near-perfect detection, and group dependence, persist once extraction is corrected?
- Detection persists (O).
- Group dependence is practically equivalent to zero within corrected data (S, near a floor).
- Original-trained models do not transfer unless the flag group is excluded (D).

**RQ4 (baselines).** Do duplicate-aware evaluations change the reported performance of other published architectures?
- Answer: **yes, measured on our adaptations** (D).

## Claims

| # | Proposed claim | Numerical evidence | Type | Limitations | Status |
|---|---|---|---|---|---|
| C1 | AE-XGBoost reaches near-perfect accuracy on CICIDS2017 Friday DDoS under a duplicate-aware split | Accuracy 0.999824, MCC 0.999639, 5.8 ± 1.6 errors per 33,038 (10 seeds) | O | One file, one day, one attack; inspected test population | supported |
| C2 | Removing documented artifact groups does not materially reduce in-domain accuracy | d (×10⁻³): A +0.097, B −0.012, C +0.039, D +0.148, U +0.182; all intervals inside ±1; Holm p 0.020 / 1 / 1 / 0.047 / 0.020 | S | SESOI is a judgement; "not material" is relative to it; conditional on one test set | supported (as "detectable but below SESOI" for A, D, U) |
| C3 | The model does not rely on the TCP flag-count defects | In-domain +3 errors per 33,038 when A is removed (S); but R4a-i recall 0.09 with A vs 0.96 without A (D) | S + D | In-domain redundancy vs cross-extractor dependence | **qualified**: true in-domain only. Must not be stated without the R4a-i result. |
| C4 | Group-removal effects on Monday FPR are negligible | No Holm-significant contrast; C equivalent; A, B, D, U inconclusive (intervals up to ±1.4×10⁻³) | S | Large seed variance of full-model FPR (0.068–0.195%) | inconclusive (except C) |
| C5 | Monday results show the model generalises to unseen attacks | Monday is benign-only | — | Cannot measure recall | **unsupported**. Do not claim. |
| C6 | Near-perfect detection persists on corrected CICIDS2017 | R4a-ii full model: 1.8 errors per 22,049, MCC 0.999822 | O | Different segmentation, population, window; +5:00 assumption | supported |
| C7 | On corrected data no documented group matters (equivalence) | d: A −0.005, B +0.014, U −0.018 (×10⁻³); 96.67% TOST inside ±1; Holm p = 1 | S | Near-zero error floor; 17 of 70 AEs at the epoch cap | supported (qualified by the floor) |
| C8 | The small r1 A/U effects disappear after correction | Corrected − original: A −0.101 [−0.155, −0.048], U −0.200 [−0.275, −0.124] ×10⁻³ (Welch, descriptive) | D | Not a test; datasets differ in many ways; seeds not exchangeable across datasets | qualified (observational) |
| C9 | The r1 A/U effects were caused by the extraction defects | — | H | Confounded (segmentation, labels, population, ≥ 16 definitions, group composition) | **unsupported** as causal. State as compatible only. |
| C10 | Original-trained models fail on the corrected extractor's flows unless the flag-count group is excluded | Recall: full 0.088; without A 0.957; without U 0.994; without B 0.000; controls ≤ 0.114 | D | Transfer result, not a controlled ablation; definitions differ; seed spread 0.00–0.88 | supported (as descriptive) |
| C11 | This shows 99% accuracy is an artifact | — | — | In-domain accuracy survives every removal (C2, C6) | **unsupported**. Correct form: high in-domain accuracy coexists with extractor-specific decision rules. |
| C12 | SHAP attribution concentrates on documented defect features | ACK Flag Count top-1 in 6/6 variants; direct-tier ARR@2 55.0–60.8%, ARR@20 21.3–22.2%; all-registered ARR@20 34.7–36.8% | O | One model, float64, test rows of an inspected population | supported |
| C13 | Attribution concentration is not evidence of reliance | C12 vs C2 | O + S | Shown for one architecture | supported |
| C14 | Duplicated test rows inflate DCNN scores on UNSW-NB15 | Same 5 models: MCC 0.784 → 0.719 (paired Δ −0.065 [−0.068, −0.062]); identical false negatives; all 1,468 duplicate DoS rows detected | O + D | Population change; the filtered set has a lower DoS share (6.9% vs 10.0%), so precision changes partly by prevalence | qualified |
| C15 | The DCNN learned from leakage | — | H | Filtering changes evaluation, not training | **unsupported** (not tested) |
| C16 | MES-DNN's apparent skill depends on duplicate overlap | Ensemble MCC N1 0.658 → 0.001, N2 0.625 → 0.242 (random → duplicate-aware); N2 own base 0.906 → 0.150 | O + D | Two networks; unstable seeds; duplicate-aware also changes partition composition | qualified |
| C17 | MES-DNN generalises to unseen networks | No network held out | — | | **unsupported**. Do not claim. |
| C18 | Our AE-XGBoost outperforms Nezhadsistani et al. | 0.99985 vs 0.9993 (different data and protocol) | — | Incompatible settings | **unsupported**. Describe, don't rank. |
| C19 | The DCNN adaptation reproduces Fang et al. | MCC 0.784 vs 0.9355 | — | Adaptation | **unsupported**. It is an adaptation. |
| C20 | The Friday DDoS benchmark is saturated | C1, C2, C6; almost all features redundant | O + S | One attack family | supported |
| C21 | Corrected-data results are near a floor that limits the equivalence claim | 0–4 errors per model; SESOI = 22 errors | O | | supported (a limitation to state) |
| C22 | The +5:00 offset is a time-zone correction | DDoS onset and end align exactly at +5:00 | D | Only 2 anchor points; UTC−3 / UTC+2 is a hypothesis | **unsupported** as fact; supported as an empirical assumption |

## Strongest contributions

1. **A pre-registered, controlled group-removal design (design D) for NIDS feature-reliance claims:** size-matched random controls, paired contrasts, exact tests, Holm and SESOI. Applied to 110 fits, it shows that documented-artifact removal costs at most about 6 errors per 33,038.
2. **A cross-extractor audit on the same traffic (R4a):** within-corrected equivalence, and a descriptive transfer contrast showing that original-trained models fail unless TCP flag-count inputs are excluded (recall 0.09 vs 0.96–0.99).
3. **A demonstration that SHAP concentration and interventional reliance disagree** (ACK Flag Count top-1; removal ≈ +3 errors in-domain), with a corrected evidence registry and ARR@K.
4. **Same-model duplicate-population audits of two further published architectures**, quantifying inflation: DCNN MCC −0.065; MES-DNN collapse under duplicate-aware splitting.

## Most significant threats to validity

- **Inspected population:** the CICIDS2017 test population was inspected during protocol design.
- **Unit of analysis:** the seed. Inference is conditional on one test set; ten seeds give min p = 2/1024.
- **Narrow scope for the main experiment:** one capture day and one attack family.
- **R4a confounding:** segmentation, labels, population, ≥ 16 definition changes, group composition, and the +5:00 assumption.
- **Floor effect:** corrected-data errors are near zero.
- **Convergence:** 19 autoencoder fits at the epoch cap.
- **Adaptations:** all baselines are adaptations; MES-DNN uses 2 of 5 networks plus a subsample.
- **SHAP scope:** a single model, float64.
