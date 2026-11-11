"""NetFlow-v2 networks for the two-network MES-DNN adaptation (D-010).

N1 = NF-UNSW-NB15-v2, all 2,390,275 flows. N2 = a FIXED, documented uniform random subsample of
NF-ToN-IoT-v2 (16,940,496 flows) of the same size as N1, drawn without replacement with
numpy default_rng(42). The 2.7 GB CSV is streamed from the verified zip (never extracted); its
publisher BagIt SHA-1 is checked during the same pass and the row count must equal the landing
page total, else nothing is written. Inputs: Wardana's 39 (the 43 NetFlow-v2 features minus the
4 IP/port identifiers, D-001); target: Label (0 benign, 1 attack).

  python -m src.data.netflow build-ton      # writes the cache and results/protocol/mesdnn/ton_subsample_v1.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

from src.data.acquire import check_file
from src.data.manifest import ROOT, load_manifest

UNSW, TON = "nf_unsw_nb15_v2", "nf_ton_iot_v2"
TON_TOTAL = 16_940_496
TON_MEMBER = "9bafce9d380588c2_MOHANAD_A4706/data/NF-ToN-IoT-v2.csv"
TON_SHA1 = "c0e014512c9a825146c52982d3cf12d3fce1ccc9"
SUBSAMPLE_SEED = 42
CACHE = ROOT / "data/processed/nf_ton_iot_v2_subsample_v1.pkl"
RECORD = ROOT / "results/protocol/mesdnn/ton_subsample_v1.json"


def inputs() -> list:
    return list(load_manifest()["datasets"][UNSW]["feature_schema"]["wardana_table2_inputs"])


def _verified_archive(dataset_id: str, root: Path = ROOT) -> Path:
    ds = load_manifest()["datasets"][dataset_id]
    entry = ds["files"][0]
    path = root / ds["local_dir"] / entry["name"]
    problems = check_file(path, entry)
    if problems:
        raise RuntimeError(f"{path.name} failed verification: {problems}")
    return path


def _read(fh, cols: list, **kw) -> pd.DataFrame:
    return pd.read_csv(fh, usecols=cols + ["Label", "Attack"], dtype={c: np.float64 for c in cols}, **kw)


def load_unsw(root: Path = ROOT) -> pd.DataFrame:
    archive = _verified_archive(UNSW, root)
    cols = inputs()
    with zipfile.ZipFile(archive) as zf:
        member = next(n for n in zf.namelist() if n.endswith("/data/NF-UNSW-NB15-v2.csv"))
        with zf.open(member) as fh:
            df = _read(fh, cols)
    if len(df) != load_manifest()["datasets"][UNSW]["records"]["total"]:
        raise RuntimeError("NF-UNSW-NB15-v2 row count differs from the manifest")
    return df


class _Sha1Reader:
    def __init__(self, fh):
        self.fh, self.h, self.n = fh, hashlib.sha1(), 0

    def read(self, size=-1):
        b = self.fh.read(size)
        self.h.update(b)
        self.n += len(b)
        return b

    def readable(self):
        return True

    def seekable(self):
        return False

    @property
    def closed(self):
        return self.fh.closed

    def readinto(self, b):
        data = self.read(len(b))
        b[:len(data)] = data
        return len(data)

    def __iter__(self):            # pandas may probe for iteration support
        return self

    def __next__(self):
        line = self.fh.readline()
        if not line:
            raise StopIteration
        self.h.update(line)
        self.n += len(line)
        return line


def build_ton(size: int | None = None, root: Path = ROOT, chunk: int = 1_000_000) -> dict:
    archive = _verified_archive(TON, root)
    size = size or load_manifest()["datasets"][UNSW]["records"]["total"]
    pick = np.sort(np.random.default_rng(SUBSAMPLE_SEED).choice(TON_TOTAL, size=size, replace=False))
    cols = inputs()
    parts, seen = [], 0
    with zipfile.ZipFile(archive) as zf, zf.open(TON_MEMBER) as raw:
        rd = _Sha1Reader(raw)
        for df in _read(rd, cols, chunksize=chunk):
            lo, hi = np.searchsorted(pick, [seen, seen + len(df)])
            parts.append(df.iloc[pick[lo:hi] - seen])
            seen += len(df)
        while rd.read(1 << 20):                       # hash any trailing bytes
            pass
    if rd.h.hexdigest() != TON_SHA1 or seen != TON_TOTAL:
        raise RuntimeError(f"NF-ToN-IoT-v2 CSV check failed: sha1 {rd.h.hexdigest()}, rows {seen}")
    sub = pd.concat(parts).reset_index(drop=False).rename(columns={"index": "source_row"})
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    sub.to_pickle(CACHE)
    rec = {"dataset": TON, "source_rows": seen, "csv_sha1_verified": TON_SHA1, "csv_bytes": rd.n,
           "subsample_size": int(len(sub)), "rng": f"numpy default_rng({SUBSAMPLE_SEED}).choice(replace=False)",
           "size_rule": "equal to the NF-UNSW-NB15-v2 total (N1)",
           "selected_rows_sha256": hashlib.sha256(pick.astype(np.int64).tobytes()).hexdigest(),
           "label_counts": {str(k): int(v) for k, v in sub["Label"].value_counts().sort_index().items()},
           "attack_counts": {str(k): int(v) for k, v in sub["Attack"].value_counts().items()},
           "cache_frame_sha256": frame_sha256(sub)}
    RECORD.parent.mkdir(parents=True, exist_ok=True)
    RECORD.write_text(json.dumps(rec, indent=2) + "\n", encoding="utf-8")
    return rec


def frame_sha256(df: pd.DataFrame) -> str:
    cols = inputs()
    h = hashlib.sha256(np.ascontiguousarray(df[cols].to_numpy(np.float64)).tobytes())
    h.update(df["Label"].to_numpy(np.int64).tobytes())
    return h.hexdigest()


def load_ton(root: Path = ROOT) -> pd.DataFrame:
    rec = json.loads(RECORD.read_text(encoding="utf-8"))
    if not CACHE.is_file():
        build_ton(rec["subsample_size"], root)
    df = pd.read_pickle(CACHE)
    if frame_sha256(df) != rec["cache_frame_sha256"]:
        raise RuntimeError("NF-ToN-IoT-v2 subsample cache does not match its frozen record")
    return df


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("command", choices=("build-ton",))
    p.parse_args(argv)
    rec = build_ton()
    print(json.dumps({k: rec[k] for k in ("subsample_size", "label_counts", "selected_rows_sha256")}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
