"""Train-only preprocessing.

Two kinds of step, kept apart on purpose:

* Row rules (`invalid_row_mask`) use no fitted statistics, so they may run
  before splitting. They return a mask; nothing is dropped implicitly.
* `TrainOnlyPreprocessor` learns everything (constant columns, medians,
  min/max, category vocabularies) from the training partition only and then
  applies the same mapping to validation/test. Input frames are never mutated.

Every kept column must be either declared categorical or numeric. A value that
does not parse as a number in an undeclared column is an error, not a silent
NaN, and transform() refuses to return non-finite output.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd


def invalid_row_mask(
    df: pd.DataFrame,
    check_missing: bool = True,
    check_infinite: bool = True,
    nonnegative_cols: tuple[str, ...] = (),
) -> pd.DataFrame:
    """Boolean frame with one column per rule; `.any(axis=1)` gives rows to review/drop."""
    numeric = df.select_dtypes(include="number")
    rules = {}
    if check_missing:
        rules["missing"] = df.isna().any(axis=1)
    if check_infinite:
        rules["infinite"] = pd.Series(np.isinf(numeric.to_numpy()).any(axis=1), index=df.index)
    for col in nonnegative_cols:
        rules[f"negative:{col}"] = df[col] < 0
    return pd.DataFrame(rules, index=df.index)


@dataclass
class TrainOnlyPreprocessor:
    drop_cols: tuple[str, ...] = ()          # identifiers / labels, removed by name
    categorical_cols: tuple[str, ...] = ()   # one-hot encoded with the training vocabulary
    drop_constant: bool = True
    clip_to_train_range: bool = False        # False keeps out-of-range test values visible (>1 or <0)

    fitted_: bool = field(default=False, init=False)
    n_fit_rows_: int = field(default=0, init=False)
    numeric_cols_: list[str] = field(default_factory=list, init=False)
    constant_cols_: list[str] = field(default_factory=list, init=False)
    medians_: dict[str, float] = field(default_factory=dict, init=False)
    mins_: dict[str, float] = field(default_factory=dict, init=False)
    maxs_: dict[str, float] = field(default_factory=dict, init=False)
    categories_: dict[str, list] = field(default_factory=dict, init=False)

    def _numeric(self, df: pd.DataFrame, cols: list[str], stage: str) -> pd.DataFrame:
        parsed = df[cols].apply(pd.to_numeric, errors="coerce")
        bad = {}
        for c in cols:
            # Textual missing markers ("nan", "") are missing data, not unparseable text.
            given = df[c].notna() & ~df[c].astype(str).str.strip().str.lower().isin(("nan", ""))
            n_bad = int((given & parsed[c].isna()).sum())
            if n_bad:
                bad[c] = n_bad
        if bad:
            raise TypeError(
                f"{stage}: non-numeric values in columns not declared categorical {bad}; "
                "add them to categorical_cols or drop_cols"
            )
        return parsed.replace([np.inf, -np.inf], np.nan)

    def fit(self, train: pd.DataFrame) -> "TrainOnlyPreprocessor":
        missing = [c for c in (*self.drop_cols, *self.categorical_cols) if c not in train.columns]
        if missing:
            raise KeyError(f"columns not in training frame: {missing}")
        kept = [c for c in train.columns if c not in self.drop_cols]
        if self.drop_constant:
            self.constant_cols_ = [c for c in kept if train[c].nunique(dropna=False) <= 1]
        kept = [c for c in kept if c not in self.constant_cols_]

        cats = [c for c in self.categorical_cols if c in kept]
        self.numeric_cols_ = [c for c in kept if c not in cats]
        num = self._numeric(train, self.numeric_cols_, "fit")
        self.medians_ = num.median().to_dict()
        filled = num.fillna(self.medians_)
        self.mins_ = filled.min().to_dict()
        self.maxs_ = filled.max().to_dict()
        self.categories_ = {c: sorted(train[c].dropna().astype(str).unique()) for c in cats}
        self.n_fit_rows_ = len(train)
        self.fitted_ = True
        return self

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        if not self.fitted_:
            raise RuntimeError("fit() must be called on the training partition first")
        num = self._numeric(df, self.numeric_cols_, "transform").fillna(self.medians_)
        lo = pd.Series(self.mins_)
        span = pd.Series(self.maxs_) - lo
        span = span.where(span != 0, 1.0)
        scaled = (num - lo) / span
        if self.clip_to_train_range:
            scaled = scaled.clip(0.0, 1.0)
        parts = [scaled]
        for col, vocab in self.categories_.items():
            values = df[col].astype(str)
            onehot = pd.DataFrame(
                {f"{col}={v}": (values == v).astype(np.float64) for v in vocab}, index=df.index
            )
            parts.append(onehot)
        out = pd.concat(parts, axis=1)
        nonfinite = out.columns[~np.isfinite(out.to_numpy()).all(axis=0)].tolist()
        if nonfinite:
            # e.g. a column that was entirely missing in train (median is NaN)
            raise ValueError(f"transform produced non-finite values in {nonfinite}")
        return out

    def fit_transform(self, train: pd.DataFrame) -> pd.DataFrame:
        return self.fit(train).transform(train)

    @property
    def output_columns(self) -> list[str]:
        cols = list(self.numeric_cols_)
        for col, vocab in self.categories_.items():
            cols += [f"{col}={v}" for v in vocab]
        return cols

    def state(self) -> dict:
        """Serializable record of what was learned, for experiment metadata."""
        return {
            "n_fit_rows": self.n_fit_rows_,
            "dropped_by_name": list(self.drop_cols),
            "dropped_constant_on_train": self.constant_cols_,
            "numeric_cols": self.numeric_cols_,
            "categories": self.categories_,
            "clip_to_train_range": self.clip_to_train_range,
        }
