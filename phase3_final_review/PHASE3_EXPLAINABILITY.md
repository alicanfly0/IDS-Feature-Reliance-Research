# Explainability: SHAP, ARR and baseline attribution

This is a consolidation of existing records. **No SHAP was recomputed.**

**Sources:**
- `results/shap/ae_xgb_d008_trackB-seed0-cpu-565a8b9e/` (M2A)
- `results/corrections/milestone2b/corrected_arr_v2.json` (M2B, registry v2)
- `results/attribution_pilot/{dcnn,mes}.json`
- `docs/MILESTONE_2B_CORRECTIONS.md`

## 1. AE-XGBoost original-feature SHAP

| Item | Value |
|---|---|
| Model explained | **One** model: the Milestone 1A baseline `ae_xgb_d008_trackB-seed0-cpu-565a8b9e` (laptop CPU, seed 0, the same Friday DDoS task and duplicate-aware split as r1). Test F1 0.99987, MCC 0.99970 on 33,877 rows. It is **not** one of the 110 r1 models. |
| Method | `shap.explainers.Permutation` (shap 0.49.1) on the composite AE→XGBoost **margin** (log-odds of DDoS), so attributions are on the 68 original inputs, not the latent codes. Interventional `Independent` masker; background = stratified **training** sample; explained rows from **test**. |
| Precision | float64 model evaluation. The deployed runner uses float32 inputs to the AE, so explanations describe the float64 composite (known limitation, M2A). Stored-array additivity error ≤ 3.8×10⁻⁷ per variant. |
| Six variants | Background 100 or 200 × two background draws × two explained-row draws × 5 or 10 permutations |
| Ranking stability | Pairwise Spearman over all 68 features 0.9945–0.9993; over the top-20 union ≥ 0.973. Intersections: top-5 has 4 common features, top-10 has 8, top-20 has 18. |
| Top-ranked | **ACK Flag Count first in all 6 variants**, then Average Packet Size, Packet Length Mean, PSH Flag Count, Bwd Packet Length Max, Destination Port, Init_Win_bytes_forward |

## 2. Evidence registry v2 and ARR

**Definition.** ARR@K = (sum of mean |SHAP| of the registered features within the top K) / (sum of mean |SHAP| of all top K features). It is an importance-weighted mass share, **not** a count.

**Registry v2 tiers** (`corrected_arr_v2.json` → `membership`):

| Tier | Size | Members |
|---|---|---|
| Direct extraction defects | 16 | 12 TCP flag fields (ACK, Bwd PSH, Bwd URG, CWE, ECE, FIN, Fwd PSH, Fwd URG, PSH, RST, SYN, URG) and 4 duplicated-packet timing fields (Bwd Packets/s, Flow IAT Mean, Flow IAT Min, Flow Packets/s) |
| Shortcut | 6 | Bwd Packet Length Mean, Fwd Header Length, Init_Win_bytes_forward, SYN Flag Count, Total Fwd Packets, min_seg_size_forward |
| Hypothesis only | 2 | Destination Port, Init_Win_bytes_backward |
| All registered | 23 | The union of the three tiers. SYN is in both direct and shortcut. |

Registry v1 lacked the flag-count defect family; its 0% / 13–15% values are **historical and superseded**. `stability_all_variants.json` → `arr_merged_range` still holds v1 values, so do not cite it.

**ARR, primary aggregation sum |SHAP|, range over the 6 variants:**

| K | All registered | Direct | Shortcut | Hypothesis |
|---|---|---|---|---|
| 2 | 55.0–60.8% | 55.0–60.8% | 0 | 0 |
| 5 | 43.7–60.7% | 43.7–46.1% | 0 | 0–14.6% |
| 10 | 35.9–45.1% | 27.4–28.9% | 0–7.6% | 8.2–9.1% |
| 20 | 34.7–36.8% | 21.3–22.2% | 7.4–8.7% | 5.6–6.2% |

The signed aggregation gives the same ARR@20 for "all" within the reported ranges (sensitivity in `corrected_arr_v2.json`).

**Duplicate-feature grouping sensitivity:**
- Merging documented duplicate columns (e.g. `Fwd Header Length` / `.1`) changes no top-K membership and gives a maximum ARR difference of 0.0 in every variant (`duplicate_comparison`).
- The duplicate column ranks 41st.

**Original vs corrected ARR.** ARR exists **only for the original-data model.** No SHAP was computed on R4a models; corrected-data attribution is not available.

**Terminology warning.** ARR's "all registered" (23 features, including the D hypotheses) is **not** the same set as ablation group U (20 features, A ∪ B ∪ C, excluding D).

## 3. Attribution concentration vs reliance

| Question | Evidence | Status |
|---|---|---|
| Does attribution concentrate on defect features? | ACK Flag Count is top-1; the direct tier holds 55–61% of top-2 mass and 21–22% of top-20 mass | Observed (one model, descriptive) |
| Does in-domain accuracy depend on them? | Retraining without group A: +3 errors per 33,038 vs random control (Holm p 0.020; inside SESOI) | Statistical: small, practically negligible |
| Does cross-extractor behaviour depend on them? | R4a-i: DDoS recall 0.09 with A, 0.96 without A | Descriptive; confounded with definition changes |

**Conclusion.** SHAP mass concentration identified the features that matter for **transfer** (R4a-i) but greatly overstated their importance for **in-domain** accuracy, where redundant features compensate. Attribution concentration must not be reported as causal reliance.

## 4. DCNN + self-attention pilot (D-009)

- **Method:** `shap.GradientExplainer` on each seed's DCNN; 500 training background rows; 1,000 class-balanced explained rows from the **duplicate-filtered** test population.
- **Stability across 5 seeds:** mean pairwise Spearman 0.909 (min 0.857); mean top-5 overlap 0.78. The top features are sttl, ct_state_ttl, dttl, sloss and swin; proto_tcp and ct_srv_dst appear in some seeds.
- **Agreement with the LightGBM selector's SHAP ranking:** Spearman 0.43, 0.38, 0.48, 0.47 and 0.28. **The selector's SHAP explains LightGBM, not the DCNN**, and the two rankings agree only weakly.
- **No ARR:** no artifact registry exists for UNSW-NB15. None is invented.

## 5. MES-DNN pilot (D-010)

- **Method:** GradientExplainer on the ensemble (inputs in log1p space); 500 background rows; 1,000 explained rows per network.

| Mode / network | Mean Spearman (min) | Mean top-5 overlap |
|---|---|---|
| Random / N1 | 0.727 (0.566) | 0.46 |
| Random / N2 | 0.874 (0.822) | 0.48 |
| Duplicate-aware / N1 | 0.691 (0.643) | 0.44 |
| Duplicate-aware / N2 | 0.859 (0.772) | 0.50 |

- **Top features:** retransmission, ICMP-type and TTL fields (N1); TCP flags, TTL and window fields (N2).
- **No ARR:** there is no NetFlow-v2 registry (the CICFlowMeter defects do not apply).

## 6. Scope and limits

- **AE-XGBoost SHAP** covers one model and one seed, uses float64, and explains test rows of the inspected population.
- **Permutation SHAP** with an independent masker attributes over correlated features, so mass can shift among proxies. Duplicate-grouping sensitivity was checked; general correlation was not.
- **Baseline pilots** are descriptive stability checks, not reliance tests.
