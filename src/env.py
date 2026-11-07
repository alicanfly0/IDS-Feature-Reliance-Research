"""Runtime environment: device selection, seeding and a provenance snapshot.

    python -m src.env                      # print the snapshot as JSON
    python -m src.env --json results/runs/<run>/environment.json

Works the same on Windows CPU and Linux/Colab CUDA. torch is optional: without
it the device is "cpu" and GPU facts come from nvidia-smi when present.
"""
from __future__ import annotations

import argparse
import importlib.metadata
import importlib.util
import json
import os
import platform
import random
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from src.data.manifest import ROOT, load_manifest

PACKAGES = ("numpy", "pandas", "scikit-learn", "PyYAML", "pytest", "torch", "xgboost", "lightgbm", "shap")


def _torch():
    return importlib.import_module("torch") if importlib.util.find_spec("torch") else None


def select_device(prefer: str = "auto") -> str:
    """"cuda" when requested/available, else "cpu". prefer="cuda" fails loudly if no GPU."""
    torch = _torch()
    has_cuda = bool(torch and torch.cuda.is_available())
    if prefer == "cpu":
        return "cpu"
    if prefer == "cuda":
        if not has_cuda:
            raise RuntimeError("CUDA requested but not available (no GPU runtime, or torch without CUDA)")
        return "cuda"
    if prefer != "auto":
        raise ValueError(f"prefer must be auto, cpu or cuda, not {prefer!r}")
    return "cuda" if has_cuda else "cpu"


def set_seeds(seed: int, deterministic: bool = True) -> dict:
    """Seed Python, NumPy and (if installed) torch; returns what was set, for the run record."""
    random.seed(seed)
    np.random.seed(seed)
    done = {"seed": seed, "python": True, "numpy": True, "torch": False}
    torch = _torch()
    if torch is not None:
        torch.manual_seed(seed)
        torch.cuda.manual_seed_all(seed)
        if deterministic:
            torch.backends.cudnn.deterministic = True
            torch.backends.cudnn.benchmark = False
        done["torch"] = True
        done["cudnn_deterministic"] = deterministic
    return done


def _run(cmd: list[str]) -> str | None:
    if not shutil.which(cmd[0]):
        return None
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=20, cwd=ROOT)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return out.stdout.strip() if out.returncode == 0 else None


def _total_ram_bytes() -> int | None:
    if sys.platform == "win32":
        import ctypes

        class MemStatus(ctypes.Structure):
            _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                        ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                        ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                        ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                        ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]
        status = MemStatus()
        status.dwLength = ctypes.sizeof(MemStatus)
        return int(status.ullTotalPhys) if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)) else None
    try:
        with open("/proc/meminfo", encoding="utf-8") as f:
            for line in f:
                if line.startswith("MemTotal:"):
                    return int(line.split()[1]) * 1024
    except OSError:
        pass
    return None


def _cpu_name() -> str:
    try:
        with open("/proc/cpuinfo", encoding="utf-8") as f:
            for line in f:
                if line.startswith("model name"):
                    return line.split(":", 1)[1].strip()
    except OSError:
        pass
    return platform.processor() or platform.machine()


def _gpu() -> dict:
    info: dict = {"torch_cuda_available": None, "devices": []}
    torch = _torch()
    if torch is not None:
        info["torch_cuda_available"] = torch.cuda.is_available()
        info["torch_cuda_version"] = torch.version.cuda
        for i in range(torch.cuda.device_count()):
            props = torch.cuda.get_device_properties(i)
            info["devices"].append({"name": props.name, "memory_bytes": props.total_memory})
    smi = _run(["nvidia-smi", "--query-gpu=name,memory.total,driver_version", "--format=csv,noheader"])
    info["nvidia_smi"] = smi.splitlines() if smi else None
    return info


def _git() -> dict:
    commit = _run(["git", "rev-parse", "HEAD"])
    status = _run(["git", "status", "--porcelain"])
    return {"commit": commit, "dirty": bool(status) if status is not None else None}


def in_colab() -> bool:
    if "COLAB_RELEASE_TAG" in os.environ or "google.colab" in sys.modules:
        return True
    try:
        return importlib.util.find_spec("google.colab") is not None
    except ModuleNotFoundError:  # no "google" package at all (e.g. Windows)
        return False


def dataset_hashes(dataset_id: str) -> dict:
    """Manifest sha256 of every file of a dataset, to identify the exact data a run used."""
    entry = load_manifest()["datasets"][dataset_id]
    return {f["name"]: f.get("sha256") for f in entry["files"]}


def snapshot(seed: int | None = None, dataset_id: str | None = None) -> dict:
    versions = {}
    for name in PACKAGES:
        try:
            versions[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            versions[name] = None
    return {
        "utc_time": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "python": platform.python_version(),
        "os": platform.platform(),  # includes the build; Windows 11 reports release "10" (build >= 22000)
        "machine": platform.machine(),
        "cpu": _cpu_name(),
        "cpu_count": os.cpu_count(),
        "ram_bytes": _total_ram_bytes(),
        "in_colab": in_colab(),
        "device": select_device("auto"),
        "gpu": _gpu(),
        "packages": versions,
        "git": _git(),
        "seed": seed,
        "dataset": {"id": dataset_id, "sha256": dataset_hashes(dataset_id)} if dataset_id else None,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--json", type=Path, help="also write the snapshot to this file")
    parser.add_argument("--dataset", help="manifest dataset id whose file hashes to include")
    args = parser.parse_args(argv)
    snap = snapshot(dataset_id=args.dataset)
    text = json.dumps(snap, indent=2)
    print(text)
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(text, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
