"""Download, verify and extract datasets listed in configs/datasets.yaml.

    python -m src.data.acquire download unsw_nb15     # or: all
    python -m src.data.acquire extract nf_unsw_nb15_v2
    python -m src.data.acquire verify all             # size + sha256 against the manifest

Only files with a `download` block in the manifest are fetched, and only from
the official source recorded there. Files whose source needs a manual step
(the CIC-IDS2017 registration form) are reported and skipped.
"""
from __future__ import annotations

import argparse
import hashlib
import http.cookiejar
import json
import shutil
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path, PurePosixPath

from src.data.manifest import ROOT, load_manifest, sha256_file

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) cnet-xai-audit"
UQ_RDM_API = "https://api.rdm.uq.edu.au/datasets/{uuid}/download"


def _opener(cookies: bool = False) -> urllib.request.OpenerDirector:
    handlers = [urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar())] if cookies else []
    opener = urllib.request.build_opener(*handlers)
    opener.addheaders = [("User-Agent", USER_AGENT)]
    return opener


def resolve_url(spec: dict, opener: urllib.request.OpenerDirector) -> str:
    """Turn a manifest `download` block into a fetchable URL (may prime cookies on `opener`)."""
    method = spec["method"]
    if method == "direct":
        return spec["url"]
    if method == "uq_rdm":
        with opener.open(UQ_RDM_API.format(uuid=spec["uuid"]), timeout=60) as r:
            return json.load(r)["url"]  # short-lived signed URL issued by UQ
    if method == "sharepoint_share":
        with opener.open(spec["share_url"], timeout=60) as r:
            r.read()  # sets the guest-access cookie
        site = spec["site"].rstrip("/")
        source = urllib.parse.quote(spec["source_path"])
        return f"{site}/_layouts/15/download.aspx?SourceUrl={source}"
    raise ValueError(f"unknown download method '{method}'")


def fetch(url: str, dest: Path, opener: urllib.request.OpenerDirector, chunk: int = 1 << 20) -> int:
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_name(dest.name + ".part")
    with opener.open(url, timeout=120) as r, open(tmp, "wb") as f:
        shutil.copyfileobj(r, f, chunk)
    tmp.replace(dest)
    return dest.stat().st_size


def check_file(path: Path, entry: dict) -> list[str]:
    """Problems with a local file versus its manifest entry (empty list = OK)."""
    if not path.is_file():
        return ["missing"]
    problems = []
    want_size = entry.get("size_bytes")
    if want_size is not None and path.stat().st_size != want_size:
        problems.append(f"size {path.stat().st_size} != manifest {want_size}")
    want_hash = entry.get("sha256")
    if want_hash and sha256_file(path) != want_hash:
        problems.append("sha256 mismatch")
    want_md5 = entry.get("publisher_md5")
    if want_md5 and _md5_file(path) != want_md5:
        problems.append("publisher md5 mismatch")
    return problems


def _md5_file(path: Path, chunk_size: int = 1 << 20) -> str:
    digest = hashlib.md5()
    with open(path, "rb") as f:
        while chunk := f.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def _windows_safe(part: str) -> str:
    # Windows drops trailing spaces/dots from names, so "TrafficLabelling /x.csv"
    # (CICIDS2017 GeneratedLabelledFlows.zip) cannot be created as-is.
    return part.rstrip(" .") or "_"


def safe_extract(zip_path: Path, dest: Path) -> dict[str, str]:
    """Extract a zip, refusing members that would land outside `dest`.

    Returns {written relative path: name inside the zip}; they differ only when
    a path part had to be made Windows-safe.
    """
    dest = dest.resolve()
    plan = []
    with zipfile.ZipFile(zip_path) as zf:
        for info in zf.infolist():
            name = PurePosixPath(info.filename.replace("\\", "/"))
            if name.is_absolute() or ".." in name.parts:
                raise ValueError(f"unsafe path in {zip_path.name}: {info.filename}")
            rel = PurePosixPath(*(_windows_safe(p) for p in name.parts)) if name.parts else PurePosixPath()
            target = (dest / Path(*rel.parts)).resolve()
            if not target.is_relative_to(dest):
                raise ValueError(f"unsafe path in {zip_path.name}: {info.filename}")
            plan.append((info, rel, target))
        written = {}
        for info, rel, target in plan:
            if info.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(info) as src, open(target, "wb") as out:
                shutil.copyfileobj(src, out, 1 << 20)
            written[str(rel)] = info.filename
        return written


def _selected(manifest: dict, target: str) -> dict:
    datasets = manifest["datasets"]
    if target == "all":
        return datasets
    if target not in datasets:
        raise SystemExit(f"unknown dataset '{target}'; choose from {sorted(datasets)} or 'all'")
    return {target: datasets[target]}


def cmd_download(manifest: dict, target: str, root: Path = ROOT, force: bool = False) -> int:
    failures = 0
    for ds_id, ds in _selected(manifest, target).items():
        for entry in ds.get("files") or []:
            spec = entry.get("download")
            if not spec:
                continue
            if spec["method"] == "manual":
                print(f"{ds_id}/{entry['name']}: manual download needed: {spec.get('instructions', '')}")
                continue
            dest = root / ds["local_dir"] / entry["name"]
            if not force and dest.is_file() and not check_file(dest, entry):
                print(f"{ds_id}/{entry['name']}: already present and verified")
                continue
            opener = _opener(cookies=spec["method"] == "sharepoint_share")
            print(f"{ds_id}/{entry['name']}: downloading ...", flush=True)
            fetch(resolve_url(spec, opener), dest, opener)
            problems = check_file(dest, entry)
            print(f"{ds_id}/{entry['name']}: {'OK' if not problems else '; '.join(problems)}")
            failures += bool(problems)
    return 1 if failures else 0


def cmd_extract(manifest: dict, target: str, root: Path = ROOT) -> int:
    for ds_id, ds in _selected(manifest, target).items():
        for entry in ds.get("files") or []:
            if not entry.get("extract_to"):
                continue
            zip_path = root / ds["local_dir"] / entry["name"]
            if not zip_path.is_file():
                print(f"{ds_id}/{entry['name']}: missing, download it first")
                continue
            dest = root / ds["local_dir"] / entry["extract_to"]
            members = safe_extract(zip_path, dest)
            print(f"{ds_id}/{entry['name']}: extracted {len(members)} files to {dest}")
            for written, original in members.items():
                note = f"   (zip name {original!r})" if written != original else ""
                print(f"    {written}{note}")
    return 0


def cmd_verify(manifest: dict, target: str, root: Path = ROOT) -> int:
    failures = 0
    for ds_id, ds in _selected(manifest, target).items():
        for entry in ds.get("files") or []:
            if not entry.get("name") or not (entry.get("download") or entry.get("sha256") or entry.get("publisher_md5")):
                continue
            path = root / ds["local_dir"] / entry["name"]
            problems = check_file(path, entry)
            print(f"{ds_id:<30} {entry['name']:<34} {'OK' if not problems else '; '.join(problems)}")
            failures += bool(problems)
    return 1 if failures else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command", choices=("download", "extract", "verify"))
    parser.add_argument("dataset", help="dataset id from configs/datasets.yaml, or 'all'")
    parser.add_argument("--force", action="store_true", help="re-download even if a verified copy exists")
    args = parser.parse_args(argv)
    manifest = load_manifest()
    if args.command == "download":
        return cmd_download(manifest, args.dataset, force=args.force)
    if args.command == "extract":
        return cmd_extract(manifest, args.dataset)
    return cmd_verify(manifest, args.dataset)


if __name__ == "__main__":
    raise SystemExit(main())
