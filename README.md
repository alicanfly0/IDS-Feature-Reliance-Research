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

**Status: Milestone 0.** This milestone covers the repository, dataset
provenance, inspection, train-only preprocessing and split utilities. No
dataset has been downloaded, no model has been trained, and the repository
contains no results.

## Layout

```
configs/      base.yaml (paths, seed, split/preprocessing policy)
              datasets.yaml (acquisition manifest)
.venv/        Python environment, created by scripts/setup_env.ps1 (Git-ignored)
data/raw/     original datasets, one folder per manifest id (Git-ignored)
data/processed/
src/data/     manifest.py, load.py, inspection.py, preprocess.py, split.py
src/models/   baselines (Milestone 1+)
src/audit/    SHAP, artifact registry, ARR@K (Milestone 1+)
src/evaluation/  metrics, ablations, statistics (Milestone 1+)
tests/        synthetic-data tests for everything in src/data
docs/         decision_log.md, milestone0_checklist.md
results/      figures, tables, run metadata
paper/        IEEE LaTeX manuscript
```

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

- `manifest` checks the manifest and lists which files are on disk. With
  `--hash` it also computes sha256 checksums.
- `inspection` reports a dataset's schema, label counts, missing/infinite
  values, duplicates and leakage candidates. The label column name in the
  example is unconfirmed.

### Preprocessing and splitting

```python
from src.data.split import stratified_split, check_disjoint, cross_split_duplicates
from src.data.preprocess import TrainOnlyPreprocessor

split = stratified_split(df["Label"], seed=42)   # or group_split / temporal_split / predefined_split
check_disjoint(split, len(df))
pre = TrainOnlyPreprocessor(drop_cols=(...), categorical_cols=(...)).fit(df.iloc[split.train])
X_test = pre.transform(df.iloc[split.test])
```

## Ground rules

- **Official sources only.** Use only the sources listed in
  `configs/datasets.yaml`. Changing a source or a corrected-dataset version
  requires a decision-log entry first.
- **Train-only fitting.** Everything that is fitted (imputation, scaling,
  vocabularies, feature selection, oversampling, thresholds) uses the training
  partition only.
- **No universal split.** A random row split is not assumed to be safe. The
  split strategy is chosen per dataset (D-007) and checked for duplicates and
  group overlap.
- **Paper figures are not our results.** Numbers from the papers are labelled
  author-reported. Our own results come only from logged runs.
