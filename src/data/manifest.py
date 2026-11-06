"""Load and check configs/datasets.yaml against what is on disk.

    python -m src.data.manifest            # validate manifest, list local status
    python -m src.data.manifest --hash     # also print sha256 of local files

Nothing here downloads data.
"""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = ROOT / "configs" / "datasets.yaml"

REQUIRED_KEYS = (
    "name", "status", "local_dir", "official_source", "files", "license",
    "citation", "feature_schema", "labeling", "split_policy", "intended_experiments",
)
VALID_STATUS = {"not_acquired", "downloaded", "verified"}


def load_manifest(path: Path = MANIFEST_PATH) -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def validate_manifest(manifest: dict) -> list[str]:
    """Return a list of problems; empty means the manifest is well formed."""
    problems = []
    datasets = manifest.get("datasets") or {}
    if not datasets:
        problems.append("manifest has no datasets")
    for ds_id, entry in datasets.items():
        for key in REQUIRED_KEYS:
            if key not in entry:
                problems.append(f"{ds_id}: missing '{key}'")
        if entry.get("status") not in VALID_STATUS:
            problems.append(f"{ds_id}: status must be one of {sorted(VALID_STATUS)}")
        source = entry.get("official_source") or {}
        for key in ("landing_page", "download"):
            if not source.get(key):
                problems.append(f"{ds_id}: official_source.{key} is empty")
        if entry.get("status") == "verified":
            for f in entry.get("files") or []:
                if not f.get("sha256"):
                    problems.append(f"{ds_id}: status 'verified' but {f.get('name')} has no sha256")
    return problems


def sha256_file(path: Path, chunk_size: int = 1 << 20) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def local_status(manifest: dict, root: Path = ROOT, compute_hash: bool = False) -> list[dict]:
    """One row per manifest file: present?, recorded vs actual sha256."""
    rows = []
    for ds_id, entry in manifest["datasets"].items():
        local_dir = root / entry["local_dir"]
        for f in entry.get("files") or []:
            name = f.get("name")
            path = local_dir / name if name else None
            present = bool(path and path.is_file())
            actual = sha256_file(path) if (present and compute_hash) else None
            expected = f.get("sha256")
            rows.append({
                "dataset": ds_id,
                "file": name,
                "present": present,
                "sha256_expected": expected,
                "sha256_actual": actual,
                "sha256_match": (actual == expected) if (actual and expected) else None,
            })
    return rows


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--manifest", type=Path, default=MANIFEST_PATH)
    parser.add_argument("--hash", action="store_true", help="compute sha256 of files that are present")
    args = parser.parse_args(argv)

    manifest = load_manifest(args.manifest)
    problems = validate_manifest(manifest)
    for p in problems:
        print(f"MANIFEST PROBLEM: {p}")

    for row in local_status(manifest, compute_hash=args.hash):
        state = "present" if row["present"] else "missing"
        line = f"{row['dataset']:<32} {str(row['file']):<34} {state}"
        if row["sha256_actual"]:
            line += f"  sha256={row['sha256_actual']}"
            if row["sha256_match"] is False:
                line += "  MISMATCH"
        print(line)
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
