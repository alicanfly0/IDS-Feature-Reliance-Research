import json

import numpy as np
import pandas as pd
import pytest

from src.data.split import (
    check_disjoint, class_proportions, conflicting_groups, content_groups, cross_split_duplicates,
    exclude_eval_twins, group_overlap, group_split, partition_overlap,
    load_split, predefined_split, save_split, stratified_split, temporal_split,
)

LABELS = np.array(["A"] * 800 + ["B"] * 200)
GROUP_SPLIT_SEED42_FINGERPRINT = "3d93b9deb786e458"  # pinned 2026-11-08 (numpy legacy RandomState)


def test_stratified_is_deterministic_and_disjoint():
    s1 = stratified_split(LABELS, seed=7)
    s2 = stratified_split(LABELS, seed=7)
    s3 = stratified_split(LABELS, seed=8)
    assert s1.fingerprint() == s2.fingerprint()
    assert s1.fingerprint() != s3.fingerprint()
    check_disjoint(s1, len(LABELS))
    assert (len(s1.train), len(s1.val), len(s1.test)) == (700, 150, 150)


def test_stratified_preserves_class_ratio():
    props = class_proportions(LABELS, stratified_split(LABELS, seed=1))
    for part in props.values():
        assert part["B"] == pytest.approx(0.2, abs=0.01)


def test_group_split_keeps_groups_whole():
    groups = np.repeat(np.arange(100), 10)
    split = group_split(groups, seed=3)
    check_disjoint(split, len(groups))
    assert group_overlap(groups, split) == {"val": 0, "test": 0}


def test_random_split_leaks_groups_that_group_split_does_not():
    groups = np.repeat(np.arange(100), 10)
    labels = np.tile(["A"] * 8 + ["B"] * 2, 100)
    assert group_overlap(groups, stratified_split(labels, seed=3))["test"] > 0


def test_content_groups_keep_identical_vectors_on_one_side():
    rng = np.random.default_rng(0)
    base = pd.DataFrame({"a": rng.integers(0, 5, 300), "b": rng.integers(0, 3, 300)})  # many repeats
    df = base.assign(label=rng.integers(0, 2, 300))
    feats = ["a", "b"]
    groups = content_groups(df, feats)
    assert len(np.unique(groups)) == len(base.drop_duplicates())
    split = group_split(groups, seed=1)
    check_disjoint(split, len(df))
    assert cross_split_duplicates(df, split, feats) == {"val": 0, "test": 0}
    assert sum(cross_split_duplicates(df, stratified_split(df["label"], seed=1), feats).values()) > 0


def test_group_split_is_pinned_to_a_frozen_rng():
    # Regression pin: legacy RandomState permutations never change, so this split must not either.
    split = group_split(np.repeat(np.arange(20), 3), seed=42)
    assert split.fingerprint()[:16] == GROUP_SPLIT_SEED42_FINGERPRINT
    assert (len(split.train), len(split.val), len(split.test)) == (42, 9, 9)


def test_content_groups_are_exact_and_ignore_signed_zero():
    df = pd.DataFrame({"a": [0.0, -0.0, 1.0, 1.0, 2.0], "b": [5, 5, 6, 6, 7]})
    assert content_groups(df, ["a", "b"]).tolist() == [0, 0, 1, 1, 2]
    text = pd.DataFrame({"s": ["x", "y", "x"]})
    g = content_groups(text, ["s"])
    assert g[0] == g[2] != g[1]


def test_conflicting_groups_and_pairwise_overlap():
    groups = np.array([0, 0, 1, 1, 2, 3, 3, 4])
    labels = np.array([1, 1, 0, 1, 0, 0, 0, 1])
    assert conflicting_groups(groups, labels).tolist() == [1]
    split = predefined_split(["train", "train", "train", "val", "test", "val", "test", "test"])
    assert partition_overlap(groups, split) == {"train_val": 1, "train_test": 0, "val_test": 1}
    clean = group_split(groups, seed=0)
    assert partition_overlap(groups, clean) == {"train_val": 0, "train_test": 0, "val_test": 0}


def test_exclude_eval_twins_removes_only_evaluation_duplicates():
    groups = np.array([0, 1, 2, 3, 0, 4, 1, 5, 4, 6])
    split = predefined_split(["train", "train", "train", "train", "val", "val", "test", "test", "test", "test"])
    reduced, info = exclude_eval_twins(groups, split)
    assert reduced.train.tolist() == split.train.tolist()                       # training rows unchanged
    assert reduced.val.tolist() == [5] and info["val_excluded_positions"] == [4]   # val twin of train
    assert reduced.test.tolist() == [7, 9] and info["test_excluded_positions"] == [6, 8]  # twins of train / val
    assert partition_overlap(groups, reduced) == {"train_val": 0, "train_test": 0, "val_test": 0}
    assert reduced.params["base_fingerprint"] == split.fingerprint()


def test_temporal_split_orders_and_keeps_ties_together():
    times = np.repeat(np.arange(50), 4)[::-1]  # reversed order, 4 rows per timestamp
    split = temporal_split(times)
    check_disjoint(split, len(times))
    assert times[split.train].max() < times[split.val].min()
    assert times[split.val].max() < times[split.test].min()


def test_predefined_split_and_bad_labels():
    split = predefined_split(["train", "train", "test", "val"])
    assert split.train.tolist() == [0, 1] and split.test.tolist() == [2] and split.val.tolist() == [3]
    with pytest.raises(ValueError):
        predefined_split(["train", "holdout"])


def test_check_disjoint_catches_overlap_and_gaps():
    split = predefined_split(["train", "test", "val"])
    split.test = np.array([0, 1])
    with pytest.raises(AssertionError):
        check_disjoint(split, 3)
    split = predefined_split(["train", "test", "val"])
    with pytest.raises(AssertionError):
        check_disjoint(split, 4)


def test_cross_split_duplicates_detects_identical_vectors():
    df = pd.DataFrame({"x": [1, 2, 3, 1, 5, 2], "y": [0, 0, 0, 0, 0, 0]})
    split = predefined_split(["train", "train", "train", "test", "test", "val"])
    assert cross_split_duplicates(df, split, ["x", "y"]) == {"val": 1, "test": 1}


@pytest.mark.parametrize("fractions", [(0.5, 0.5, 0.5), (0.7, 0.3, 0.0), (0.0, 0.5, 0.5)])
def test_bad_fractions_rejected(fractions):
    with pytest.raises(ValueError):
        stratified_split(LABELS, fractions=fractions)


def test_save_load_roundtrip_and_tamper_detection(tmp_path):
    split = stratified_split(LABELS, seed=5)
    path = tmp_path / "split.json"
    save_split(split, path, source={"dataset": "toy"})
    assert load_split(path).fingerprint() == split.fingerprint()
    text = path.read_text().replace('"test": [', '"test": [0, ', 1)
    path.write_text(text)
    with pytest.raises(ValueError):
        load_split(path)


SOURCE = {"dataset": "toy", "files": {"toy.csv": "a" * 64}, "n_rows": 1000}


def _saved(tmp_path):
    path = tmp_path / "split.json"
    save_split(stratified_split(LABELS, seed=5), path, source=SOURCE)
    return path


@pytest.mark.parametrize("field,value", [("seed", 6), ("source", {**SOURCE, "files": {"toy.csv": "b" * 64}})])
def test_edited_provenance_is_detected(tmp_path, field, value):
    # Audit F2: edits to seed or source metadata used to load without complaint.
    path = _saved(tmp_path)
    payload = json.loads(path.read_text())
    payload[field] = value
    path.write_text(json.dumps(payload))
    with pytest.raises(ValueError, match="modified"):
        load_split(path)


def test_load_checks_expected_dataset_and_row_count(tmp_path):
    path = _saved(tmp_path)
    split = load_split(path, expected_source={"dataset": "toy", "files": SOURCE["files"]}, n_rows=1000)
    assert split.source == SOURCE and split.seed == 5
    with pytest.raises(ValueError, match="files"):
        load_split(path, expected_source={"files": {"toy.csv": "c" * 64}})
    with pytest.raises(ValueError, match="rows"):
        load_split(path, n_rows=1200)
