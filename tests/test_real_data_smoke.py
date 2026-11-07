"""End-to-end checks on real dataset files (audit F4; D-007/D-011 demonstration).

Each test runs only when its files are present and match the manifest; otherwise
it is skipped, so the suite still passes on a machine without data.
"""
import numpy as np
import pandas as pd
import pytest

from src.config import ROOT, check_no_leaky_outputs, excluded_columns, load_config, make_preprocessor, write_run_record
from src.data import ddos
from src.data.acquire import check_file
from src.data.load import read_flow_csv
from src.data.manifest import load_manifest
from src.data.split import (
    check_disjoint, cross_split_duplicates, load_split, predefined_split, save_split, stratified_split,
)

CONFIG = ROOT / "configs" / "experiments" / "smoke_unsw_official.yaml"
CFG = load_config(CONFIG)
EXP = CFG["experiment"]
DATASET = load_manifest()["datasets"][EXP["dataset"]]
DATA_DIR = ROOT / DATASET["local_dir"]
ENTRIES = {e["name"]: e for e in DATASET["files"]}
FILES = {part: DATA_DIR / name for part, name in EXP["files"].items()}

needs_unsw = pytest.mark.skipif(
    not all(p.is_file() for p in FILES.values()), reason=f"{EXP['dataset']} files not downloaded"
)

# Measured 2026-11-07 (results/inspection/unsw_train.json, unsw_test.json); fixed by the checksums.
EXPECTED_ROWS = {"train": 175341, "test": 82332}
EXPECTED_TEST_ROWS_WITH_TRAIN_TWIN = 8541

CIC_DIR = ROOT / load_manifest()["datasets"][ddos.DATASET_ID]["local_dir"]
DDOS_CSV = CIC_DIR / "extracted" / ddos.MEMBER
needs_ddos = pytest.mark.skipif(not (CIC_DIR / ddos.ARCHIVE).is_file(), reason="CICIDS2017 MachineLearningCSV.zip not downloaded")
TRACK_B = load_config(ROOT / "configs" / "experiments" / "ae_xgb_d008_trackB.yaml")


@needs_unsw
def test_unsw_official_partition_end_to_end(tmp_path):
    for name in EXP["files"].values():
        assert check_file(DATA_DIR / name, ENTRIES[name]) == [], f"{name} differs from the manifest"

    parts = {part: read_flow_csv(path)[0] for part, path in FILES.items()}
    assert {p: len(f) for p, f in parts.items()} == EXPECTED_ROWS
    df = pd.concat([parts["train"], parts["test"]], ignore_index=True)
    before = df.copy()

    split = predefined_split(["train"] * len(parts["train"]) + ["test"] * len(parts["test"]))
    check_disjoint(split, len(df))
    source = {
        "dataset": EXP["dataset"],
        "files": {name: ENTRIES[name]["sha256"] for name in EXP["files"].values()},
        "n_rows": len(df),
    }
    save_split(split, tmp_path / "split.json", source=source)
    assert load_split(tmp_path / "split.json", expected_source=source, n_rows=len(df)).fingerprint() == split.fingerprint()

    features = [c for c in df.columns if c not in excluded_columns(CFG)]
    dup = cross_split_duplicates(df, split, features)
    assert dup["test"] == EXPECTED_TEST_ROWS_WITH_TRAIN_TWIN

    pre = make_preprocessor(CFG)
    x_train = pre.fit_transform(df.iloc[split.train])
    x_test = pre.transform(df.iloc[split.test])

    pd.testing.assert_frame_equal(df, before)                     # source records untouched
    assert pre.n_fit_rows_ == EXPECTED_ROWS["train"]               # fitted on train only
    assert list(x_train.columns) == list(x_test.columns) == pre.output_columns
    check_no_leaky_outputs(pre.output_columns, CFG)
    assert np.isfinite(x_train.to_numpy()).all() and np.isfinite(x_test.to_numpy()).all()
    num = x_train[pre.numeric_cols_]
    assert num.min().min() >= 0.0 and num.max().max() <= 1.0     # train scaled by its own min/max

    record = write_run_record(CFG, tmp_path / "run", extra={
        "split_fingerprint": split.fingerprint(),
        "split_source": source,
        "test_rows_with_train_twin": dup["test"],
        "preprocessor": pre.state(),
        "shapes": {"train": list(x_train.shape), "test": list(x_test.shape)},
    })
    assert record.is_file()


@needs_ddos
def test_friday_ddos_row_rules_and_duplicate_aware_split():
    """D-011 rules and the D-007 track-B split on the D-008 scope, via the module the runner uses."""
    csv, provenance = ddos.verified_csv()                   # archive sha256 + MD5, member CRC
    assert csv == DDOS_CSV and provenance["archive_sha256"].startswith("c3f26274")
    df = ddos.load(csv)
    assert len(df) == 225745 and df.shape[1] == 79
    assert df["Label"].value_counts().to_dict() == {"DDoS": 128027, "BENIGN": 97718}

    prep = ddos.prepare(df, TRACK_B["data"]["label_map"], tuple(TRACK_B["experiment"]["split"]["fractions"]),
                        TRACK_B["experiment"]["split"]["seed"], tuple(TRACK_B["data"]["nonnegative_cols"]))
    r = prep.report
    assert r["rule_rows"] == {"missing": 4, "infinite": 34, "negative:Flow Duration": 2}
    assert r["invalid_rows"] == 36 and r["invalid_class_counts"] == {"BENIGN": 34, "DDoS": 2}
    assert r["kept_rows"] == 225709 and r["kept_class_counts"] == {"DDoS": 128025, "BENIGN": 97684}
    assert prep.frame.index.equals(df.index[~df.index.isin(r["invalid_source_rows"])])   # source rows kept
    # The -1 window sentinel is not a rule: all forward -1 survive; the 25 backward -1 rows that go
    # are removed by the missing/infinite/negative rules, not by the sentinel.
    assert r["sentinel_minus1_Init_Win_bytes_forward"] == {"total": 32925, "kept": 32925}
    assert r["sentinel_minus1_Init_Win_bytes_backward"] == {"total": 88299, "kept": 88274}
    assert r["conflicting_label_groups"] == 0
    assert r["n_features"] == 78 and r["distinct_vectors"] == 223080

    # Track B: zero shared feature vectors for every partition pair; fixed, pinned split.
    assert r["partition_overlap"] == {"train_val": 0, "train_test": 0, "val_test": 0}
    assert r["partition_rows"] == {"train": 157998, "val": 33834, "test": 33877}
    assert r["partition_positive"] == {"train": 89577, "val": 19215, "test": 19233}
    assert prep.split.fingerprint() == TRACK_B["experiment"]["split"]["expected_fingerprint"]
    feats = prep.feature_cols
    assert all(abs(r["partition_positive"][p] / r["partition_rows"][p] - 128025 / 225709) < 0.01 for p in r["partition_rows"])

    # Contrast: a row-stratified random split of the same rows leaks identical vectors.
    random_split = stratified_split(prep.y, seed=42)
    assert sum(cross_split_duplicates(prep.frame.reset_index(drop=True), random_split, feats).values()) > 900
