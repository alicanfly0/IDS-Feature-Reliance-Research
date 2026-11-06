import numpy as np
import pandas as pd
import pytest

from src.data.split import (
    check_disjoint, class_proportions, cross_split_duplicates, group_overlap, group_split,
    load_split, predefined_split, save_split, stratified_split, temporal_split,
)

LABELS = np.array(["A"] * 800 + ["B"] * 200)


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
