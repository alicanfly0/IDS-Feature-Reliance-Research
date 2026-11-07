# Milestone 1A handover — AE-XGBoost baseline, Colab-first

Date: 2026-11-08. Continues Milestone 0 commit `98620bd`. The commit hash of this work is reported with the delivery; a file cannot contain its own commit hash.

**What does not exist yet:**

- no full training run has been made, locally or on Colab;
- **no experimental result exists**;
- every metric printed so far comes from a tiny smoke run (3,000 training rows, 3 epochs) and is meaningless by design.

## 1. Implemented

| File | What it does |
|---|---|
| `src/data/ddos.py` | D-008 scope. Verifies `MachineLearningCSV.zip` (manifest sha256 + CIC MD5) before use; extracts only the Friday DDoS member if needed and checks its CRC; applies the D-011 rules with per-rule counts and excluded source rows; keeps `-1` window sentinels; excludes conflicting-label groups; makes the track-B split and refuses to continue if any partition pair shares a feature vector. All counts are recomputed, not assumed |
| `src/data/split.py` | `content_groups` (exact, library-version-independent), `group_split` (NumPy legacy `RandomState`, so identical on laptop and Colab), `conflicting_groups`, `partition_overlap` (all three pairs) |
| `src/models/autoencoder.py` | Configurable AE (paper default 80/40, ReLU, Adam 1e-3, batch 256). Early stopping on validation reconstruction MSE, best weights restored. Atomic per-epoch checkpoints (model, optimizer, epoch, early-stopping state, RNG states, config). Resume is bit-identical on CPU |
| `src/models/augment.py` | Paper Eq. 4 latent Gaussian augmentation, training-only, with the paper's minority-attack rule. Disabled in the primary run because DDoS is the majority class |
| `src/models/xgb.py` | XGBoost on latent codes (`device` cpu/cuda, `hist`), validation early stopping, values checked against the paper's Table 5 ranges |
| `src/evaluation/metrics.py` | Accuracy, precision, recall, F1 (DDoS = positive), macro-F1, AUROC, MCC, confusion matrix, class counts |
| `src/experiments/ae_xgb.py` | Runner with resumable stages, never overwriting a finished run, and identity checks (config hash, device, dataset hash, Git commit). Saves split, preprocessing state, checkpoints, latent codes, model, predictions, metrics and run record. Timing benchmark with projection |
| `configs/experiments/ae_xgb_d008_trackB.yaml` / `ae_xgb_d008_smoke.yaml` | Real experiment (seed 0, cuda) / tiny smoke run (cpu, subsample) |
| `src/env.py` | Commit from a code bundle (`CNET_GIT_COMMIT`) when there is no `.git` |
| `src/data/acquire.py` | `verify <dataset> --file <name>`, to verify only the transferred archive |
| `notebooks/colab_runner.ipynb` | Runnable thin workflow: GPU check → D-015 switch → code bundle (or token-safe GitHub) → missing packages + tests → copy and verify one archive → GPU benchmark → run → results |
| `requirements.txt` | + `torch==2.15.0` (CPU on Windows), `xgboost==3.2.0`. Colab uses its own stack (see file) |
| `docs/decision_log.md` | D-007 track B exact procedure and measurements; D-012 (Destination Port retained); D-015 Amendment 1 **proposed**; D-016 benchmark note; **D-017** deviations from the paper |

## 2. Verified locally (Windows CPU) — actual results

| Check | Result |
|---|---|
| Full test suite (`.\run.cmd -m pytest -q -rs -W default`) | **93 passed, 0 failed, 0 skipped**, no warnings (91 unit, 2 real-data) |
| Same suite on a copy without data | **91 passed, 2 skipped** (real-data tests skip with their reason) |
| Real-data D-008 counts (recomputed) | 225,745 raw → 36 invalid (4 missing, 34 infinite, 2 negative duration; 34 BENIGN / 2 DDoS) → **225,709** kept (DDoS 128,025 / BENIGN 97,684); forward `-1` 32,925/32,925 kept, backward 88,274/88,299 kept |
| Track-B split, seed 42 | 157,998 / 33,834 / 33,877 rows (DDoS 89,577 / 19,215 / 19,233); **0 / 0 / 0** shared vectors (train–val / train–test / val–test), also 0 after preprocessing; fingerprint `50bd9948…447f44` pinned in the config |
| Feature dimension | **68** on the full training partition (78 − 10 constant columns) |
| Tiny smoke run, CLI, real data | `ae_xgb_d008_smoke`: end to end in 7.7 s; augmentation correctly skipped; DONE written |
| Timing benchmark, CPU, real 157,998-row training partition | AE 0.92 s/epoch (≤ 1.5 min for 100 epochs); XGBoost 9 ms/round (≤ 0.3 min for 2,000 rounds); data preparation 12.8 s |
| Code bundle | `git archive` zip stores the exact commit id that the notebook checks; no data inside |
| Notebook | 9 code cells parse; no Windows-only paths; no token in persisted URLs; Drive mount behind the D-015 switch |
| Repository hygiene | 108 files scanned: no datasets, secrets, personal registration data or local absolute paths |

**Focused tests:**

- **`tests/test_ae_xgb.py`:** labels and rules; conflicting groups; split reproducibility; AE dimensions and finiteness; latent extraction; bit-identical resume after a simulated crash; early stopping restoring the best weights; augmentation rule and determinism; XGBoost fit/predict/save/load; metrics with the positive class; CUDA request failing without a GPU; runner end to end, including no-overwrite, AE not retrained after an XGBoost-stage disconnect, refusal to resume under a different commit, and split reuse across configs.
- **`tests/test_split.py`:** pinned frozen-RNG split; exact groups; all-pair overlap.

## 3. Not verified until a real Colab run

- Colab's package versions and the test suite there.
- CUDA execution of the AE and of XGBoost (`device="cuda"`).
- GPU timing.
- Drive I/O and checkpointing to Drive.
- Real disconnect/resume on Colab.
- **The first real training run and its metrics.**

## 4. First real run

Follow `docs/COLAB_EXECUTION_PLAN.md`, "First real run — exact steps". The command the notebook runs is:

    python -m src.experiments.ae_xgb --config configs/experiments/ae_xgb_d008_trackB.yaml --device cuda --storage /content/drive/MyDrive/cnet-runs

**Outputs:**

- `MyDrive/cnet-runs/runs/ae_xgb_d008_trackB-seed0-cuda-<hash>/`: metrics.json, predictions, run_record.json, checkpoints, log.
- `MyDrive/cnet-runs/splits/ae_xgb_d008_trackB-split.json`.

## 5. Scientifically significant deviations from the paper

Full table: **D-017**.

- **Scope and protocol:** one CICIDS2017 file, binary. Duplicate-aware 70/15/15 hold-out instead of 5-fold CV and synthetic test sets.
- **Input width:** 68, not 120. The first layer widens 68 → 80; the paper's 80/40 widths are kept.
- **Unstated details filled with labelled choices:** linear output layer, early-stopping patience 10.
- **Augmentation:** implemented but **not applied**, because DDoS is the majority class and the paper augments minority attack classes only.
- **XGBoost:** fixed a priori inside the paper's ranges with validation early stopping, instead of the paper's (unreported) grid search.
- **Comparison wording:** results are a documented adaptation and must not be presented as an exact reproduction of the paper's 0.9993 F1.

## 6. Blockers and decisions for you

1. **D-015 Amendment 1** (proposed text in the decision log). Authorize it before any data or code reaches Google.
2. **Where to run the first baseline.** The CPU benchmark says the full single-seed run takes minutes on the laptop. Colab is kept as instructed, but running small baselines locally would need no cloud transfer at all. Your call (D-016 note).
3. **GitHub remote:** optional. The code-bundle path works without one.
4. **After the first results:** additional seeds, track A (paper-comparable 5-fold), the Destination Port ablation and SHAP (D-002) need approval.
