"""R4a-ii data: Engelen WTMC2021 corrected Friday flows in the original DDoS recording window (D-004, D-005).

Returns a frame with the 78 ORIGINAL MachineLearningCVE feature names (column map v1) plus `Label`,
so the registry, groups and preprocessing apply unchanged. Steps, all fail-closed:
  1. dataset.zip verified against the manifest (size, sha256); only Friday-WorkingHours.csv is used,
     extracted if needed and checked against its archive CRC.
  2. Clock alignment re-validated ON THE DATA before use: the first and last DDoS minute must sit
     exactly +5:00 after the original file's (15:56 / 16:16). The offset is an empirically supported
     assumption (D-005), not a confirmed time-zone correction.
  3. Rows restricted to the aligned original window [15:30, 17:03) and to labels DDoS / BENIGN.
  4. Columns renamed by configs/protocol/r4a_column_map_v1.yaml; `Fwd Header Length.1` <- `Fwd Header
     Length` (documented duplicate). Definitions differ for at least 16 inputs (readiness doc §4).
"""
from __future__ import annotations

import shutil
import zipfile
from pathlib import Path

import pandas as pd
import yaml

from src.data.acquire import check_file
from src.data.ddos import _crc32, _sha256
from src.data.load import read_flow_csv
from src.data.manifest import ROOT, load_manifest

DATASET_ID = "cicids2017_engelen_wtmc2021"
ARCHIVE = "dataset.zip"
MEMBER = "Friday-WorkingHours.csv"
MAP_FILE = "configs/protocol/r4a_column_map_v1.yaml"
OFFSET = pd.Timedelta(hours=5)
ORIGINAL_DDOS_FIRST, ORIGINAL_DDOS_LAST = pd.Timestamp("2017-07-07 15:56"), pd.Timestamp("2017-07-07 16:16")
WINDOW = (pd.Timestamp("2017-07-07 15:30"), pd.Timestamp("2017-07-07 17:03"))


def verified_csv(root: Path = ROOT) -> tuple[Path, dict]:
    entry = {f["name"]: f for f in load_manifest()["datasets"][DATASET_ID]["files"]}[ARCHIVE]
    local = root / load_manifest()["datasets"][DATASET_ID]["local_dir"]
    archive = local / ARCHIVE
    problems = check_file(archive, entry)
    if problems:
        raise RuntimeError(f"{archive.name} failed verification: {problems}")
    csv = local / "extracted" / MEMBER
    with zipfile.ZipFile(archive) as zf:
        info = zf.getinfo(MEMBER)
        if not csv.is_file():
            csv.parent.mkdir(parents=True, exist_ok=True)
            tmp = csv.with_name(csv.name + ".part")
            with zf.open(info) as src, open(tmp, "wb") as out:
                shutil.copyfileobj(src, out, 1 << 20)
            tmp.replace(csv)
    if _crc32(csv) != info.CRC:
        raise RuntimeError(f"{csv.name} does not match its archive member (CRC mismatch)")
    return csv, {"archive": ARCHIVE, "archive_sha256": entry["sha256"], "member": MEMBER,
                 "member_crc32": f"{info.CRC:08x}", "csv_sha256": _sha256(csv)}


def window_frame(raw: pd.DataFrame, column_map: dict) -> tuple[pd.DataFrame, dict]:
    """Validate the alignment, select the window and labels, map columns. Pure function (testable)."""
    label = raw["Label"].astype(str).str.strip()
    t = pd.to_datetime(raw["Timestamp"], format="%m/%d/%Y %I:%M:%S %p", errors="coerce")
    if t.isna().any():
        raise RuntimeError(f"{int(t.isna().sum())} unparseable timestamps")
    ddos = t[label == "DDoS"]
    first, last = ddos.min().floor("min") - OFFSET, ddos.max().floor("min") - OFFSET
    if (first, last) != (ORIGINAL_DDOS_FIRST, ORIGINAL_DDOS_LAST):
        raise RuntimeError(f"alignment check failed: corrected DDoS spans {first}..{last} after -5:00, "
                           f"expected {ORIGINAL_DDOS_FIRST}..{ORIGINAL_DDOS_LAST}")
    aligned = t - OFFSET
    keep = (aligned >= WINDOW[0]) & (aligned < WINDOW[1]) & label.isin(["DDoS", "BENIGN"])
    sub = raw.loc[keep]
    out = pd.DataFrame({orig: pd.to_numeric(sub[eng], errors="coerce") for orig, eng in column_map.items()},
                       index=sub.index)
    out["Label"] = label[keep].to_numpy()
    info = {"offset": "+05:00 (empirical assumption, D-005)", "window_original_clock": [str(WINDOW[0]), str(WINDOW[1])],
            "alignment_validated": True, "rows_in_file": int(len(raw)), "rows_kept": int(keep.sum()),
            "labels_kept": out["Label"].value_counts().to_dict(),
            "labels_outside_scope_in_window": label[((aligned >= WINDOW[0]) & (aligned < WINDOW[1])) & ~label.isin(["DDoS", "BENIGN"])].value_counts().to_dict()}
    return out, info


def load(root: Path = ROOT) -> tuple[pd.DataFrame, dict]:
    csv, provenance = verified_csv(root)
    raw, _ = read_flow_csv(csv)
    column_map = yaml.safe_load((root / MAP_FILE).read_text(encoding="utf-8"))["mapping"]
    frame, info = window_frame(raw, column_map)
    return frame, {**provenance, "column_map": MAP_FILE, **{f"window_{k}": v for k, v in info.items()}}
