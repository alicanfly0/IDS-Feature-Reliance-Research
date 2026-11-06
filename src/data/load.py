"""Read flow CSVs without silently altering them.

Known release quirks this handles: whitespace around column names, repeated
column names, non-UTF-8 bytes in label strings and "Infinity" tokens
(CICIDS2017), a UTF-8 byte-order mark and header-less files whose names live
in a separate file (UNSW-NB15). Every adjustment is reported in the returned
notes; the values themselves are not modified.
"""
from __future__ import annotations

import codecs
import csv
from pathlib import Path

import pandas as pd

ENCODINGS = ("utf-8-sig", "cp1252")  # utf-8-sig also reads plain UTF-8 and drops a BOM


def _read_header(path: Path, encoding: str) -> list[str]:
    with open(path, encoding=encoding, newline="") as f:
        return next(csv.reader(f))


def read_names_file(path: str | Path, column: str = "Name") -> list[str]:
    """Column names listed one per row in a descriptor CSV (e.g. NUSW-NB15_features.csv)."""
    df, _ = read_flow_csv(path)
    return df[column].astype(str).tolist()


def read_flow_csv(
    path: str | Path,
    nrows: int | None = None,
    header: bool = True,
    names: list[str] | None = None,
) -> tuple[pd.DataFrame, dict]:
    """Return (frame, notes). Column names are stripped; duplicates get a .N suffix.

    For header-less files pass `header=False` and, if known, `names`.
    """
    path = Path(path)
    with open(path, "rb") as f:
        has_bom = f.read(3) == codecs.BOM_UTF8
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

    notes = {"path": str(path), "encoding": encoding, "utf8_bom": has_bom, "nrows_limit": nrows}
    if header:
        raw_names = raw_header
    elif names is not None:
        if len(names) != df.shape[1]:
            raise ValueError(f"{len(names)} names given for {df.shape[1]} columns in {path.name}")
        raw_names = list(names)
    else:
        raw_names = [f"col_{i}" for i in range(df.shape[1])]
    notes["names_source"] = "header" if header else ("names" if names is not None else "positional")

    notes["names_with_whitespace"] = [c for c in raw_names if c != c.strip()]
    seen: dict[str, int] = {}
    duplicated, final = [], []
    for name in (c.strip() for c in raw_names):
        if name in seen:
            seen[name] += 1
            duplicated.append(name)
            final.append(f"{name}.{seen[name]}")
        else:
            seen[name] = 0
            final.append(name)
    notes["duplicated_names"] = duplicated
    df.columns = final
    return df, notes
