# Baseline adaptations: Fang DCNN + self-attention (D-009) and two-network MES-DNN (D-010)

Both are **adaptations**. Neither is claimed as a reproduction of the source paper. Numbers are
reported only from the result records named below.

## 1. Fang et al. 2026, DCNN + self-attention (UNSW-NB15, Normal vs DoS)

Sources inspected before implementation:
- the paper (`../project/paper3.pdf`);
- the authors' repository `github.com/ZHF123775838/WSN-DCNN-SHAP`: `models.py`, `test.py`,
  `shap_sort.py`, `data_utils.py`.

Code: `src/models/dcnn.py`, `src/experiments/dcnn_fang.py`. Tests: `tests/test_dcnn.py`.
Records: `results/dcnn_fang/selection.json`, `seed{0..4}/metrics.json`, `summary.json`.

| Item | Source (paper / repository) | Ours | Why |
|---|---|---|---|
| Data split | Paper: stratified 70/30 of the pooled data | Official UNSW-NB15 training/testing partitions, Normal + DoS rows (train 56,000 / 12,264; test 37,000 / 4,089) | D-009; publisher partition, no split choice |
| Positive class | Normal (paper p.14) | DoS = 1; both class-conditional views reported | Consistency with the other experiments |
| Preprocessing | `data_utils.py`: median / "Unknown" imputation, 1st/99th winsorising, min–max, one-hot | Same, fitted on the training partition only | — |
| Input width | Paper: 47 → 22 | 194 transformed columns → 22 | One-hot of proto/service/state on this subset gives 194 |
| Selection | LightGBM (300 trees, lr 0.05, 31 leaves, subsample 0.8, colsample 0.8, seed 42) + TreeExplainer on train; 95 % cumulative mean\|SHAP\| | Same model and explainer; **K = 22 fixed** (approved spec) | The 95 % rule gives **30** features on our training data (22 cover 90.5 %); recorded, not used |
| Architecture | Code: Conv1D 32 → Conv1D 64 (k 3, same, BN, ReLU), 4-head self-attention (key_dim 16) + residual + LayerNorm, Dense 128 → Dropout 0.3 → Dense 64 → sigmoid; L2 1e-3 | Same, in PyTorch; Keras defaults matched (Glorot init, BN eps 1e-3 / momentum 0.99, LN eps 1e-3, Adam eps 1e-7) | Paper text says 3×3 kernels and 64 first-layer maps; we follow the released code |
| Training | `test.py`: 20 % stratified validation, 50 epochs, batch 128, Adam 5e-4, EarlyStopping(10, restore best), ReduceLROnPlateau(0.1, 5, min 1e-6), balanced class weights | Same; best-validation weights restored also when 50 epochs complete | Explicit choice |
| Seeds | 42 | 0–4 (validation split and initialisation) | D-009: 5 seeds |
| Test populations | Single test set | (a) official test; (b) **duplicate-filtered**: test rows whose model-visible float32 input equals any training-partition row removed (3,330 removed, 37,759 kept); (c) raw-feature duplicate filter as sensitivity (1,395 removed) | D-009 |

**Attribution.** The LightGBM SHAP values explain the selector, not the DCNN. Any attribution of
the DCNN uses its own explainer. No artifact registry exists for UNSW-NB15, so no ARR
classification is made (D-012/D-013).

## 2. Wardana et al. 2026, MES-DNN: two-network adaptation

Code: `src/data/netflow.py`, `src/experiments/mes_dnn.py`. Tests: `tests/test_mes_dnn.py`.
Records: `results/protocol/mesdnn/ton_subsample_v1.json`, `results/mes_dnn/networks.json`,
`{random,dup_aware}_seed{0..4}/metrics.json`, `summary.json`.

| Item | Paper | Ours | Why |
|---|---|---|---|
| Networks | Five NetFlow-v2 datasets (N1–N5) | **Two**: N1 NF-UNSW-NB15-v2 (all 2,390,275 flows); N2 a fixed uniform subsample of NF-ToN-IoT-v2 of the same size (numpy `default_rng(42)`, no replacement, from 16,940,496 flows) | D-010; compute and storage |
| Inputs | 39 (Table 2 / Table 6) | The same 39 (43 minus 4 IP/port fields) | D-001 |
| Partitions | 70/30; train 90 % base / 10 % meta sample; test 90 % test / 10 % validation | Same proportions (63 / 7 / 3 / 27 %), all four disjoint | — |
| Split modes | Random | **random** (stratified rows) and **dup_aware** (each exact 39-input vector in one partition, stratified by majority label) | D-010 |
| Base DNN | 39-9-7-5-3-1, ReLU, sigmoid, Adam, BCE, batch 1000, 10 epochs | Same; Glorot init; Adam lr 1e-3 (Keras default) | Paper gives no learning rate |
| Scaling | Not stated | Fixed elementwise `log1p` (no fitted parameters), then standardisation with mean/std of each base model's own base partition | Paper silent. **Measured:** the NF-ToN-IoT-v2 subsample holds `SRC_TO_DST_SECOND_BYTES` up to 4.0e152 and `DST_TO_SRC_SECOND_BYTES` up to 1.9e257 (22 and 23 rows beyond the float32 maximum); raw standardisation overflowed to NaN in the first attempt (stopped, nothing recorded). Counts per network are in `networks.json` |
| Meta-model | Frozen bases, concatenated outputs, Dense 10 ReLU, Dense 1 sigmoid, 10 epochs, batch 1000 | Same, trained on the union of both meta samples (scenario 1, all networks integrated) | Scenario 2 (unseen network) needs ≥ 3 networks; not attempted |
| Validation | Monitors base training | Monitored and recorded; no early stopping | As the paper |
| Seeds | Not stated | 0–4 per mode: 10 ensemble fits | D-010 |
| Evaluation | Test partition | Each network's test partition; in random mode also the subset of test rows whose vector never occurs in base/meta/validation ("novel") | Duplicate-leakage audit |

**Not claimed:** a faithful five-network reproduction, or generalisation to an unseen network.
No artifact registry exists for NetFlow-v2 (the Engelen/Lanvin defects concern CICFlowMeter),
so no ARR classification is made.
