"""Generate notebooks/colab_runner.ipynb (thin launcher; all science lives in src/)."""
import json
import sys
from pathlib import Path


def md(text):
    return {"cell_type": "markdown", "metadata": {}, "source": text.strip("\n").splitlines(keepends=True)}


def code(text):
    return {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [],
            "source": text.strip("\n").splitlines(keepends=True)}


cells = [
    md("""
# CNET Phase III — Colab runner: AE-XGBoost, D-008 scope, track B

Thin launcher: every scientific step is a module in the repository (`src/`), tested locally first.
Plan and rationale: `docs/COLAB_EXECUTION_PLAN.md`.

**Status:** prepared and checked locally; **not yet executed on Colab**.

**Authorization boundary (D-015):** no data may reach Google until **D-015 Amendment 1** is recorded in
`docs/decision_log.md`. Step 1 refuses to continue before you set the switch.

Running the cells top to bottom performs **verification, a bounded timing benchmark and a dry run only**.
It never trains a full model: every action that trains anything (the bounded benchmark in section 5 and
the runs in sections 6 and 8) is disabled by default and runs only after you type the exact confirmation
phrase into that cell. Preflight records (environment, tests, benchmark) are saved to `cnet-runs/preflight/`. After a disconnect, an authorized run
resumes from its last checkpoint; a finished run is never recomputed or overwritten.
"""),
    md("## 0. Runtime\nRuntime → Change runtime type → **T4 GPU** (or any GPU). Free tier may not assign one."),
    code("""
import subprocess, torch
smi = subprocess.run(["nvidia-smi"], capture_output=True, text=True)
print(smi.stdout or "No NVIDIA GPU attached to this runtime")
print("torch", torch.__version__, "| CUDA available:", torch.cuda.is_available())
"""),
    md("## 1. Settings and authorization\nFill in `EXPECTED_COMMIT` with the hash Claude reports. Folders are in **your** Drive and must stay unshared."),
    code("""
D015_AMENDMENT_1_RECORDED = False      # set True ONLY after the amendment is recorded in docs/decision_log.md
EXPECTED_COMMIT = ""                   # full 40-character commit hash to run
DRIVE_ROOT = "/content/drive/MyDrive"
DATA_DRIVE = f"{DRIVE_ROOT}/cnet-data"  # code bundle here; datasets in one subfolder per manifest id
ARCHIVE = f"{DATA_DRIVE}/cicids2017_original/MachineLearningCSV.zip"   # the only dataset file needed
STORAGE = f"{DRIVE_ROOT}/cnet-runs"     # splits, checkpoints, run records, metrics persist here
CODE_DIR = "/content/cnet"              # VM-local working copy (fast, wiped between sessions)

assert D015_AMENDMENT_1_RECORDED, "Record D-015 Amendment 1 first; no dataset may reach Google before that."
assert len(EXPECTED_COMMIT) == 40, "Set EXPECTED_COMMIT to the full commit hash"
from google.colab import drive
drive.mount("/content/drive")           # you approve Google's prompt
"""),
    md("""
## 2. Code at the exact commit

**Default — code bundle (no GitHub needed).** On the laptop, from the repository folder:
`git archive --format=zip -o cnet_code_<first 12 chars of hash>.zip <hash>` and upload the zip to `cnet-data/`.
`git archive` stores the commit id inside the zip; the cell checks it against `EXPECTED_COMMIT`.
"""),
    code("""
import os, shutil, zipfile
bundle = f"{DATA_DRIVE}/cnet_code_{EXPECTED_COMMIT[:12]}.zip"
with zipfile.ZipFile(bundle) as zf:
    commit = zf.comment.decode().strip()
    assert commit == EXPECTED_COMMIT, f"bundle contains commit {commit}, expected {EXPECTED_COMMIT}"
    shutil.rmtree(CODE_DIR, ignore_errors=True)
    zf.extractall(CODE_DIR)
os.environ["CNET_GIT_COMMIT"] = commit   # recorded in every run (no .git folder in a bundle)
os.chdir(CODE_DIR)
print("code ready at commit", commit)
"""),
    md("""
**Alternative — GitHub (only after you configure and authorize a remote).** For a private repository, store a
read-only token in Colab Secrets as `GITHUB_TOKEN`. The token is passed only for the clone command, never written
to `.git/config`, files or logs, and is redacted from printed output.
"""),
    code("""
USE_GITHUB = False
REPO = ""   # e.g. "https://github.com/<owner>/<repo>.git"
if USE_GITHUB:
    import base64, os, shutil, subprocess
    from google.colab import userdata
    token = userdata.get("GITHUB_TOKEN") or ""
    extra = []
    if token:
        auth = base64.b64encode(f"x-access-token:{token}".encode()).decode()
        extra = ["-c", f"http.extraHeader=AUTHORIZATION: basic {auth}"]
    shutil.rmtree(CODE_DIR, ignore_errors=True)
    r = subprocess.run(["git", *extra, "clone", "-q", REPO, CODE_DIR], capture_output=True, text=True)
    print((r.stdout + r.stderr).replace(token, "***") if token else r.stdout + r.stderr)
    del token, extra
    subprocess.run(["git", "-C", CODE_DIR, "checkout", "-q", EXPECTED_COMMIT], check=True)
    os.chdir(CODE_DIR)
    print(subprocess.run(["git", "log", "-1", "--oneline"], capture_output=True, text=True).stdout)
"""),
    md("## 3. Environment, dependencies and tests on this runtime\nInstalls only what is missing, then checks the runtime against the frozen spec `configs/environments/colab_env_v1.yaml` (Milestone 3B-1). Python, the torch/CUDA stack and the GPU model cannot be changed by pip: a mismatch stops the notebook. If only pip packages differ, the exact versions are pinned and you must **restart the runtime (Runtime → Restart session) and run all again**. Tests must pass before anything else (real-data tests skip until the data is present)."),
    code("""
import importlib.metadata, importlib.util, subprocess, sys
# Decide what to install WITHOUT importing anything (an import would fail if a package is missing).
need = {"xgboost": "xgboost>=2.0", "pytest": "pytest", "yaml": "PyYAML", "sklearn": "scikit-learn", "pandas": "pandas",
        "numba": "numba", "shap": "shap"}   # shap imports numba; tests/test_audit.py needs both (blocked on the laptop)
missing = [pkg for mod, pkg in need.items() if importlib.util.find_spec(mod) is None]
if "xgboost>=2.0" not in missing and int(importlib.metadata.version("xgboost").split(".")[0]) < 2:
    missing.append("xgboost>=2.0")   # device="cuda" API needs XGBoost 2+
if missing:
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", *missing], check=True)
os.makedirs(f"{STORAGE}/preflight", exist_ok=True)
check = subprocess.run([sys.executable, "-m", "src.colab_env", "install", "--json", f"{STORAGE}/preflight/env_check.json"])
if check.returncode == 4:
    raise RuntimeError("Pinned package versions were installed. Runtime -> Restart session, then Run all again.")
if check.returncode != 0:
    raise RuntimeError("This runtime is INCOMPATIBLE with the frozen environment spec (see preflight/env_check.json). "
                     "Do not run experiments here.")
import xgboost   # only after installation and the environment check
print("xgboost", xgboost.__version__, "| CUDA build:", xgboost.build_info().get("USE_CUDA"))
import numba, shap
print("numba", numba.__version__, "| shap", shap.__version__)
!python -m pytest -q -ra 2>&1 | tee "{STORAGE}/preflight/pytest_before_data.txt"
!python -m src.env --dataset cicids2017_original --json "{STORAGE}/preflight/environment.json"
"""),
    md("## 4. Data: copy ONE archive and verify it\nOnly `MachineLearningCSV.zip` (235,102,953 bytes) is needed. Verified against the manifest's SHA-256 and CIC's MD5 before use; the runner then extracts only the Friday DDoS file and checks its CRC."),
    code("""
!mkdir -p data/raw/cicids2017_original
!cp "{ARCHIVE}" data/raw/cicids2017_original/
!python -m src.data.acquire verify cicids2017_original --file MachineLearningCSV.zip 2>&1 | tee "{STORAGE}/preflight/dataset_verify.txt"
!python -m src.experiments.population verify --json "{STORAGE}/preflight/split_population.json"
!python -m pytest -q -ra 2>&1 | tee "{STORAGE}/preflight/pytest_with_data.txt"
"""),
    md("## 5. GPU timing benchmark (about a minute): DISABLED by default\nBounded computational work: it trains **temporary** model components (60 autoencoder batches and 50 XGBoost rounds on the real training partition) only to measure speed, then discards them. It saves no model and evaluates nothing, and it is not an experiment run. Because it trains temporary components, it needs its own explicit authorization. It records timing (`cnet-runs/benchmarks/`) and peak memory (`cnet-runs/preflight/benchmark_resources.json`)."),
    code("""
AUTHORIZE_BENCHMARK = ""                # type exactly: I confirm the bounded benchmark is authorized
if AUTHORIZE_BENCHMARK == "I confirm the bounded benchmark is authorized":
    import json, resource, time
    t0 = time.time()
    subprocess.run([sys.executable, "-m", "src.experiments.ae_xgb", "--config", "configs/experiments/ae_xgb_d008_trackB.yaml",
                    "--device", "cuda", "--storage", STORAGE, "--benchmark"], check=True)
    gpu = subprocess.run(["nvidia-smi", "--query-gpu=name,memory.total,memory.used", "--format=csv,noheader"],
                         capture_output=True, text=True).stdout.strip()
    res = {"wall_s": round(time.time() - t0, 1),
           "peak_rss_mb_children": round(resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss / 1024, 1),
           "gpu_after": gpu}
    json.dump(res, open(f"{STORAGE}/preflight/benchmark_resources.json", "w"), indent=1)
    print(res)
else:
    print("Benchmark disabled: nothing was trained in this cell.")
"""),
    md("## 6. Legacy single-baseline run: DISABLED by default\nTrains one full model. Leave the phrase empty unless this exact run has been approved. `--device cuda` stops immediately if no GPU is attached. After a disconnect, re-running an authorized cell resumes it."),
    code("""
AUTHORIZE_LEGACY_BASELINE_RUN = ""      # type exactly: I confirm this training run is approved
if AUTHORIZE_LEGACY_BASELINE_RUN == "I confirm this training run is approved":
    subprocess.run([sys.executable, "-m", "src.experiments.ae_xgb", "--config", "configs/experiments/ae_xgb_d008_trackB.yaml",
                    "--device", "cuda", "--storage", STORAGE], check=True)
else:
    print("Training disabled: no model was trained in this cell.")
"""),
    md("## 7. Results\nOur measured results (not author-reported). Bring the run folder back to the laptop for review: download `cnet-runs/runs/<run_id>/` into `results/runs/`."),
    code("""
import glob, json
done = sorted(d for d in glob.glob(f"{STORAGE}/runs/ae_xgb_d008_trackB-seed0-cuda-*") if os.path.isfile(f"{d}/DONE"))
if not done:
    print("No completed legacy run (expected unless section 6 was authorized).")
else:
    run_dir = done[-1]
    print(run_dir)
    metrics = json.load(open(f"{run_dir}/metrics.json"))
    for part in ("val", "test"):
        m = metrics[part]
        print(part, {k: round(m[k], 6) for k in ("accuracy", "precision", "recall", "f1", "macro_f1", "auroc", "mcc")},
              m["confusion_matrix"], m["class_counts"])
    record = json.load(open(f"{run_dir}/run_record.json"))
    print(json.dumps({k: record[k] for k in ("input_dim", "autoencoder", "augmentation", "xgboost", "timings")}, indent=1))
"""),
    md("## 8. Milestone 3B (protocol r1)\nThe dry run shows the 110-fit matrix, batch status and estimates and trains nothing. Training ONE batch is disabled by default: it needs the approvals (D-007, D-012, D-020 r1, D-021, D-023) recorded in the decision log, the batch number, and the confirmation phrase. `--confirm-approved` is only the operator's confirmation; it is not proof that the approvals exist."),
    code("""
!python -m src.experiments.matrix_3b plan --storage "{STORAGE}" 2>&1 | tee "{STORAGE}/preflight/dry_run.txt"
AUTHORIZE_3B_BATCH = ""                 # type exactly: I confirm this training batch is approved
BATCH = None                            # e.g. 0, after approval only
if AUTHORIZE_3B_BATCH == "I confirm this training batch is approved" and isinstance(BATCH, int):
    subprocess.run([sys.executable, "-m", "src.experiments.matrix_3b", "run", "--batch", str(BATCH), "--storage", STORAGE,
                    "--device", "cuda", "--confirm-approved"], check=True)
else:
    print("Training disabled: no batch was trained in this cell.")
"""),
    md("## 9. Preflight manifest\nWrites `cnet-runs/preflight/MANIFEST.json`: the commit, the time and the SHA-256 of every preflight file produced by **this** session. Download the whole `preflight` folder for review."),
    code("""
import hashlib, json, glob, datetime
files = sorted(f for f in glob.glob(f"{STORAGE}/preflight/*") if not f.endswith("MANIFEST.json"))
manifest = {"commit": EXPECTED_COMMIT, "utc_time": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
            "files": {os.path.basename(f): hashlib.sha256(open(f, "rb").read()).hexdigest() for f in files}}
json.dump(manifest, open(f"{STORAGE}/preflight/MANIFEST.json", "w"), indent=1)
print(json.dumps(manifest, indent=1))
"""),
]

nb = {
    "cells": cells,
    "metadata": {"accelerator": "GPU", "colab": {"provenance": [], "gpuType": "T4"},
                 "kernelspec": {"display_name": "Python 3", "name": "python3"}, "language_info": {"name": "python"}},
    "nbformat": 4, "nbformat_minor": 5,
}
out = Path(sys.argv[1])
out.write_text(json.dumps(nb, indent=1) + "\n", encoding="utf-8")
print("wrote", out, len(cells), "cells")
