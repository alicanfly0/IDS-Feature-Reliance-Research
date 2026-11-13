# Baselines: our adaptations vs the three source papers

**Author-reported** numbers come from the source PDFs as recorded in `CNET_COMPLETE_PROJECT_HANDOVER.md` §2.2 (verified against the PDFs in earlier milestones; not re-read in this audit, because the laptop has no PDF renderer). **Ours** are our measurements, recomputed from saved predictions in this audit. None of our implementations is a reproduction. **No quantitative comparison below is fair as a head-to-head benchmark**, for the reasons in the "material differences" rows.

## 1. Nezhadsistani et al., AE-XGBoost

**Reference:** Nezhadsistani, Tajgardan, Rabbani, Niu, Stiller, "Design and evaluation of a robust and explainable intrusion detection framework for 5G/B5G networks", *Computer Networks* 278 (2026) 112100, doi 10.1016/j.comnet.2026.112100.

| | Author-reported | Ours (r1, AE-XGBoost adaptation) |
|---|---|---|
| Architecture | AE 120→80→40→80→120 (ReLU), latent Gaussian minority augmentation, XGBoost on the latent codes, SHAP | AE inputs→80→40 (ReLU, linear output), XGBoost (lr 0.11, depth 6, 2,000-round cap, early stopping 50) on the latent codes. Augmentation disabled: attack is not the minority (89,577 vs 68,421). |
| Data / task | CIC-IDS2017 DDoS subset (225,745 rows, 78 features) **jointly** with 5G-NIDD and a 5G dataset; binary | CICIDS2017 Friday DDoS file only; binary DDoS vs benign; 68 inputs after train-only preprocessing |
| Protocol | 5-fold CV (Table 7) | Duplicate-aware track-B split 70/15/15; family-common twin-excluded test (33,038); 10 seeds; GPU (T4) |
| Metrics | F1 0.9993 on CIC-IDS2017 (Table 6); LODO F1 0.9089 | F1 0.999849 (0.999792–0.999922), MCC 0.999639, AUROC 0.999996, accuracy 0.999824, 5.8 errors per 33,038 |
| Material differences | | Training data, folds vs split, duplicate control, augmentation, input width, SHAP model (theirs explains raw names over latent codes; ours uses permutation SHAP on the composite model) |
| Fair to compare? | No | Our higher F1 shows only that this single-file task is saturated under our split; it is not an improvement over their joint multi-dataset model |

## 2. Wardana et al., MES-DNN (SNI-CIDS)

**Reference:** Wardana, Kołaczek, Warzyński, Sukarno, Adiwijaya, "SNI-CIDS: Collaborative intrusion detection using modified ensemble stacking deep neural networks for new network integration in heterogeneous networks", *Future Generation Computer Systems* 177 (2026) 108252.

| | Author-reported | Ours (D-010 two-network adaptation) |
|---|---|---|
| Architecture | Five base DNNs 39-9-7-5-3-1 (ReLU, sigmoid), frozen; meta Dense(10, ReLU)→Dense(1, sigmoid); Adam, BCE, batch 1000, 10 epochs | Same layer sizes and training. **Two** base DNNs. Fixed log1p input transform, then per-base standardisation; Adam lr 1e-3 (paper silent). |
| Data | NF-UNSW-NB15-v2, NF-ToN-IoT-v2, NF-BoT-IoT-v2, NF-CSE-CIC-IDS2018-v2, NF-UQ-NIDS-v2 (Table 3 counts below the official totals) | N1 NF-UNSW-NB15-v2 (all 2,390,275 flows); N2 a uniform NF-ToN-IoT-v2 subsample of equal size (default_rng(42), from 16,940,496) |
| Inputs | 39 | Same 39 (43 NetFlow features minus 4 IP/port fields) |
| Protocol | Random 70/30; 10% of train as meta sample; 10% of test as validation; scenarios incl. new-network integration | 63/7/3/27% disjoint partitions per network; **random** and **duplicate-aware** (each exact vector in one partition, partitioner v2); 5 seeds each; all networks integrated |
| Metrics | **Scenario 2** (integrated five-network stack MES-DNN0, tested on each network TS1–TS5; Table 10): average accuracy 96.67%, recall 95.17%, precision 95.82%, F1 95.36%; per-network accuracy 87.92–99.84%. **Scenario 3** (new-network integration; Table 11): average accuracy 89.23%, F1 71.09%. Scenario numbering checked against the PDF text on 2026-11-13. | **Per network**, ensemble, mean [range] over 5 seeds (table below). Our setting is the two-network analogue of Scenario 2. |
| Material differences | | 2 vs 5 networks; ToN subsample; input transform; a duplicate-aware mode the paper does not use. Their Table 10 is per network, so a per-network description is possible; a ranked comparison is still not fair. |
| Fair to compare? | No | Our ensemble's instability and its collapse under duplicate-aware splits are findings about the adaptation and about duplication, not about their five-network model |

**Our MES-DNN ensemble results, per network, mean [range] over 5 seeds:**

| Network, split | Accuracy | F1 | MCC | AUROC |
|---|---|---|---|---|
| N1, random | 0.941 [0.771, 0.995] | 0.665 | 0.658 [0.166, 0.938] | 0.927 |
| N1, duplicate-aware | 0.536 [0.326, 0.877] | 0.087 | 0.001 [−0.101, 0.134] | 0.678 |
| N2, random | 0.769 [0.611, 0.946] | 0.764 | 0.625 [0.412, 0.884] | 0.952 |
| N2, duplicate-aware | 0.699 [0.630, 0.946] | 0.804 | 0.242 [0.061, 0.890] | 0.865 |

**Own-network base models (MCC):**

| Network | Random | Duplicate-aware |
|---|---|---|
| N1 | 0.939 | 0.940 |
| N2 | 0.906 | 0.150 (FPR 0.888) |

**Cross-network base models (MCC):**
- N1 base on N2: 0.053 (random), 0.459 (duplicate-aware).
- N2 base on N1: −0.03 (random), −0.07 (duplicate-aware).

**Interpretation (revised after the independent audit):**
- N1's own base model keeps MCC ≈ 0.94 under **both** split modes (0.939 random, 0.940 duplicate-aware).
- The N1 ensemble collapse (0.658 → 0.001) is therefore **not** explained by losing duplicated test rows. It arises in the stacking step: the meta-model sees only the two base scores, the N2 base model transfers badly to N1 (MCC ≈ −0.03 to −0.07), and duplicate-aware partitioning also changes the meta-sample composition.
- Only the **N2 own base model** (0.906 → 0.150) shows a drop directly attributable to holding out whole duplicate groups. Even there, the giant 422,766-row benign group also changes partition composition.

**Not claimed:** a faithful five-network reproduction, or generalisation to an unseen network (none was held out).

**Pooling caveat:** the draft paper's "85.5% / 0.715" and "61.7% / 0.445" are means over the two networks (prevalence 4.0% vs 64.0%). Report per network instead.

## 3. Fang et al., DCNN + self-attention

**Reference:** Fang, Xuan, Ding, "An efficient method for network traffic anomaly detection based on SHAP and deep learning", *PLOS One* 21(8) (2026) e0356069.

| | Author-reported | Ours (D-009 adaptation) |
|---|---|---|
| Architecture | LightGBM + TreeSHAP selects 22 of 47 features (95% cumulative rule); Conv1D blocks + 4-head self-attention; dense head; L2 1e-3 | Same as the authors' released code (Conv1D 32→64, k3, BN, ReLU; 4-head SA, key_dim 16, residual + LayerNorm; Dense 128→Dropout 0.3→64→sigmoid), in PyTorch with Keras defaults matched |
| Data / task | UNSW-NB15 Normal vs DoS; **Normal positive**; stated stratified 70/30, counts match the official partition | Official partition, Normal + DoS (train 68,264 / test 41,089); **DoS positive**; preprocessing fitted on train only (194 transformed columns) |
| Selection | 95% rule → 22 | K = 22 fixed by approval. The 95% rule gives **30** on our training data; 22 cover 90.5%. Not retrained with 30. |
| Protocol | Seed 42; 5-fold CV; Wilcoxon | 5 seeds (0–4); official test plus model-visible duplicate-filtered test (3,330 twins removed); raw-feature filter as sensitivity |
| Metrics | MCC 0.9015 (DCNN) → 0.9355 (full model), AUROC 0.999, AUPRC 0.992 | Official: MCC 0.784 [0.763, 0.801], AUROC 0.995, DoS recall 0.975, DoS precision 0.669, FPR 0.053. Filtered: MCC 0.719, AUROC 0.992. Raw filter: MCC 0.781. |
| Material differences | | Polarity (MCC is symmetric, but precision and recall are not), CV vs fixed partition, K, seeds, framework |
| Fair to compare? | Partly (MCC and AUROC are polarity-free) | Our adaptation stays well below the reported MCC on the same official partition; the cause is not established (possibly framework, preprocessing or tuning). This is not evidence that their number is wrong. |

## Conclusions

- The three comparisons show how strongly each reported figure depends on split, population and protocol.
- Two of our results are the same-model, two-population contrasts (DCNN official vs filtered; MES-DNN random vs duplicate-aware). These are internally fair comparisons because model and data are held fixed, and they are the defensible quantitative statements.
- Cross-paper differences must be described, not ranked.
