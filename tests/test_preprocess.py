import numpy as np
import pandas as pd
import pytest

from src.data.preprocess import TrainOnlyPreprocessor, invalid_row_mask
from src.data.split import stratified_split

ID_COLS = ("Flow ID", "Source IP", "Timestamp", "Label")


def _fit(df):
    split = stratified_split(df["Label"], seed=0)
    train, test = df.iloc[split.train], df.iloc[split.test]
    pre = TrainOnlyPreprocessor(drop_cols=ID_COLS, categorical_cols=("proto",)).fit(train)
    return pre, train, test


def test_source_frame_is_not_mutated(toy_flows):
    before = toy_flows.copy()
    pre, train, test = _fit(toy_flows)
    pre.transform(test)
    pd.testing.assert_frame_equal(toy_flows, before)


def test_statistics_come_from_train_only(toy_flows):
    pre, train, test = _fit(toy_flows)
    clean = train["Flow Duration"]
    assert pre.mins_["Flow Duration"] == clean.min()
    assert pre.maxs_["Flow Duration"] == clean.max()
    finite = train["Flow Bytes/s"].replace([np.inf, -np.inf], np.nan)
    assert pre.medians_["Flow Bytes/s"] == finite.median()


def test_test_set_extremes_do_not_change_fit(toy_flows):
    pre, train, test = _fit(toy_flows)
    shifted = test.copy()
    shifted["Flow Duration"] = 1e9
    out = TrainOnlyPreprocessor(drop_cols=ID_COLS, categorical_cols=("proto",)).fit(train).transform(shifted)
    assert pre.maxs_["Flow Duration"] == train["Flow Duration"].max()
    assert (out["Flow Duration"] > 1).all()  # out-of-range stays visible unless clipping is chosen


def test_identifiers_and_train_constants_dropped(toy_flows):
    pre, train, test = _fit(toy_flows)
    out = pre.transform(test)
    for col in ID_COLS:
        assert col not in out.columns
    assert "Bwd URG Flags" in pre.constant_cols_
    assert "Bwd URG Flags" not in out.columns
    assert list(out.columns) == pre.output_columns


def test_no_missing_or_infinite_after_transform(toy_flows):
    pre, train, test = _fit(toy_flows)
    out = pre.transform(toy_flows)
    assert np.isfinite(out.to_numpy()).all()


def test_unseen_category_encodes_as_zeros(toy_flows):
    pre, train, test = _fit(toy_flows)
    unseen = test.head(3).copy()
    unseen["proto"] = "icmp"
    out = pre.transform(unseen)
    assert (out[["proto=tcp", "proto=udp"]] == 0).all().all()
    assert "proto=icmp" not in out.columns


def test_transform_before_fit_raises(toy_flows):
    with pytest.raises(RuntimeError):
        TrainOnlyPreprocessor().transform(toy_flows)


def test_missing_configured_column_raises(toy_flows):
    with pytest.raises(KeyError):
        TrainOnlyPreprocessor(drop_cols=("not_a_column",)).fit(toy_flows)


def test_invalid_row_mask_reports_without_dropping(toy_flows):
    mask = invalid_row_mask(toy_flows, nonnegative_cols=("Flow Duration",))
    assert len(mask) == len(toy_flows)
    assert mask.loc[3, "infinite"] and mask.loc[5, "missing"] and mask.loc[7, "negative:Flow Duration"]
    assert mask.any(axis=1).sum() == 3
