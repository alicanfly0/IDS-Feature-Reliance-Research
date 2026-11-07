"""Deterministic train/val/test splits and leakage checks.

Splits are returned as positional index arrays into the source frame, so the
source records are never copied or reordered. Which strategy is valid depends
on the dataset (decision log D-007): a random row split can place duplicated
flows, or flows from the same session/host/time window, on both sides.

Strategies:
  stratified_split  - random, label-stratified (Phase II proposal; needs checks)
  group_split       - whole groups (session, host pair, capture day) per side;
                      with content_groups(), identical feature vectors stay together
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
from sklearn.model_selection import train_test_split

PARTS = ("train", "val", "test")


@dataclass
class Split:
    train: np.ndarray
    val: np.ndarray
    test: np.ndarray
    strategy: str
    seed: int | None
    params: dict = field(default_factory=dict)
    source: dict = field(default_factory=dict)  # filled by load_split

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
    """Whole groups per partition; fractions apply to groups, not rows (measure row/class shares).

    Groups are shuffled with NumPy's legacy RandomState, whose stream is frozen across
    NumPy versions, so the same groups and seed give the same split on every machine
    (e.g. Windows locally and Colab), independent of scikit-learn's version.
    """
    _check_fractions(fractions)
    _, codes = np.unique(np.asarray(groups), return_inverse=True)
    codes = codes.reshape(-1)
    n_groups = codes.max() + 1 if len(codes) else 0
    order = np.random.RandomState(seed).permutation(n_groups)
    n_train = int(round(fractions[0] * n_groups))
    n_val = int(round(fractions[1] * n_groups))
    part_of_group = np.empty(n_groups, dtype=np.int8)
    part_of_group[order[:n_train]] = 0
    part_of_group[order[n_train:n_train + n_val]] = 1
    part_of_group[order[n_train + n_val:]] = 2
    part = part_of_group[codes]
    return Split(*(np.flatnonzero(part == p) for p in range(3)), "group", seed,
                 {"fractions": list(fractions), "n_groups": int(n_groups)})


def content_groups(df: pd.DataFrame, feature_cols: list[str]) -> np.ndarray:
    """One group id per distinct feature vector, for duplicate-aware `group_split`.

    Rows with identical values on `feature_cols` get the same id, so a group split
    cannot place a vector on both sides. For all-numeric, NaN-free columns the id is
    the rank of the row among the sorted distinct rows: exact (no hashing) and
    independent of library versions. Otherwise a pandas row hash is used (a 64-bit
    collision could only merge groups, never separate identical rows). Recompute
    when the model input columns change: fewer columns can make more rows identical.
    """
    values = df[feature_cols]
    if all(pd.api.types.is_numeric_dtype(t) for t in values.dtypes):
        arr = values.to_numpy(dtype=np.float64) + 0.0   # + 0.0 turns -0.0 into 0.0
        if not np.isnan(arr).any():
            _, inverse = np.unique(arr, axis=0, return_inverse=True)
            return inverse.reshape(-1).astype(np.int64)
    hashed = pd.util.hash_pandas_object(values, index=False).to_numpy()
    return np.unique(hashed, return_inverse=True)[1].reshape(-1).astype(np.int64)


def conflicting_groups(groups, labels) -> np.ndarray:
    """Group ids whose rows carry more than one label (identical inputs, different targets)."""
    frame = pd.DataFrame({"g": np.asarray(groups), "y": np.asarray(labels)})
    n_labels = frame.groupby("g")["y"].nunique()
    return n_labels.index[n_labels > 1].to_numpy()


def partition_overlap(groups, split: Split) -> dict[str, int]:
    """For every partition pair, rows of the second partition whose group also occurs in the first.

    With content_groups this counts exact feature-vector duplicates across partitions;
    a duplicate-aware split must give 0 for all three pairs.
    """
    groups = np.asarray(groups)
    parts = split.parts()
    out = {}
    for a, b in (("train", "val"), ("train", "test"), ("val", "test")):
        out[f"{a}_{b}"] = int(np.isin(groups[parts[b]], groups[parts[a]]).sum())
    return out


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


def _record_digest(payload: dict) -> str:
    body = {k: v for k, v in payload.items() if k != "record_sha256"}
    return hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def save_split(split: Split, path: str | Path, source: dict) -> None:
    """Write indices plus provenance.

    `source` must identify the exact input, e.g. {"dataset": id, "files": {name: sha256},
    "n_rows": n}. The record digest covers every field (indices, seed, params, source),
    so an edited file is detected on load. This is integrity checking, not authenticity:
    anyone can recompute the digest after editing.
    """
    payload = {
        "strategy": split.strategy,
        "seed": split.seed,
        "params": split.params,
        "source": source,
        "fingerprint": split.fingerprint(),
        **{name: idx.tolist() for name, idx in split.parts().items()},
    }
    payload["record_sha256"] = _record_digest(payload)
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(payload), encoding="utf-8")


def load_split(path: str | Path, expected_source: dict | None = None, n_rows: int | None = None) -> Split:
    """Load a saved split, refusing edited records or a mismatched dataset.

    expected_source: every key given must equal the saved `source` value (e.g. the
        dataset id and file checksums of the data about to be used).
    n_rows: row count of the frame the indices will be applied to.
    """
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if payload.get("record_sha256") != _record_digest(payload):
        raise ValueError(f"split file {path} was modified after saving (record digest mismatch)")
    split = Split(
        *(np.asarray(payload[p], dtype=int) for p in PARTS),
        strategy=payload["strategy"], seed=payload["seed"], params=payload["params"],
        source=payload["source"],
    )
    if split.fingerprint() != payload["fingerprint"]:
        raise ValueError(f"split file {path} fails its fingerprint check")
    for key, want in (expected_source or {}).items():
        if payload["source"].get(key) != want:
            raise ValueError(f"split file {path} was made for {key}={payload['source'].get(key)!r}, expected {want!r}")
    if n_rows is not None:
        try:
            check_disjoint(split, n_rows)
        except AssertionError as e:
            raise ValueError(f"split file {path} does not fit a frame of {n_rows} rows: {e}") from e
    return split
