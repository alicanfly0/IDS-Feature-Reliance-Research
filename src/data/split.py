"""Deterministic train/val/test splits and leakage checks.

Splits are returned as positional index arrays into the source frame, so the
source records are never copied or reordered. Which strategy is valid depends
on the dataset (decision log D-007): a random row split can place duplicated
flows, or flows from the same session/host/time window, on both sides.

Strategies:
  stratified_split  - random, label-stratified (Phase II proposal; needs checks)
  group_split       - whole groups (session, host pair, capture day) per side
  temporal_split    - ordered by time, earlier rows train, later rows test
  predefined_split  - a split the publisher shipped (e.g. UNSW-NB15 train/test sets)
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.model_selection import GroupShuffleSplit, train_test_split

PARTS = ("train", "val", "test")


@dataclass
class Split:
    train: np.ndarray
    val: np.ndarray
    test: np.ndarray
    strategy: str
    seed: int | None
    params: dict = field(default_factory=dict)

    def parts(self) -> dict[str, np.ndarray]:
        return {"train": self.train, "val": self.val, "test": self.test}

    def fingerprint(self) -> str:
        digest = hashlib.sha256()
        for name, idx in self.parts().items():
            digest.update(name.encode())
            digest.update(np.sort(idx).astype(np.int64).tobytes())
        return digest.hexdigest()


def _check_fractions(fractions: tuple[float, float, float]) -> None:
    if len(fractions) != 3 or any(f < 0 for f in fractions) or not np.isclose(sum(fractions), 1.0):
        raise ValueError(f"fractions must be three non-negative values summing to 1, got {fractions}")
    if fractions[0] == 0 or fractions[2] == 0:
        raise ValueError("train and test fractions must be positive")


def stratified_split(labels, fractions=(0.70, 0.15, 0.15), seed: int = 42) -> Split:
    _check_fractions(fractions)
    labels = np.asarray(labels)
    idx = np.arange(len(labels))
    train_f, val_f, test_f = fractions
    train, rest = train_test_split(idx, train_size=train_f, stratify=labels, random_state=seed)
    if val_f == 0:
        val, test = np.array([], dtype=int), rest
    else:
        val, test = train_test_split(
            rest, test_size=test_f / (val_f + test_f), stratify=labels[rest], random_state=seed
        )
    return Split(np.sort(train), np.sort(val), np.sort(test), "stratified_random", seed, {"fractions": list(fractions)})


def group_split(groups, fractions=(0.70, 0.15, 0.15), seed: int = 42) -> Split:
    """Fractions apply to groups, not rows; class balance is not guaranteed (check it)."""
    _check_fractions(fractions)
    groups = np.asarray(groups)
    idx = np.arange(len(groups))
    train_f, val_f, test_f = fractions
    outer = GroupShuffleSplit(n_splits=1, train_size=train_f, random_state=seed)
    train, rest = next(outer.split(idx, groups=groups))
    if val_f == 0:
        val, test = np.array([], dtype=int), rest
    else:
        inner = GroupShuffleSplit(n_splits=1, test_size=test_f / (val_f + test_f), random_state=seed)
        v, t = next(inner.split(rest, groups=groups[rest]))
        val, test = rest[v], rest[t]
    return Split(np.sort(train), np.sort(val), np.sort(test), "group", seed, {"fractions": list(fractions)})


def temporal_split(times, fractions=(0.70, 0.15, 0.15)) -> Split:
    """Rows ordered by time; ties stay together so no timestamp spans two parts."""
    _check_fractions(fractions)
    times = pd.Series(np.asarray(times))
    if times.isna().any():
        raise ValueError("temporal_split requires a timestamp for every row")
    unique = np.sort(times.unique())
    counts = times.value_counts().reindex(unique).to_numpy()
    cum = np.cumsum(counts) / counts.sum()
    train_end = unique[min(np.searchsorted(cum, fractions[0]), len(unique) - 1)]
    val_end = unique[min(np.searchsorted(cum, fractions[0] + fractions[1]), len(unique) - 1)]
    t = times.to_numpy()
    train = np.flatnonzero(t <= train_end)
    val = np.flatnonzero((t > train_end) & (t <= val_end))
    test = np.flatnonzero(t > val_end)
    return Split(train, val, test, "temporal", None, {"fractions": list(fractions)})


def predefined_split(assignment) -> Split:
    """`assignment` holds 'train' / 'val' / 'test' per row (e.g. from the source file name)."""
    a = np.asarray(assignment)
    unknown = set(np.unique(a)) - set(PARTS)
    if unknown:
        raise ValueError(f"unknown split labels: {unknown}")
    return Split(*(np.flatnonzero(a == p) for p in PARTS), "predefined", None)


def check_disjoint(split: Split, n_rows: int) -> None:
    """Raise if any row appears twice, falls outside the frame, or is unassigned."""
    parts = split.parts()
    all_idx = np.concatenate(list(parts.values()))
    if len(all_idx) != len(np.unique(all_idx)):
        raise AssertionError("a row is assigned to more than one partition")
    if len(all_idx) and (all_idx.min() < 0 or all_idx.max() >= n_rows):
        raise AssertionError("split index out of range")
    if len(all_idx) != n_rows:
        raise AssertionError(f"{n_rows - len(all_idx)} rows are unassigned")


def cross_split_duplicates(df: pd.DataFrame, split: Split, feature_cols: list[str]) -> dict[str, int]:
    """Count evaluation rows whose exact feature vector also occurs in train."""
    train_keys = set(pd.util.hash_pandas_object(df.iloc[split.train][feature_cols], index=False))
    out = {}
    for name in ("val", "test"):
        idx = getattr(split, name)
        keys = pd.util.hash_pandas_object(df.iloc[idx][feature_cols], index=False)
        out[name] = int(keys.isin(train_keys).sum())
    return out


def group_overlap(groups, split: Split) -> dict[str, int]:
    """Number of groups shared between train and val/test."""
    groups = np.asarray(groups)
    train_groups = set(groups[split.train])
    return {name: len(train_groups & set(groups[getattr(split, name)])) for name in ("val", "test")}


def class_proportions(labels, split: Split) -> dict[str, dict[str, float]]:
    labels = pd.Series(np.asarray(labels))
    return {
        name: {str(k): float(v) for k, v in labels.iloc[idx].value_counts(normalize=True).items()}
        for name, idx in split.parts().items()
    }


def save_split(split: Split, path: str | Path, source: dict) -> None:
    """Write indices plus provenance; `source` should identify the exact input (e.g. file sha256s)."""
    payload = {
        "strategy": split.strategy,
        "seed": split.seed,
        "params": split.params,
        "source": source,
        "fingerprint": split.fingerprint(),
        **{name: idx.tolist() for name, idx in split.parts().items()},
    }
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(payload), encoding="utf-8")


def load_split(path: str | Path) -> Split:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    split = Split(
        *(np.asarray(payload[p], dtype=int) for p in PARTS),
        strategy=payload["strategy"], seed=payload["seed"], params=payload["params"],
    )
    if split.fingerprint() != payload["fingerprint"]:
        raise ValueError(f"split file {path} fails its fingerprint check")
    return split
