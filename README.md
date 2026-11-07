# How Real Is 99% Accuracy? Auditing Feature Reliance in Network Intrusion Detection

CNET Phase III implementation: Ali Waseem (23i-2630), Muhammad Mudassir (23i-2562), FAST-NUCES Islamabad.

The research question is whether high-scoring NIDS models rely on
dataset-specific artifacts. The planned method is:

- SHAP attributions;
- an evidence-tagged artifact registry and ARR@K;
- controlled retrained ablations;
- corrected-capture and cross-domain evaluation.

The planned baselines are:

| Baseline | Paper |
|---|---|
| AE-XGBoost | Nezhadsistani et al. 2026 |
| MES-DNN | Wardana et al. 2026 |
| SHAP-selected DCNN + self-attention | Fang et al. 2026 |

**Status: Milestone 1A implemented; first real training run not yet executed.**
No full model has been trained and no experimental result exists. Local runs
were tiny smoke runs and timing benchmarks only.

| Capability | State |
|---|---|
| Dataset manifest, download / verify / extract (all 4 datasets downloaded and verified locally) | Implemented |
| Dataset inspection (28 descriptive reports in `results/inspection/`) | Implemented |
| Invalid-row rules, train-only preprocessing, duplicate-aware split (0 shared vectors across all 3 partition pairs), leakage checks | Implemented; unit + real-data tests |
| Config-driven runs (`src/config.py`), environment/device/seed recording (`src/env.py`) | Implemented; tested on Windows CPU |
| **AE-XGBoost baseline** (`src/experiments/ae_xgb.py`; D-008 scope, D-007 track B): resumable AE, latent augmentation (disabled, see D-017), XGBoost, metrics | Implemented; tested on synthetic data + a tiny real-data CPU smoke run |
| Google Colab execution (`notebooks/colab_runner.ipynb`, `docs/COLAB_EXECUTION_PLAN.md`) | Workflow ready; **not executed on Colab**; needs D-015 Amendment 1 |
| MES-DNN, DCNN + self-attention baselines | Planned |
| SHAP attribution, artifact registry, ARR@K, ablations, repeated seeds, statistics | Planned |

- **Research decisions:** in `docs/decision_log.md`.
  - Approved: D-001, D-003, D-008, D-011.
  - D-007: track-B split approved and implemented.
  - D-002: deferred.
  - D-017: lists every deviation from the AE-XGBoost paper.
- **Checks:** Milestone 0 checks in `docs/milestone0_checklist.md`; Milestone 1A handover in `docs/MILESTONE_1A_HANDOVER.md`.

## Layout

```
configs/      base.yaml (paths, seed, split/preprocessing policy)
              datasets.yaml (acquisition manifest)
configs/experiments/  one YAML per experiment, overlaid on base.yaml by src/config.py
.venv/        Python environment, created by scripts/setup_env.ps1 (Git-ignored)
data/raw/     original datasets, one folder per manifest id (Git-ignored)
data/processed/
src/config.py effective run config (base.yaml + experiment), preprocessor factory, leakage assertion
src/env.py    CPU/CUDA selection, seeding, environment + provenance snapshot (python -m src.env)
src/data/     manifest.py, acquire.py, load.py, inspection.py, preprocess.py, split.py,
              ddos.py (D-008 scope: verified file, D-011 rules, track-B split)
src/models/   autoencoder.py (resumable), augment.py (latent Gaussian), xgb.py
src/experiments/  ae_xgb.py (runner: stages, resume, benchmark)
src/audit/    SHAP, artifact registry, ARR@K (later)
src/evaluation/  metrics.py (binary metrics, DDoS = positive)
tests/        synthetic-data unit tests + real-data tests (skip without data)
scripts/      setup_env.ps1, inspect_all.ps1 (Windows conveniences)
notebooks/    colab_runner.ipynb (thin Colab launcher; scaffold, not yet run)
docs/         decision_log.md, milestone0_checklist.md, COLAB_EXECUTION_PLAN.md
results/      figures, tables, run metadata
paper/        IEEE LaTeX manuscript
```

## Platforms

| Machine | Role |
|---|---|
| Windows 11 laptop, CPU only (i7-1265U, 16 GB RAM, no CUDA) | Development and tests |
| Google Colab GPU runtimes | Heavy training and evaluation, from Milestone 1 (D-016) |

- **Same commands everywhere:** every step is a `python -m src.<module>` call, which works the same on Linux/Colab.
- **Windows conveniences only:** `run.cmd` and `scripts/*.ps1`.
- **Data and Colab:** no data goes to Google Drive or Colab until D-015 is amended (see `docs/COLAB_EXECUTION_PLAN.md`).

## Setup (Windows, one time)

1. Install Python 3.11 from python.org. You can skip this step if it is
   already installed.

   ```powershell
   winget install --id Python.Python.3.11 --exact --scope user
   ```

2. From the repository folder, create the environment, install the pinned
   dependencies and run the tests:

   ```powershell
   powershell -ExecutionPolicy Bypass -File scripts\setup_env.ps1
   ```

**Where things live.** Everything stays inside the project folder:

- the environment in `.venv\`
- datasets in `data\raw\<dataset id>\`
- prepared data in `data\processed\`

All three are Git-ignored. The only thing outside the folder is the Python
3.11 installation itself, which `.venv` is built from.

Re-run the setup script whenever `requirements.txt` changes. It reuses the
existing `.venv`.

`-ExecutionPolicy Bypass` applies to that one command only. It does not change
your system policy.

## Usage

Run everything through `run.cmd`, which calls the venv's Python directly. No
activation is needed, and it works in both PowerShell and cmd:

```powershell
.\run.cmd -m pytest
.\run.cmd -m src.data.manifest --hash
.\run.cmd -m src.data.inspection data\raw\unsw_nb15\UNSW_NB15_training-set.csv --label label --json results\inspection\unsw_train.json
```

- `manifest` checks the manifest and lists which files are on disk. With
  `--hash` it also computes sha256 checksums.
- `inspection` reports a dataset's schema, label counts, missing/infinite
  values, duplicates and leakage candidates. The label column name in the
  example is unconfirmed.

**VS Code / Jupyter.** VS Code detects `.venv` automatically. If it does not,
select `.venv\Scripts\python.exe` (Command Palette → "Python: Select
Interpreter").

**Activating the venv in a terminal.**

- In cmd, run `.venv\Scripts\activate.bat`.
- In PowerShell, `Activate.ps1` is blocked by the default script policy unless
  you choose to allow it yourself with
  `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`. `run.cmd` avoids the
  need.

### Getting the datasets

```powershell
.\run.cmd -m src.data.acquire download all   # fetch every file with a scripted official source
.\run.cmd -m src.data.acquire verify all     # check sizes and sha256 against the manifest
.\run.cmd -m src.data.acquire extract all    # unzip archives into data\raw\<id>\extracted\
```

Downloads come only from the sources recorded in `configs/datasets.yaml`:

| Source | How it is fetched |
|---|---|
| Engelen corrected CICIDS2017 | direct link |
| UNSW-NB15 | the official SharePoint share |
| NF-UNSW-NB15-v2 | the UQ RDM API |

**Manual step: original CIC-IDS2017.** Its download sits behind CIC's
registration form at https://cicresearch.ca/CICDataset/CIC-IDS-2017/. Submit
the form in a browser and save `MachineLearningCSV.zip` (and
`GeneratedLabelledFlows.zip`) into `data\raw\cicids2017_original\`. Then run
`verify` and `extract`.

Extraction refuses archive entries that would land outside the target folder.

### Preprocessing and splitting

Runs are driven by a config:

- `configs/base.yaml` holds project defaults.
- One file in `configs/experiments/` overlays them per experiment.
- `src/config.py` rejects any setting the code does not implement and builds the preprocessor from the config.

```python
from src.config import load_config, make_preprocessor, check_no_leaky_outputs, write_run_record
from src.data.split import stratified_split, check_disjoint, save_split, load_split

cfg = load_config("configs/experiments/<experiment>.yaml")
split = stratified_split(df[cfg["experiment"]["label"]], seed=cfg["seed"])   # or group / temporal / predefined
check_disjoint(split, len(df))
save_split(split, "results/runs/<run>/split.json", source={"dataset": ..., "files": {...}, "n_rows": len(df)})
pre = make_preprocessor(cfg)            # drops the config's label + identifier columns
X_train = pre.fit_transform(df.iloc[split.train])   # statistics from train only
X_test = pre.transform(df.iloc[split.test])
check_no_leaky_outputs(pre.output_columns, cfg)
write_run_record(cfg, "results/runs/<run>", extra={"split_fingerprint": split.fingerprint()})
```

Two safety checks:

- **Undeclared text columns fail.** A column that is neither declared categorical nor numeric raises an error instead of becoming NaN.
- **Edited split files are refused.** `load_split` rejects a split file whose indices, seed or source were edited. It also checks the expected dataset and row count you pass in.

**Real-data checks.** `tests/test_real_data_smoke.py` runs two checks. Each one skips when its data isn't downloaded.

1. **UNSW-NB15 official partition:** the full chain through `configs/experiments/smoke_unsw_official.yaml`.
2. **CICIDS2017 Friday DDoS scope (D-008):** the D-011 row rules with logged counts, then the D-007 duplicate-aware split (`content_groups` + `group_split`). It shows 0 cross-split duplicates, against 486 test-row leaks for a random split.

```powershell
.\run.cmd -m pytest tests\test_real_data_smoke.py -v
```

### AE-XGBoost baseline

The tiny local smoke run takes seconds; its results are meaningless by design. The timing benchmark uses the real training partition and does not train.

```powershell
.\run.cmd -m src.experiments.ae_xgb --config configs/experiments/ae_xgb_d008_smoke.yaml
.\run.cmd -m src.experiments.ae_xgb --config configs/experiments/ae_xgb_d008_trackB.yaml --device cpu --benchmark
```

The real run is on Colab: see `docs/COLAB_EXECUTION_PLAN.md`, "First real run".

**Environment record** (Python, OS, CPU, RAM, GPU, package versions, Git commit, dataset hashes):

```powershell
.\run.cmd -m src.env --dataset cicids2017_original
```

## Ground rules

- **Official sources only.** Use only the sources listed in
  `configs/datasets.yaml`. Changing a source or a corrected-dataset version
  requires a decision-log entry first.
- **Train-only fitting.** Everything that is fitted (imputation, scaling,
  vocabularies, feature selection, oversampling, thresholds) uses the training
  partition only.
- **No universal split.** A random row split is not assumed to be safe.
  D-007 has two tracks: a paper-comparable protocol and a leakage-resistant,
  duplicate-aware split. Both report cross-split duplicate rates.
- **Paper figures are not our results.** Numbers from the papers are labelled
  author-reported. Our own results come only from logged runs.
