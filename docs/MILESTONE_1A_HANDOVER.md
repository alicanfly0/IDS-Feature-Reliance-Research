# Milestone 1A handover — AE-XGBoost baseline

Date: 2026-11-08. Continues Milestone 0 commit `98620bd`. Implementation commit: `6fed9b0`.

**Status:**

| Item | State |
|---|---|
| **First full training run** | **Done on the laptop CPU** (user decision, D-016 Amendment 1): one model seed, D-008 scope, D-007 track B. Results in §2b; they are our only experimental result so far |
| **Colab GPU execution** | **Not done.** The Colab workflow is prepared and statically checked but has never been executed; nothing has been uploaded to Google (D-015) |
| Tiny smoke run | Also made (3,000 training rows, 3 epochs); its metrics are meaningless by design and are not results |
| Not started | Additional seeds, the paper-comparable track A, ablations, SHAP |

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
| `configs/experiments/ae_xgb_d008_trackB.yaml` / `ae_xgb_d008_smoke.yaml` | Real experiment (seed 0; config default device `cuda`, the completed run used `--device cpu`) / tiny smoke run (cpu, subsample) |
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

## 2b. First full run — laptop CPU (user decision, D-016 Amendment 1)

| Item | Value |
|---|---|
| Run | `ae_xgb_d008_trackB-seed0-cpu-565a8b9e` |
| Commit | `6fed9b0` |
| Duration | 1.45 min |
| Command | `.\run.cmd -m src.experiments.ae_xgb --config configs/experiments/ae_xgb_d008_trackB.yaml --device cpu` |
| Config hash / split fingerprint | `565a8b9e62065f93…` / `50bd994880abbe15…` (pinned) |
| Summary files | `results/baselines/<run>/` (checkpoints, latent codes and model stay in Git-ignored `results/runs/`) |
| Model outcome | Input dimension 68; AE early-stopped at epoch 60 (best 50); XGBoost 204 trees; augmentation not applicable; 0 / 0 / 0 partition overlap |
| **Test (33,877 rows)** | Accuracy 0.999852, precision 0.999844, recall 0.999896, **F1 0.999870**, macro-F1 0.999850, AUROC 0.999992, **MCC 0.999699** |
| Test confusion matrix (TN / FP / FN / TP) | 14,641 / 3 / 2 / 19,231 |
| Validation | F1 0.999870, MCC 0.999699 |

**Limits:**

- One model seed only.
- Not comparable to the paper's author-reported numbers (different protocol, D-017).
- Shortcut reliance is untested until the ablations run.

## 3. Not verified, because Colab has never been executed

- Colab's package versions and the test suite there.
- CUDA execution of the AE and of XGBoost (`device="cuda"`).
- GPU timing.
- Drive I/O and checkpointing to Drive.
- Real disconnect/resume on Colab. Resume is verified locally by tests only.
- Whether a GPU run reproduces the CPU run's metrics. Not expected to be bit-identical; to be compared when a GPU run exists.

## 4. Colab GPU run (prepared, not executed)

Only needed for GPU workloads (D-016 Amendment 1). Follow `docs/COLAB_EXECUTION_PLAN.md`, "First real run — exact steps", after authorizing D-015 Amendment 1. The notebook runs:

    python -m src.experiments.ae_xgb --config configs/experiments/ae_xgb_d008_trackB.yaml --device cuda --storage /content/drive/MyDrive/cnet-runs

**Outputs would be:**

- `MyDrive/cnet-runs/runs/ae_xgb_d008_trackB-seed0-cuda-<hash>/`: a separate run id from the CPU run.
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

1. **Decided:** the first baseline ran on the laptop CPU (D-016 Amendment 1).
2. **D-015 Amendment 1** (proposed text in the decision log) is still needed before any Colab GPU run. Nothing has reached Google.
3. **GitHub remote:** optional. The code-bundle path works without one.
4. **Next experiments need approval:** additional seeds, track A (paper-comparable 5-fold), the Destination Port ablation, and SHAP (D-002).
