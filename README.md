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

## Setup

```bash
python -m pip install -r requirements.txt
python -m pip install -e .
python -m pytest
```

The editable install (`pip install -e .`) is needed for the `python -m src...`
commands when the interpreter does not put the working directory on `sys.path`.
That applies to the embeddable Python on the development machine (decision log
D-014).

## Usage

```bash
python -m src.data.manifest --hash
python -m src.data.inspection data/raw/unsw_nb15/UNSW_NB15_training-set.csv --label label --json results/inspection/unsw_train.json
```

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
