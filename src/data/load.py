"""Read flow CSVs without silently altering them.

Known release quirks this handles (CICIDS2017 especially): whitespace around
column names, repeated column names, non-UTF-8 bytes in label strings, and
"Infinity" tokens. Every adjustment is reported in the returned notes; the
values themselves are not modified.
"""
from __future__ import annotations

import csv
from pathlib import Path

import pandas as pd

ENCODINGS = ("utf-8", "cp1252")


def _read_header(path: Path, encoding: str) -> list[str]:
    with open(path, encoding=encoding, newline="") as f:
        return next(csv.reader(f))


def read_flow_csv(path: str | Path, nrows: int | None = None, header: bool = True) -> tuple[pd.DataFrame, dict]:
    """Return (frame, notes). Column names are stripped; duplicates get a .N suffix."""
    path = Path(path)
    last_error = None
    for encoding in ENCODINGS:
        try:
            raw_header = _read_header(path, encoding) if header else None
            df = pd.read_csv(
                path,
                encoding=encoding,
                nrows=nrows,
                header=0 if header else None,
                low_memory=False,
            )
            break
        except UnicodeDecodeError as e:
            last_error = e
    else:
        raise last_error

    notes = {"path": str(path), "encoding": encoding, "nrows_limit": nrows}
    if header:
        stripped = [c.strip() for c in raw_header]
        notes["names_with_whitespace"] = [c for c in raw_header if c != c.strip()]
        seen: dict[str, int] = {}
        duplicated, names = [], []
        for name in stripped:
            if name in seen:
                seen[name] += 1
                duplicated.append(name)
                names.append(f"{name}.{seen[name]}")
            else:
                seen[name] = 0
                names.append(name)
        notes["duplicated_names"] = duplicated
        df.columns = names
    else:
        df.columns = [f"col_{i}" for i in range(df.shape[1])]
        notes["names_with_whitespace"] = []
        notes["duplicated_names"] = []
    return df, notes
