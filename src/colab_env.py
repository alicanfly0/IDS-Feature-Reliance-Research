"""Check (and, where safe, pin) the Colab environment against a frozen spec (Milestone 3B-1).

    python -m src.colab_env check   [--spec configs/environments/colab_env_v1.yaml] [--json OUT]
    python -m src.colab_env install [--spec ...] [--json OUT]

Exit codes: 0 = compatible; 3 = FATAL incompatibility that pip cannot fix (Python version, torch/CUDA
stack, GPU model, device, platform); 4 = pinned packages were (re)installed, so the runtime must be
restarted and the notebook run again; 2 = usage error. The checker never reinstalls torch or CUDA.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

import yaml

from src import env
from src.config import ROOT

DEFAULT_SPEC = ROOT / "configs/environments/colab_env_v1.yaml"


def load_spec(path: Path = DEFAULT_SPEC) -> dict:
    spec = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    for key in ("version", "python_major_minor", "platform", "device", "gpu_name", "torch", "pinned_packages"):
        if key not in spec:
            raise ValueError(f"environment spec missing '{key}'")
    if "torch" in spec["pinned_packages"]:
        raise ValueError("torch must never be a pip-pinned package (managed with Colab's CUDA stack)")
    return spec


def compare(snap: dict, spec: dict) -> dict:
    """Problems are split into `fatal` (pip cannot fix) and `pinnable` (exact pip version differs)."""
    fatal, pinnable = [], {}
    rel = env.result_relevant(snap)
    if rel["python"] != spec["python_major_minor"]:
        fatal.append(f"Python {rel['python']} != {spec['python_major_minor']} (pip cannot change Colab's Python)")
    if rel["platform"] != spec["platform"]:
        fatal.append(f"platform {rel['platform']} != {spec['platform']}")
    if rel["device"] != spec["device"]:
        fatal.append(f"device {rel['device']} != {spec['device']} (attach a GPU runtime)")
    if spec["device"] == "cuda" and rel["gpu_names"] != [spec["gpu_name"]]:
        fatal.append(f"GPU {rel['gpu_names']} != [{spec['gpu_name']}]")
    pkgs = snap.get("packages") or {}
    if pkgs.get("torch") != spec["torch"]["version"]:
        fatal.append(f"torch {pkgs.get('torch')} != {spec['torch']['version']} (never reinstalled automatically)")
    if spec["device"] == "cuda" and rel["torch_cuda_version"] != spec["torch"]["cuda_runtime"]:
        fatal.append(f"CUDA runtime {rel['torch_cuda_version']} != {spec['torch']['cuda_runtime']}")
    for name, version in spec["pinned_packages"].items():
        if pkgs.get(name) != str(version):
            pinnable[name] = {"found": pkgs.get(name), "required": str(version)}
    return {"compatible": not fatal and not pinnable, "fatal": fatal, "pinnable": pinnable,
            "spec_version": spec["version"], "result_relevant": rel, "fingerprint": env.fingerprint(snap)}


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("command", choices=("check", "install"))
    p.add_argument("--spec", type=Path, default=DEFAULT_SPEC)
    p.add_argument("--json", type=Path)
    a = p.parse_args(argv)
    spec = load_spec(a.spec)
    report = compare(env.snapshot(), spec)
    report["installed"] = []
    if a.command == "install" and not report["fatal"] and report["pinnable"]:
        wanted = [f"{n}=={v['required']}" for n, v in report["pinnable"].items()]
        r = subprocess.run([sys.executable, "-m", "pip", "install", "-q", "--no-deps", *wanted])
        if r.returncode != 0:
            report["fatal"].append(f"pip could not install {wanted}")
        else:
            report["installed"] = wanted
    if a.json:
        a.json.parent.mkdir(parents=True, exist_ok=True)
        a.json.write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8")
    if report["fatal"]:
        print("INCOMPATIBLE runtime (cannot be fixed by pip):\n  " + "\n  ".join(report["fatal"]), file=sys.stderr)
        return 3
    if report["installed"]:
        print("Pinned packages installed: " + ", ".join(report["installed"]) +
              "\nRESTART the runtime (Runtime -> Restart session), then run all cells again.", file=sys.stderr)
        return 4
    if report["pinnable"]:
        print("Package versions differ from the spec (run `install`): " + json.dumps(report["pinnable"]), file=sys.stderr)
        return 3
    print(f"environment compatible with spec v{spec['version']} (fingerprint {report['fingerprint'][:16]})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
