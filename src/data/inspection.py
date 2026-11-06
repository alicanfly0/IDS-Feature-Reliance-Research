"""Inspect a flow dataset before any modelling decision is made.

    python -m src.data.inspection data/raw/unsw_nb15/UNSW_NB15_training-set.csv --label label
    python -m src.data.inspection data/raw/cicids2017_original/ --label Label --nrows 200000

Reports schema, shape, label counts, missing and infinite values, negative
values, duplicates, feature types and candidate leakage fields. Leakage flags
are heuristics to review by hand, not conclusions.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from src.data.load import read_flow_csv, read_names_file

# Name patterns for fields that identify hosts, sessions or capture time.
IDENTIFIER_PATTERNS = {
    "flow_id": r"^flow[ _]?id$",
    # Whole-name matches only: MIN_IP_PKT_LEN etc. are features, not addresses.
    "ip_address": r"^((src|dst|source|destination)[ _]?)?ip$|^ipv4_(src|dst)_addr$|^(srcip|dstip)$",
    "port": r"port$|^(sport|dsport)$|^l4_(src|dst)_port$",
    "timestamp": r"timestamp|^(stime|ltime)$|^date$",
    "row_id": r"^(id|no\.?|index|unnamed: 0)$",
}
# Columns that carry the answer in another form (e.g. attack_cat next to label).
LABEL_LIKE = r"^(label|class|attack|attack_cat|attack_type|category|target)$"

NEAR_UNIQUE_RATIO = 0.95       # nunique / rows above this looks like a row identifier
SEPARATOR_MAX_CARD_RATIO = 0.01  # only test low-cardinality columns as label separators
SEPARATOR_PURITY = 0.99


def _match(name: str, pattern: str) -> bool:
    return re.search(pattern, name.strip().lower()) is not None


def feature_types(df: pd.DataFrame) -> dict[str, str]:
    out = {}
    for col in df.columns:
        s = df[col]
        if pd.api.types.is_bool_dtype(s):
            out[col] = "bool"
        elif pd.api.types.is_numeric_dtype(s):
            out[col] = "integer" if pd.api.types.is_integer_dtype(s) else "float"
        else:
            converted = pd.to_numeric(s.dropna(), errors="coerce")
            if len(converted) and converted.notna().mean() > 0.99:
                out[col] = "numeric_stored_as_text"
            else:
                out[col] = "categorical"
    return out


def label_purity(values: pd.Series, labels: pd.Series) -> float:
    """Accuracy of predicting the label from this column alone (majority per value)."""
    table = pd.crosstab(values.fillna("<NA>"), labels.fillna("<NA>"))
    return float(table.max(axis=1).sum() / table.to_numpy().sum())


def leakage_candidates(df: pd.DataFrame, label_col: str | None) -> list[dict]:
    flags = []
    n = len(df)
    for col in df.columns:
        if col == label_col:
            continue
        for kind, pattern in IDENTIFIER_PATTERNS.items():
            if _match(col, pattern):
                flags.append({"column": col, "reason": f"name matches {kind}"})
        if _match(col, LABEL_LIKE):
            flags.append({"column": col, "reason": "label-like column besides the target"})
        nunique = df[col].nunique(dropna=False)
        if nunique <= 1:
            flags.append({"column": col, "reason": "constant column"})
            continue
        if n and nunique / n > NEAR_UNIQUE_RATIO:
            flags.append({"column": col, "reason": f"near-unique values ({nunique}/{n})"})
        if label_col and n and nunique / n <= SEPARATOR_MAX_CARD_RATIO:
            purity = label_purity(df[col], df[label_col])
            majority = df[label_col].value_counts(normalize=True, dropna=False).iloc[0]
            if purity >= SEPARATOR_PURITY and purity > majority:
                flags.append({
                    "column": col,
                    "reason": f"single-column label separator (purity {purity:.4f} vs majority {majority:.4f})",
                })
    return flags


def inspect_frame(df: pd.DataFrame, label_col: str | None = None) -> dict:
    if label_col is not None and label_col not in df.columns:
        raise KeyError(f"label column '{label_col}' not in columns")
    numeric = df.select_dtypes(include="number")
    label_cols = [c for c in df.columns if c == label_col or _match(c, LABEL_LIKE)]
    feature_cols = [c for c in df.columns if c not in label_cols]

    missing = df.isna().sum()
    infinite = pd.Series(np.isinf(numeric.to_numpy()).sum(axis=0), index=numeric.columns)
    negative = (numeric < 0).sum()

    id_cols = [c for c in feature_cols if any(_match(c, p) for p in IDENTIFIER_PATTERNS.values())]
    content_cols = [c for c in feature_cols if c not in id_cols]

    report = {
        "shape": list(df.shape),
        "columns": list(df.columns),
        "dtypes": {c: str(t) for c, t in df.dtypes.items()},
        "feature_types": feature_types(df),
        "label_column": label_col,
        "label_counts": (
            {str(k): int(v) for k, v in df[label_col].value_counts(dropna=False).items()}
            if label_col else None
        ),
        "label_like_counts": {
            c: {str(k): int(v) for k, v in df[c].value_counts(dropna=False).items()}
            for c in label_cols if c != label_col
        },
        "missing": {c: int(v) for c, v in missing.items() if v},
        "infinite": {c: int(v) for c, v in infinite.items() if v},
        "negative": {c: int(v) for c, v in negative.items() if v},
        "duplicate_rows": int(df.duplicated().sum()),
        "duplicate_feature_rows": int(df.duplicated(subset=feature_cols).sum()) if feature_cols else 0,
        "identifier_columns": id_cols,
        "duplicate_content_rows": int(df.duplicated(subset=content_cols).sum()) if content_cols else 0,
        "conflicting_label_duplicates": 0,
        "leakage_candidates": leakage_candidates(df, label_col),
    }
    if label_col and content_cols:
        # Identical flow contents (identifiers and labels ignored) that carry different labels.
        dup = df[df.duplicated(subset=content_cols, keep=False)]
        if len(dup):
            n_labels = dup.groupby(content_cols, dropna=False)[label_col].nunique(dropna=False)
            report["conflicting_label_duplicates"] = int((n_labels > 1).sum())
    return report


def format_report(report: dict, notes: dict | None = None) -> str:
    lines = []
    if notes:
        lines.append(f"file: {notes['path']}  (encoding {notes['encoding']}, nrows limit {notes['nrows_limit']})")
        lines.append(f"column names from: {notes['names_source']}" + ("; UTF-8 BOM present" if notes["utf8_bom"] else ""))
        if notes["names_with_whitespace"]:
            lines.append(f"column names stripped of whitespace: {len(notes['names_with_whitespace'])}")
        if notes["duplicated_names"]:
            lines.append(f"duplicated column names (renamed .N): {notes['duplicated_names']}")
    rows, cols = report["shape"]
    lines.append(f"shape: {rows} rows x {cols} columns")
    lines.append("\nschema (column: dtype / inferred type)")
    for c in report["columns"]:
        lines.append(f"  {c}: {report['dtypes'][c]} / {report['feature_types'][c]}")
    if report["label_counts"] is not None:
        lines.append(f"\nlabel counts ({report['label_column']})")
        for k, v in report["label_counts"].items():
            lines.append(f"  {k}: {v} ({v / rows:.4%})")
    for col, counts in report["label_like_counts"].items():
        lines.append(f"\nclass counts ({col})")
        for k, v in counts.items():
            lines.append(f"  {k}: {v} ({v / rows:.4%})")
    for key in ("missing", "infinite", "negative"):
        lines.append(f"\n{key} values: {sum(report[key].values())} in {len(report[key])} columns")
        for c, v in report[key].items():
            lines.append(f"  {c}: {v}")
    lines.append(f"\nduplicate rows (all columns): {report['duplicate_rows']}")
    lines.append(f"duplicate feature vectors (label columns excluded): {report['duplicate_feature_rows']}")
    lines.append(f"duplicate flow contents (labels and identifiers {report['identifier_columns']} excluded): "
                 f"{report['duplicate_content_rows']}")
    lines.append(f"flow contents with conflicting labels: {report['conflicting_label_duplicates']}")
    lines.append("\ncandidate leakage fields (heuristic, review manually)")
    for flag in report["leakage_candidates"]:
        lines.append(f"  {flag['column']}: {flag['reason']}")
    if not report["leakage_candidates"]:
        lines.append("  none flagged")
    return "\n".join(lines)


def _csv_paths(target: Path) -> list[Path]:
    return sorted(target.glob("*.csv")) if target.is_dir() else [target]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("path", type=Path, help="CSV file or directory of CSVs (concatenated)")
    parser.add_argument("--label", help="target label column")
    parser.add_argument("--nrows", type=int, help="read only the first N rows of each file")
    parser.add_argument("--no-header", action="store_true", help="file has no header row (e.g. UNSW-NB15_1..4.csv)")
    parser.add_argument("--names-from", type=Path,
                        help="descriptor CSV with a 'Name' column giving column names (implies --no-header)")
    parser.add_argument("--json", type=Path, help="also write the report as JSON")
    args = parser.parse_args(argv)
    # CICIDS2017 labels contain U+FFFD; a cp1252 console cannot print it.
    sys.stdout.reconfigure(errors="backslashreplace")

    names = read_names_file(args.names_from) if args.names_from else None
    header = not (args.no_header or names)
    frames, all_notes = [], []
    for path in _csv_paths(args.path):
        df, notes = read_flow_csv(path, nrows=args.nrows, header=header, names=names)
        frames.append(df)
        all_notes.append(notes)
    if not frames:
        parser.error(f"no CSV files found at {args.path}")
    columns = {tuple(f.columns) for f in frames}
    if len(columns) > 1:
        print("WARNING: files have different column sets; concatenation will introduce NaNs")
    df = pd.concat(frames, ignore_index=True)

    report = inspect_frame(df, args.label)
    report["files"] = all_notes
    for notes in all_notes[1:]:
        print(f"also read: {notes['path']} (encoding {notes['encoding']})")
    print(format_report(report, all_notes[0]))
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
