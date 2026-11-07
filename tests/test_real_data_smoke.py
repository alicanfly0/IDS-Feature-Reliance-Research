"""End-to-end checks on real dataset files (audit F4; D-007/D-011 demonstration).

Each test runs only when its files are present and match the manifest; otherwise
it is skipped, so the suite still passes on a machine without data.
"""
import zipfile
import zlib

import numpy as np
import pandas as pd
import pytest

from src.config import ROOT, check_no_leaky_outputs, excluded_columns, load_config, make_preprocessor, write_run_record
from src.data.acquire import check_file
from src.data.load import read_flow_csv
from src.data.manifest import load_manifest
from src.data.preprocess import invalid_row_mask
from src.data.split import (
    check_disjoint, class_proportions, content_groups, cross_split_duplicates, group_split, load_split,
    predefined_split, save_split, stratified_split,
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

CIC = load_manifest()["datasets"]["cicids2017_original"]
CIC_DIR = ROOT / CIC["local_dir"]
DDOS_MEMBER = "MachineLearningCVE/Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv"
DDOS_CSV = CIC_DIR / "extracted" / DDOS_MEMBER
needs_ddos = pytest.mark.skipif(not DDOS_CSV.is_file(), reason="CICIDS2017 Friday DDoS file not extracted")


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
    """D-011 row rules and the D-007 track-B split on the D-008 scope (no training)."""
    zip_entry = {e["name"]: e for e in CIC["files"]}["MachineLearningCSV.zip"]
    zip_path = CIC_DIR / "MachineLearningCSV.zip"
    assert check_file(zip_path, zip_entry) == []          # archive = manifest sha256 + publisher MD5
    with zipfile.ZipFile(zip_path) as zf:
        want_crc = zf.getinfo(DDOS_MEMBER).CRC
    crc = 0
    with open(DDOS_CSV, "rb") as f:
        while chunk := f.read(1 << 20):
            crc = zlib.crc32(chunk, crc)
    assert crc == want_crc                                  # extracted file = archive member

    df, _ = read_flow_csv(DDOS_CSV)
    assert len(df) == 225745 and df.shape[1] == 79
    assert df["Label"].value_counts().to_dict() == {"DDoS": 128027, "BENIGN": 97718}

    # D-011: explicit rules, logged counts, original row positions kept as the index.
    rules = invalid_row_mask(df, nonnegative_cols=("Flow Duration",))
    assert {k: int(v) for k, v in rules.sum().items()} == {"missing": 4, "infinite": 34, "negative:Flow Duration": 2}
    invalid = rules.any(axis=1)
    assert df.loc[invalid, "Label"].value_counts().to_dict() == {"BENIGN": 34, "DDoS": 2}
    kept = df.loc[~invalid]
    assert kept["Label"].value_counts().to_dict() == {"DDoS": 128025, "BENIGN": 97684}
    assert kept.index.equals(df.index[~invalid])            # source positions preserved
    # The -1 window sentinel is not a rule: every forward -1 survives; the 25 backward -1
    # rows removed are removed by the missing/infinite/negative rules, not by the sentinel.
    assert (kept["Init_Win_bytes_forward"] == -1).sum() == (df["Init_Win_bytes_forward"] == -1).sum() == 32925
    sentinel_back = df["Init_Win_bytes_backward"] == -1
    assert (sentinel_back & ~invalid).sum() == 88274 and (sentinel_back & invalid).sum() == 25

    # D-007 track B: identical feature vectors share a group, so they cannot cross partitions.
    kept = kept.reset_index(names="source_row")
    feats = [c for c in kept.columns if c not in ("Label", "source_row")]
    assert len(feats) == 78
    groups = content_groups(kept, feats)
    assert len(np.unique(groups)) == 223080
    split = group_split(groups, seed=42)
    check_disjoint(split, len(kept))
    assert cross_split_duplicates(kept, split, feats) == {"val": 0, "test": 0}
    assert [len(split.train), len(split.val), len(split.test)] == [157994, 33819, 33896]
    shares = {k: v["1"] for k, v in class_proportions((kept["Label"] == "DDoS").astype(int).astype(str), split).items()}
    assert all(abs(s - 128025 / 225709) < 0.01 for s in shares.values())  # balance kept without stratifying

    # Contrast: a row-stratified random split of the same rows leaks identical vectors.
    random_split = stratified_split((kept["Label"] == "DDoS").astype(int), seed=42)
    assert cross_split_duplicates(kept, random_split, feats) == {"val": 498, "test": 486}
