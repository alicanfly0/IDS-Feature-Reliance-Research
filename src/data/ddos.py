"""D-008 scope: CICIDS2017 Friday-afternoon DDoS file, prepared under D-011 and D-007 track B.

Every count is recomputed from the verified file and returned in a report; nothing
here assumes the numbers recorded in the decision log.
"""
from __future__ import annotations

import hashlib
import shutil
import zipfile
import zlib
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from src.data.acquire import check_file
from src.data.load import read_flow_csv
from src.data.manifest import ROOT, load_manifest
from src.data.preprocess import invalid_row_mask
from src.data.split import Split, conflicting_groups, content_groups, group_split, partition_overlap

DATASET_ID = "cicids2017_original"
ARCHIVE = "MachineLearningCSV.zip"
MEMBER = "MachineLearningCVE/Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv"
SENTINEL_COLS = ("Init_Win_bytes_forward", "Init_Win_bytes_backward")


@dataclass
class Prepared:
    frame: pd.DataFrame        # kept rows, all columns incl. Label; index = source row in the CSV
    y: np.ndarray              # 1 = positive class, 0 = negative class
    groups: np.ndarray         # content group per kept row (duplicate-aware split key)
    split: Split               # positional indices into `frame`
    feature_cols: list[str]
    report: dict


def _crc32(path: Path) -> int:
    crc = 0
    with open(path, "rb") as f:
        while chunk := f.read(1 << 20):
            crc = zlib.crc32(chunk, crc)
    return crc


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(1 << 20):
            digest.update(chunk)
    return digest.hexdigest()


def verified_csv(root: Path = ROOT, archive_entry: dict | None = None, member: str = MEMBER) -> tuple[Path, dict]:
    """Verify the archive (size, sha256, publisher MD5), extract only the requested member (default:
    the D-008 Friday DDoS file) if needed, and check the CSV against the archive's CRC.
    Returns (csv path, provenance)."""
    entry = archive_entry or {f["name"]: f for f in load_manifest()["datasets"][DATASET_ID]["files"]}[ARCHIVE]
    local_dir = root / load_manifest()["datasets"][DATASET_ID]["local_dir"]
    archive = local_dir / ARCHIVE
    problems = check_file(archive, entry)
    if problems:
        raise RuntimeError(f"{archive} failed verification: {problems}")
    csv = local_dir / "extracted" / member
    with zipfile.ZipFile(archive) as zf:
        info = zf.getinfo(member)
        if not csv.is_file():
            csv.parent.mkdir(parents=True, exist_ok=True)
            tmp = csv.with_name(csv.name + ".part")
            with zf.open(info) as src, open(tmp, "wb") as out:
                shutil.copyfileobj(src, out, 1 << 20)
            tmp.replace(csv)
    if _crc32(csv) != info.CRC:
        raise RuntimeError(f"{csv} does not match its archive member (CRC mismatch); delete it and re-run")
    return csv, {"archive": ARCHIVE, "archive_sha256": entry["sha256"], "member": member,
                 "member_crc32": f"{info.CRC:08x}", "csv_sha256": _sha256(csv)}


def prepare(df: pd.DataFrame, label_map: dict[str, int], fractions=(0.70, 0.15, 0.15), seed: int = 42,
            nonnegative_cols=("Flow Duration",), label_col: str = "Label") -> Prepared:
    """Apply the D-011 rules, exclude conflicting-label groups, and make the track-B split."""
    unknown = set(df[label_col].unique()) - set(label_map)
    if unknown:
        raise ValueError(f"labels not covered by label_map: {sorted(unknown)}")
    report = {"raw_rows": len(df), "raw_class_counts": df[label_col].value_counts().to_dict()}

    rules = invalid_row_mask(df, nonnegative_cols=tuple(nonnegative_cols))
    invalid = rules.any(axis=1).to_numpy()
    report["rule_rows"] = {k: int(v) for k, v in rules.sum().items()}
    report["invalid_rows"] = int(invalid.sum())
    report["invalid_class_counts"] = df.loc[invalid, label_col].value_counts().to_dict()
    report["invalid_source_rows"] = df.index[invalid].tolist()
    for col in SENTINEL_COLS:
        if col in df.columns:
            sentinel = (df[col] == -1).to_numpy()
            report[f"sentinel_minus1_{col}"] = {"total": int(sentinel.sum()), "kept": int((sentinel & ~invalid).sum())}

    kept = df.loc[~invalid]
    feature_cols = [c for c in kept.columns if c != label_col]
    groups = content_groups(kept, feature_cols)
    y = kept[label_col].map(label_map).to_numpy(dtype=np.int8)
    bad = conflicting_groups(groups, y)
    conflict = np.isin(groups, bad)
    report["conflicting_label_groups"] = int(len(bad))
    report["conflicting_label_rows_excluded"] = int(conflict.sum())
    kept, y, groups = kept.loc[~conflict], y[~conflict], groups[~conflict]

    split = group_split(groups, fractions=tuple(fractions), seed=seed)
    overlap = partition_overlap(groups, split)
    if any(overlap.values()):
        raise AssertionError(f"duplicate feature vectors cross partitions: {overlap}")
    report.update({
        "kept_rows": len(kept),
        "kept_class_counts": kept[label_col].value_counts().to_dict(),
        "n_features": len(feature_cols),
        "distinct_vectors": int(len(np.unique(groups))),
        "rows_in_duplicate_groups": int((pd.Series(groups).map(pd.Series(groups).value_counts()) > 1).sum()),
        "partition_rows": {p: len(i) for p, i in split.parts().items()},
        "partition_fraction": {p: round(len(i) / len(kept), 5) for p, i in split.parts().items()},
        "partition_positive": {p: int(y[i].sum()) for p, i in split.parts().items()},
        "partition_overlap": overlap,
    })
    return Prepared(kept, y, groups, split, feature_cols, report)


def subsample(prep: Prepared, sizes: dict[str, int], seed: int) -> Prepared:
    """Smoke runs only: keep a random subset of each partition (membership unchanged)."""
    rng = np.random.RandomState(seed)
    chosen = {p: np.sort(rng.choice(idx, size=min(sizes[p], len(idx)), replace=False)) for p, idx in prep.split.parts().items()}
    order = np.concatenate([chosen["train"], chosen["val"], chosen["test"]])
    n_tr, n_va = len(chosen["train"]), len(chosen["val"])
    split = Split(np.arange(n_tr), np.arange(n_tr, n_tr + n_va), np.arange(n_tr + n_va, len(order)),
                  "group_subsample", prep.split.seed, {**prep.split.params, "subsample": sizes})
    report = {**prep.report, "subsample": {p: len(v) for p, v in chosen.items()}}
    return Prepared(prep.frame.iloc[order], prep.y[order], prep.groups[order], split, prep.feature_cols, report)


def load(csv: Path) -> pd.DataFrame:
    df, _ = read_flow_csv(csv)
    return df
