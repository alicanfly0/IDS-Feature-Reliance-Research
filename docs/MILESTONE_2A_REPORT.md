# Milestone 2A — Artifact registry, original-feature SHAP and ARR@K (pilot)

> **Historical registry-v1 report.** Milestone 2B supersedes its evidence classifications, ARR@K interpretation and proposed confirmatory use of test-selected features. See [MILESTONE_2B_CORRECTIONS.md](MILESTONE_2B_CORRECTIONS.md). Original pilot outputs remain unchanged. D-015 upload authorization was granted after this historical report.

Date: 2026-11-08. Model explained: `ae_xgb_d008_trackB-seed0-cpu-565a8b9e` (CICIDS2017 Friday DDoS, D-008, track-B split, commit 6fed9b0). Nothing was retrained. Method decisions: decision log D-002, D-012, D-019.

## 1. What was built

| Part | File | Status |
|---|---|---|
| Artifact registry (12 feature entries, 7 flow/label/process issues) | `configs/artifact_registry.yaml` | implemented, validated, tested |
| Registry loader and validation rules | `src/audit/registry.py` | implemented, tested |
| ARR@K (per evidence tier, duplicate-column merge, NaN on zero denominator) | `src/audit/arr.py` | implemented, tested on synthetic values |
| Composite model raw features → preprocessing → AE → XGBoost, from saved artifacts | `src/audit/composite.py` | implemented, checked against the saved run, tested |
| Permutation SHAP: sampling, checks, caching, global/local outputs, stability, plots | `src/audit/shap_explain.py` | implemented, tested, pilot run |
| Tests | `tests/test_audit.py` (16) | passing |

Run it again (cached variants are read, not recomputed):

```powershell
.\run.cmd -m src.audit.shap_explain --config configs/experiments/ae_xgb_d008_trackB.yaml --run results/runs/ae_xgb_d008_trackB-seed0-cpu-565a8b9e --background 100 --explain 200 --permutations 5 --variants 0:0 1:0 0:1 1:1
.\run.cmd -m src.audit.shap_explain --config configs/experiments/ae_xgb_d008_trackB.yaml --run results/runs/ae_xgb_d008_trackB-seed0-cpu-565a8b9e --summarize
```

## 2. Registry

Evidence levels: **direct_extraction_error** (values are wrong for affected flows), **shortcut_indicator** (values are correct but mark artifact flows, so a model can use them as a shortcut), **unverified_hypothesis** (suspected, no paper evidence for this dataset). Code rule: a level above hypothesis needs a source with section and page from a paper we hold; Phase II or local notes alone are not enough.

| ID | Column(s) | Level | Concerns | Source |
|---|---|---|---|---|
| R01 | `Destination Port` | unverified hypothesis | generation process | Engelen §III-D p.4 (left open); Phase II Step 4; local: D-018 ablation, no measurable effect |
| R02 | `Init_Win_bytes_forward` | shortcut indicator | flow | Engelen §IV-B.1 p.5 |
| R03 | `Init_Win_bytes_backward` | unverified hypothesis | generation process | Phase II Step 4 only |
| R04 | `min_seg_size_forward` | shortcut indicator | flow | Engelen §IV-B.1 p.5 |
| R05 | `Fwd Header Length`, `Fwd Header Length.1` | shortcut indicator | flow | Engelen §IV-B.1 p.5 |
| R06 | `Total Fwd Packets` | shortcut indicator | flow | Engelen §IV-B.1 p.5 |
| R07 | `SYN Flag Count` | shortcut indicator | flow | Engelen §IV-B.1 p.5 |
| R08 | `Bwd Packet Length Mean` | shortcut indicator | flow | Engelen §IV-B.1 p.5 |
| R09 | `Flow IAT Min` | direct extraction error | feature | Lanvin §3.3 pp.8–9 (Table 5), §4.2 Q3 p.15 |
| R10 | `Flow IAT Mean` | direct extraction error | feature | Lanvin §4.2 Q3 p.15 |
| R11 | `Flow Packets/s` | direct extraction error | feature | Lanvin §4.2 Q3 p.15 |
| R12 | `Bwd Packets/s` | direct extraction error | feature | Lanvin §4.2 Q3 p.15 |

Non-column issues (not in ARR@K): F01 TCP appendix flows, F02 RST not ending flows, F03 swapped direction (Engelen §III-A p.3; Lanvin §3.1 pp.6–7), F04 duplicated capture packets (Lanvin §3.3 pp.8–9), L01 attempted attacks labelled as attacks (Engelen §III-B.2 p.3), L02 unlabelled port scan (Lanvin §3.4 p.9), I01 identifiers (Engelen §III-D p.4, hypothesis).

Not established: that the Lanvin duplication features are wrong **in the Friday DDoS flows used here** (the affected flows are not identified in the MachineLearningCVE CSV); that any registered feature is an artifact **for this model**. The levels need team confirmation (D-012).

## 3. SHAP method (D-019 in full)

- **Explained function:** the saved preprocessing, AE encoder and XGBoost as one function of the 78 raw columns. Latent SHAP values are not computed or relabelled.
- **Explainer:** `shap.explainers.Permutation` 0.49.1, antithetic permutations; cost per explained row = `permutations × (2·78+1)` function evaluations on every background row.
- **Output:** XGBoost margin (log-odds of DDoS); probabilities are saturated.
- **Masking:** interventional, independent masker. Breaks dependence between features and can create unrealistic flows; attributions are the model's response to these substitutions, not causal effects.
- **Background:** stratified sample of the **train** partition. **Explained:** stratified sample of the **test** partition; misclassified rows explained separately.
- **Precision:** float64 evaluation of the saved weights (batch-invariant); float32 inference changed one background row's margin by 0.083 depending on batching. All test predictions are identical to the saved run; probabilities differ by at most 8.9e-4.
- **Checks per variant (all passed):** shape (n, 78) and column order = data columns; all values finite; additivity |Σφ + base − f(x)| ≤ 5.3e-15; base value = mean background margin (≤ 9e-16); the 10 columns the model ignores get exactly 0.
- **Provenance:** `settings.json` per variant (seeds, source row IDs of background and explained rows, model identity and commit, split fingerprint, shap version); `summary.json` (runtime, checks, importances, ARR@K).

## 4. Pilot (CPU, laptop)

| Variant (background n×seed, explained n×seed, permutations) | Runtime |
|---|---|
| bg 100×0, ex 200×0, p5 | 39.9 s |
| bg 100×1, ex 200×0, p5 | 33.9 s |
| bg 100×0, ex 200×1, p5 | 33.9 s |
| bg 100×1, ex 200×1, p5 | 35.6 s |
| bg 200×0, ex 200×0, p5 | 91.0 s |
| bg 100×0, ex 200×0, p10 | 118.6 s |
| local: 5 misclassified + 4 correct, bg 100, p5 | < 5 s |

Total about 6 minutes of CPU. Cost scale: ~0.17 s per explained row (bg 100, p5), roughly proportional to background size × permutations. Explaining the whole test partition (33,877 rows) at these settings would take ~1.6 h on this laptop; it is not needed for the ranking questions below and was not run.

### Global importance (mean |SHAP|, log-odds, mean over 6 variants; merged duplicate column)

| Rank | Feature | mean \|SHAP\| | Registry |
|---|---|---|---|
| 1 | ACK Flag Count | 2.35 | — |
| 2 | Average Packet Size | 1.69 | — |
| 3 | Packet Length Mean | 1.47 | — |
| 4 | PSH Flag Count | 1.18 | — |
| 5 | Bwd Packet Length Max | 1.10 | — |
| 6 | Destination Port | 1.08 | R01 hypothesis |
| 7 | Fwd IAT Total | 0.92 | — |
| 8 | Idle Max | 0.92 | — |
| 9 | Init_Win_bytes_forward | 0.90 | R02 shortcut |
| 10 | Flow Duration | 0.89 | — |
| 15 | min_seg_size_forward | 0.58 | R04 shortcut |

Ranks of the other registered features (all variants): Bwd Packet Length Mean 28–30, SYN Flag Count 32–35, Fwd Header Length 41–45, Total Fwd Packets 50–54; direct-error features Flow IAT Mean 33–35, Flow Packets/s 44–49, Bwd Packets/s 53–59, Flow IAT Min 57–62.

### Stability across the 6 variants

- Rank correlation over the union of Top-20 lists (22 features): minimum 0.973.
- Top-5 shared by all variants: 4 of 5; Top-10: 8 of 10; Top-20: 18 of 20.
- Destination Port rank 4–6; Init_Win_bytes_forward 7–11; min_seg_size_forward 15–17.

### ARR@K (merged importances; range over the 6 variants)

| K | direct extraction errors | shortcut indicators | all registered (incl. hypotheses) |
|---|---|---|---|
| 2 | 0.00 | 0.00 | 0.00 |
| 5 | 0.00 | 0.00 | 0.00–0.15 |
| 10 | 0.00 | 0.00–0.08 | 0.08–0.16 |
| 20 | 0.00 | 0.07–0.09 | 0.13–0.15 |

### Local explanations (bg 100, p5)

- The two benign rows predicted DDoS (5245, 5246; margins 4.8, 4.4): largest push towards DDoS from ACK Flag Count; packet-length features push towards benign.
- Benign row 155712 predicted DDoS (margin 8.9): PSH Flag Count and Max Packet Length push towards DDoS.
- DDoS row 110943 predicted benign (margin −10.3): Destination Port (value 64869, not 80) is the second-largest push towards benign (−2.2), after Down/Up Ratio. It is one of the 3 DDoS flows in the file not on port 80.
- DDoS row 99515 predicted benign: packet-length features dominate.

## 5. Interpretation limits

- The ranking is stable under the sampling choices tried, so the findings describe this model, not sampling noise.
- **ARR@K is low for both evidence-backed tiers:** no direct-extraction-error feature is in any Top-20, and shortcut indicators hold at most ~9 % of Top-20 attribution. This does not show that the model is free of artifacts. Attribution goes to correlated features (packet-length statistics and flag counts) that can carry the same information as registered ones, and the independent masker splits credit among correlated features unpredictably.
- **Destination Port** carries the most attribution of any registered feature (rank ~6), while D-018 found no measurable change when it is removed and the model retrained. Both can be true: the model uses the port when it is present, and other features substitute for it when it is absent. It stays an unverified hypothesis.
- Interventional masking evaluates the model on unrealistic flows, which affects magnitudes. Results hold for one model, one seed, one dataset file and 200 explained test rows.

## 6. Not done / blockers

- No full-test-set SHAP (not needed; ~1.6 h CPU if wanted).
- No Colab run: not needed (CPU is enough), and D-015 Amendment 1 (upload) is not authorized.
- Registry levels need team confirmation (D-012); the Lanvin duplicated flows in the Friday file are not identified.
- No group ablation of registered features and no second model seed (outside 2A).

## 7. Recommended next experiment

A **group ablation of the attribution leaders vs the registered groups** under the D-018 design (same split, eval-twin exclusion, paired McNemar on common rows): (a) remove the Engelen shortcut group (R02, R04–R08) and (b) remove Destination Port plus the Top-5 SHAP features, each retrained with ≥3 seeds. This tests whether the attributed features are needed for the 0.9999 F1, which SHAP alone cannot show.
