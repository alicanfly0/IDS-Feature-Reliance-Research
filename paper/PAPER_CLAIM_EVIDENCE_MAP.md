# Claim and evidence map: Phase IV paper

Every quantitative claim in `main.tex` is listed here with its value and the record it comes from. Paths are relative to the repository root. "Status" uses the Phase III vocabulary: **statistical** (pre-declared test or interval), **observed** (a measured number), **descriptive** (measured, not tested), **literature** (from a cited source).

Main records:

- `phase3_final_review/evidence/verification/verify_r1.json`, `verify_r4a.json`, `verify_dcnn.json`, `verify_mes.json` (independent re-scoring of every run; `problems` is empty in all four)
- `phase3_final_review/PHASE3_STATISTICAL_FINDINGS.csv` (all pre-declared tests)
- `results/r4a/stats_r4a.json` (R4a-ii, original vs corrected, R4a-i)
- `results/corrections/milestone2b/corrected_arr_v2.json` (ARR, registry v2)
- `phase3_final_review/evidence/verification/d021_sensitivity.json`, `d021_comparison.json`, `r4a_preservation_status.json`

## 1. Headline and abstract

| Claim in the paper | Value | Source | Status |
|---|---|---|---|
| Full-model errors on the original test population | mean 5.8 (3 to 8) on 33,038 flows | `verify_r1.json` runs `r1_full_s0..9` | observed |
| Full-model MCC | 0.999639 (0.999502 to 0.999813) | same | observed |
| Extra errors when removing A, D, U vs random | d = 0.097, 0.148, 0.182 ×10⁻³, about 3.2, 4.9, 6.0 errors on 33,038 | `PHASE3_STATISTICAL_FINDINGS.csv`, r1 error-rate rows | statistical |
| Holm p for A, D, U | 0.020, 0.047, 0.020 | same | statistical |
| Margin | SESOI 0.001, about 33 errors (r1) and about 22 (R4a) | protocol; CSV `sesoi` column | pre-declared |
| R4a-ii all three contrasts equivalent within the margin | Holm p = 1.0; TOST intervals inside ±0.08 ×10⁻³ | CSV, R4a-ii rows | statistical |
| Original full models' recall on corrected DDoS | mean 0.0884 (0.000 to 0.879) | `verify_r4a.json` → `r4a_i`, kind `full` | descriptive |
| Recall of models trained without A | mean 0.9575 (0.800 to 0.999) | same, group `A_flag_defects` | descriptive |
| DCNN MCC, official vs filtered | 0.7836 → 0.7187 (5-seed means) | `verify_dcnn.json` seeds, `official` and `dedup_model_visible` | observed; same trained models, two test populations |
| MES-DNN N2 own base MCC, random vs duplicate-aware | 0.906 → 0.150 | `verify_mes.json` fits, `N2_ton/base_N2_ton/all` | observed; separately retrained under each split protocol |

## 2. Populations and runs

| Claim | Value | Source |
|---|---|---|
| Original file rows; invalid rows | 225,745 (128,027 DDoS); 36 invalid | `PHASE3_R4A_COMPARISON.md` §A |
| Split sizes | 157,998 / 33,834 / 33,877 | same |
| Family-common test T* | 33,038 (19,233 DDoS); 839 benign twins removed | same; `verify_r1.json` |
| Monday population | 529,918 raw, 452 invalid, 34,526 twins, 494,940 kept | `PHASE3_EXECUTIVE_RESULTS.md` §2 (`monday_population_r1.json`) |
| Corrected window | 146,643 (95,123 DDoS); 3 invalid; split 102,496 / 22,033 / 22,111 | `PHASE3_R4A_COMPARISON.md` §A |
| Corrected T'* | 22,049 (14,168 DDoS); 62 benign twins removed | `verify_r4a.json` → `population` |
| Inputs | 68 original, 74 corrected | `verify_r1.json` `input_dim`; `verify_r4a.json` `colab_check.dim` |
| UNSW-NB15 | train 68,264 (12,264 DoS); test 41,089 (4,089); filtered 37,759 (2,621); 3,330 twins (1,862 Normal, 1,468 DoS); raw filter 1,395 | `verify_dcnn.json` `rows`, `populations` |
| NetFlow-v2 | N1 2,390,275 (95,053 attack, 236,999 distinct vectors); N2 2,390,275 (1,529,289; 505,611 distinct); test partition 645,374 | `verify_mes.json` `networks`, `partitions` |
| Duplicate shares under random split | N1 93.7%, N2 81.0%; one N2 benign vector 422,766 times (17.7%) | `verify_mes.json` partitions; `PHASE3_BASELINE_COMPARISON.md` §2 |
| Run counts | 195 fits (110 + 70 + 5 + 10); 220 inference runs; 2 sensitivity fits | `PHASE3_EXECUTIVE_RESULTS.md` §1; `d021_sensitivity.json` |
| Environment | Colab T4, fingerprint be81b4d6; DCNN and MES-DNN on CPU | `verify_r1.json` `environments`; DCNN/MES `metrics.json` `device: cpu` |
| Phase II split leakage | 93.5% of NF-UNSW-NB15-v2 test rows had a training twin under the proposed split | `docs/decision_log.md` (measured 2026-11-07) |

## 3. Results

| Claim | Value | Source | Status |
|---|---|---|---|
| r1 class-conditional recall | DDoS 0.999875; benign 0.999754 | `tables/tab_full.tex` ← `verify_r1.json` | observed |
| r1 training | AE stopped after 41 to 97 epochs; best XGBoost iteration 136 to 346 | `verify_r1.json` `ae.epochs_run`, `xgb_best_iteration` | observed |
| Monday false positives | 334 to 966 (FPR 0.068% to 0.195%, mean 0.108%) | `verify_r1.json` `monday.fp` | observed |
| R4a-ii full models | 1 to 3 errors (mean 1.8); MCC 0.999822; AUROC ≥ 0.999998 | `verify_r4a.json` `runs_r4a_ii` | observed |
| R4a-i: without U | recall 0.994, FPR 0.0007 | `verify_r4a.json` `r4a_i` | descriptive |
| R4a-i: all other views | mean recall ≤ 0.158; all-benign error 0.643; full-model error 0.594 | same; `tables/tab_transfer.tex` | descriptive |
| DCNN error structure | FP share 94 to 96%; FN identical per seed (95, 109, 92, 112, 100); all 1,468 duplicated DoS rows detected | `verify_dcnn.json` `facts` | observed |
| DCNN filtered metrics | DoS precision 0.669 → 0.572; recall 0.975 → 0.961; FPR 0.053 → 0.054; raw-filter MCC 0.781 | `verify_dcnn.json` seeds | observed |
| MES-DNN per network | Table VIII values (own base, other base, ensemble; both splits) | `tables/tab_mes.tex` ← `verify_mes.json` | observed |
| N2 base under duplicate-aware split | FPR 0.888; AUROC 0.979 → 0.711 | `verify_mes.json` | observed |
| Seed spread used in the discussion | DCNN official MCC 0.763 to 0.801; N2 random base 0.778 to 0.945 | `verify_dcnn.json`; `verify_mes.json` | observed |
| SHAP model | one earlier baseline, test F1 0.99987, MCC 0.99970 on 33,877 rows | `PHASE3_EXPLAINABILITY.md` §1 | observed |
| ACK Flag Count first in all six variants; Spearman 0.9945 to 0.9993 | | same | descriptive |
| ARR ranges | direct tier ARR@2 55.0 to 60.8%, ARR@20 21.3 to 22.2%; all registered ARR@20 34.7 to 36.8% | `corrected_arr_v2.json` (`sum_abs`, six variants) | descriptive |
| DCNN and MES attribution pilots | DCNN mean Spearman 0.909, LightGBM agreement 0.28 to 0.48; MES 0.69 to 0.87, top-5 overlap 44 to 50% | `results/attribution_pilot/{dcnn,mes}.json` via `PHASE3_EXPLAINABILITY.md` | descriptive |

## 4. Ablation

| Claim | Value | Source |
|---|---|---|
| r1 table (10 tests) | all Δ, d, 99.5% difference and 99% TOST intervals, Holm p, readings | `tables/tab_r1.tex` ← `PHASE3_STATISTICAL_FINDINGS.csv` (the script asserts the interval levels) |
| Monday contrasts | none Holm-significant; C equivalent (Holm p 0.725); A, B, D, U inconclusive | same |
| R4a-ii table (3 tests) | 98.33% difference and 96.67% TOST intervals | `tables/tab_r4a.tex` ← CSV |
| Original vs corrected | A −0.101 [−0.155, −0.048]; B +0.026 [−0.039, +0.090]; U −0.200 [−0.275, −0.124] (×10⁻³, Welch 95%, descriptive) | `stats_r4a.json` → `original_vs_corrected` |
| Capture differences | about 4,870 vs 6,300 DDoS flows per minute; prevalence 64.3% vs 58.2%; at least 16 changed inputs | `PHASE3_R4A_COMPARISON.md` §A |
| D-021 cap-200 check | r1 D s0 and s5: stopped at 124 and 114 epochs; errors 8 → 9 and 14 → 13; d stays +0.148 ×10⁻³, Holm p 0.047 | `d021_sensitivity.json`, `d021_comparison.json` |

## 5. Base-paper numbers (author-reported, marked † in Table IX)

| Paper | Value | Where it comes from |
|---|---|---|
| Nezhadsistani et al. | F1 0.9993 on CIC-IDS2017 (their Table 6); 5-fold CV | `PHASE3_BASELINE_COMPARISON.md` §1 (checked against the PDF in earlier milestones) |
| Fang et al. | MCC 0.9355 for the full model in Table 6 (ablation), Table 3 (held-out test; train 55,998 + 12,264, test 37,000 + 4,089) and Table 4 (nested five-fold CV); stated stratified 70/30 split; protocol of Table 6 not stated; AUROC 0.999; 22 of 47 features | Fang et al. PDF (`../project/paper3.pdf`) pp. 7, 13, 17, 18, 22, read 2026-11-15; `PHASE3_BASELINE_COMPARISON.md` §3 |
| Wardana et al. | Scenario 2, Table 10: average accuracy 96.67%, F1 95.36%, per-network accuracy 87.92 to 99.84%; Scenario 3 is new-network integration (Table 11) | same §2 (scenario numbering checked from the PDF text on 2026-11-13) |
| Engelen et al. | 25.9% of flows are TCP appendices | handover [paper7.pdf p.3] |
| Engelen extended documentation | aggregate flag counters update only on the first packet | `docs/evidence/engelen_extended_2026-11-09.md` |

## 6. Wording rules from CLAUDE.md, as applied

| Rule | Where it is applied |
|---|---|
| r1 difference intervals 99.5%, TOST 99% | Table X caption and header; Fig. 11 caption; §III-H |
| R4a difference 98.33%, TOST 96.67% | Table XI; Fig. 12; §III-H; §VII-B |
| "Equivalent within the pre-declared margin" | readings in Tables X and XI; §VII; §VII-D explains the margin against baselines of about 6 and 2 errors |
| R4a-i "associated with", never causal | §V-B ("Successful transfer is thus associated with the absence of the flag-count fields"); Table VI caption says "Descriptive" |
| R4a-ii vs r1 observational | §III-I, §VII-B, Table XI(b), Fig. 12(b) |
| MES-DNN per network, never pooled | §V-D, Table VIII, Table IX; the pooled 85.5% / 0.715 values are not used |
| N1 base unchanged; ensemble collapse is a stacking effect; only N2 base drop tied to duplicate hold-out | §V-D, Fig. 9 caption |
| Wardana Scenario 2 is our analogue; no unseen-network claim | §II-A, §VI, Table IX |
| ARR "all registered" 23 vs group U 20 | §III-F |
| Baselines are adaptations, not ranked | §I, §III-J, Table III, §VI |
| D-021 numbers (8→9, 14→13) | §VII-C |
| Agreed limitation paragraph | §VIII-D, adapted only for flow |
| Headline sentence | abstract, §I, §IX |

## 7. Additions in the revision for the updated rubric (2026-11-15)

| Claim | Value | Source |
|---|---|---|
| Author contact details | e-mail for both authors (phone numbers removed in the final polish) | supplied by the authors in chat, 2026-11-15 |
| Funding; conflicts of interest | no external funding; no competing interests | confirmed by the authors in chat, 2026-11-15 |
| Corrected R4a group members (Table II) | A: ACK, CWE, ECE, FIN, PSH, RST, SYN Flag Count, Fwd PSH Flags, Bwd PSH Flags (9); B: Bwd Packet Length Mean, Avg Bwd Segment Size, Fwd Header Length and duplicate, Init_Win_bytes_forward, SYN Flag Count, Total Fwd Packets, min_seg_size_forward (8); U: A ∪ B ∪ four C features (20) | `configs/protocol/r4a_groups_v1.yaml` → `groups` |
| Control-draw rule and seed bases | `RandomState(b + 100g + d)`, b = 3000 (r1, order A, B, C, D, U), b = 7000 (R4a, order A, B, U) | `configs/protocol/ablation_groups_3a_r1.yaml`, `r4a_groups_v1.yaml` → `random_seed_rule` |
| Control pools | 46 (r1), 52 (R4a) | same files → `control_pool` |
| Split seed and fractions | seed 42, 70/15/15 by equivalence class, both designs | `configs/experiments/ae_xgb_d008_trackB.yaml`, `ae_xgb_r4a_trackB.yaml` |
| Split fingerprints | `50bd994880abbe15…` (r1), `acd52bd8295ffe29…` (R4a) | same configs; `verify_r1.json` `split_fingerprint` |
| Test-population hashes | `2893fd3c5eca6aa5…` (r1), `4804537214604662…` (R4a) | `verify_r1.json` `population_test_sha256`; `verify_r4a.json` `population.sha256` |
| Dataset archive hashes | `MachineLearningCSV.zip` `c3f26274b36c837c…`; Engelen `dataset.zip` `4d535da19795d853…` | `verify_r1.json` `dataset_sha256`; `results/protocol/r4a/r4a_feasibility_v1.json` |
| Constant inputs on the corrected training partition | Fwd URG Flags, Bwd URG Flags, URG Flag Count, Subflow Bwd Packets | `r4a_groups_v1.yaml` → `constant_on_train` |
| Code commits | `659c35d` (r1), `b6297226` (R4a; training path identical) | `verify_r1.json` `git_commit`; `PHASE3_EXPERIMENT_AUDIT.md` line 93; `PHASE3_FINAL_SIGNOFF.md` §3 |
| Registry chronology (§VIII-E) | flag-count family added after an earlier SHAP pilot ranked ACK Flag Count first; whole documented family added; groups frozen before ablation training | `docs/MILESTONE_2B_CORRECTIONS.md`; `CNET_COMPLETE_PROJECT_HANDOVER.md` §8; `configs/protocol/*.yaml` headers |
| Fig. 7 annotation | full-model recall range 0–87.9%, mean 8.8% | `verify_r4a.json` → `r4a_i`, kind `full` |

Wording rules from the updated brief, as applied: the DCNN comparison is "same trained models, two populations" (§V-C, §VI, §VIII-C, Fig. 8); the MES-DNN comparison is "separately retrained under two split protocols" (§III-A H4, §V-D, §VI, §VIII-C, Figs. 4 and 9); no difficulty ranking of the two captures (§V-B); Fang's published MCC is not tied to our split (§VI, Table IX).
