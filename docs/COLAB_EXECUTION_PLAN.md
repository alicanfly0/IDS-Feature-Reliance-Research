# Google Colab execution plan (Milestone 1 onward)

**Status (2026-11-08, Milestone 1A):**

- **Implemented and tested locally (Windows, CPU):**
  - the AE-XGBoost runner `src/experiments/ae_xgb.py`, with resumable stages, never overwriting a finished run, and identity checks;
  - `src/env.py`;
  - the notebook workflow `notebooks/colab_runner.ipynb`, statically checked.
- **Not executed on Colab or Linux yet.** GPU behaviour, Colab package versions and Drive I/O are unverified.
- **D-015 Amendment 1 authorized (2026-11-08).** No upload has happened yet; you upload the zip to your private Drive yourself (step 3 below).

## First real run — exact steps (AE-XGBoost, D-008 scope, track B)

**You do, once:**

1. Record **D-015 Amendment 1** as authorized in `docs/decision_log.md` (the exact text is there) and ask Claude to commit it. Claude reports the commit hash `H`.
2. On the laptop, from the repository folder:

   ```
   git archive --format=zip -o cnet_code_<first 12 chars of H>.zip H
   ```

   The bundle stores `H` inside the zip and contains no data.
3. In Google Drive (free 15 GB is enough), create the private folders `MyDrive/cnet-data/`, `MyDrive/cnet-data/cicids2017_original/` and `MyDrive/cnet-runs/`. Upload:
   - the bundle to `MyDrive/cnet-data/cnet_code_<first 12 chars of H>.zip`;
   - `data/raw/cicids2017_original/MachineLearningCSV.zip` (235,102,953 bytes; the only dataset file needed) to **`MyDrive/cnet-data/cicids2017_original/MachineLearningCSV.zip`**. This is the path the notebook's `ARCHIVE` setting reads.

**You do, each session:**

4. Open `notebooks/colab_runner.ipynb` in Colab (File → Upload notebook, or from the bundle). Runtime → Change runtime type → T4 GPU.
5. In cell 1, set `D015_AMENDMENT_1_RECORDED = True` and `EXPECTED_COMMIT = "H"`. Run all cells and approve the Drive prompt.
   - Cell 3 runs the test suite on Colab's packages: the first real Colab verification.
   - Cell 4 verifies the archive's sha256 and MD5.
   - Cell 5 is a one-minute GPU benchmark.
   - Cell 6 is the run.
6. After a disconnect, run all cells again: the run resumes from the last AE epoch checkpoint, or later stage, and a finished run prints "already complete".
7. Download `MyDrive/cnet-runs/runs/<run_id>/` into the laptop's `results/runs/` so Claude can review the measured results.

**Run identity:**

- `run_id = ae_xgb_d008_trackB-seed0-cuda-<config hash>`.
- Outputs go to `MyDrive/cnet-runs/runs/<run_id>/`, plus `MyDrive/cnet-runs/splits/ae_xgb_d008_trackB-split.json` (written once, then verified on every run).

**Expected cost:** the laptop benchmark projects ≤ 1.5 min of AE training and ≤ 0.3 min of XGBoost on CPU (decision log D-016). The GPU benchmark in cell 5 gives the real Colab figure.

Architecture decision: D-016 in `docs/decision_log.md`.

**Design rules:**

- One code base runs unchanged on Windows CPU and on Linux/Colab CUDA.
- The notebook is a thin launcher; all science lives in `src/` and is tested locally first.
- Plan for free Colab:
  - a GPU may not be assigned;
  - sessions can disconnect;
  - the VM disk is wiped between sessions.

---

## 1. One code base for Windows CPU and Colab CUDA

**What already works on both platforms:**

- **Platform-neutral code:**
  - all of `src/` uses `pathlib` and standard-library networking;
  - paths in configs and the manifest are repository-relative;
  - reports store repository-relative paths.
- **Entry points:**
  - `run.cmd` and `scripts/*.ps1` are **Windows conveniences only**;
  - on Colab, every step is the same Python call: `python -m src.<module>` from the repository root;
  - nothing in this plan requires Windows.
- **Library compatibility:**
  - an independent reviewer ran the test suite under numpy 2.3.5 / pandas 2.2.3 / scikit-learn 1.8.0 (72 passed, 1 skipped);
  - locally we pin numpy 1.26.4 / pandas 2.3.3 / scikit-learn 1.9.0;
  - so the code is not tied to the local pins.

**Dependency policy on Colab:**

- Use Colab's preinstalled scientific stack (numpy, pandas, scikit-learn, torch). Install only what is missing (e.g. `pytest`, `xgboost` if absent).
- **Do not** `pip install -r requirements.txt` on Colab: downgrading numpy can break Colab's preinstalled torch.
- Run the test suite on Colab before any training, and record the exact versions in every run (§10). If a version difference matters, add a `requirements-colab.txt` at that point.

**Code style required from Milestone 1 model code:**

- Take a `device` argument and never hard-code `"cuda"`.
- Read batch sizes and similar settings from the experiment config.
- XGBoost: use `device="cuda"` or `"cpu"` from the same selector (XGBoost ≥ 2.0). The rest of the code path is identical.

## 2. Moving verified code from Claude Code to Colab

**Preferred: GitHub.**

1. Claude Code develops and tests locally, then commits (only when you ask).
2. Once **you** create a GitHub repository and configure the remote, Claude can push the verified commit. It does this only after your explicit go-ahead, every time.
3. The notebook clones the repository and checks out the **exact commit** to run (`COMMIT = "<hash>"`). The commit hash goes into every run record.
4. **Private repository:** Colab needs a read-only token.
   - Create a fine-grained GitHub token with read access to that one repository.
   - Store it in **Colab Secrets** as `GITHUB_TOKEN`; the notebook reads it with `google.colab.userdata`.
   - Never paste tokens into notebook cells or commit them.

**Fallback without GitHub:**

- `git archive --format=zip -o cnet_<hash>.zip <hash>` produces a clean snapshot of one commit; upload it to the Colab session.
- Weaker traceability: the commit hash must be written down by hand.
- Note: uploading even code to Colab uses a Google service (see §5).

## 3. Manual steps only you can do

| When | Step |
|---|---|
| Once | Create the GitHub repository (private recommended) and tell Claude its URL; authorize pushing (e.g. `gh auth login` in your own terminal). |
| Once | If the repository is private: create a fine-grained, read-only token and add it to Colab Secrets as `GITHUB_TOKEN`. |
| Once | Decide and record **D-015 Amendment 1** (§5) before any dataset reaches Google. |
| Once, after the amendment | Upload `data/raw/cicids2017_original/MachineLearningCSV.zip` (235,102,953 bytes) to the **private, unshared** Drive folder `MyDrive/cnet-data/cicids2017_original/`. |
| Every session | Sign in to Google in the browser and open `notebooks/colab_runner.ipynb` from GitHub (File → Open notebook → GitHub). |
| Every session | Runtime → Change runtime type → choose a GPU. Not guaranteed on free tier. |
| Every session | Run the Drive-mount cell and approve Google's authorization prompt. |
| Every session | Run the cells top to bottom. If no GPU was assigned, decide whether to wait or run a CPU-sized job. |
| After a run | Bring results back for Claude to review (§4). |

## 4. What Claude can and cannot automate

| Claude can (locally, now) | Claude cannot assume |
|---|---|
| Write and test all code, configs and the notebook on Windows CPU | Sign in to your Google account or approve OAuth/Drive consent |
| Make commits when you ask; build review zips | Choose a Colab runtime or obtain a GPU |
| Push to GitHub **after** you configure the remote and authorize it | Click "Run" in Colab, keep a session alive, or see Colab output |
| Produce exact commands and checklists for each Colab run | Upload data to Drive (not allowed by D-015 until amended, and needs your account) |
| Check run records, metrics and logs **once you bring them back**: download the run folder from Drive into `results/runs/`, or paste the summary | Verify that a Colab run happened, or what it produced, without those files |

- Driving Colab through a browser tool would mean acting inside your Google account and approving consent screens. Claude must not do that, so the plan does not depend on it.

## 5. Making the dataset available in Colab without repeated downloads

**Authorization first.** Under D-015 nothing is uploaded today. Running on Colab **always** sends the data to Google infrastructure, even as a temporary session upload. **D-015 Amendment 1** must state:

1. Which files may be processed on Colab VMs. For Milestone 1 that is only `MachineLearningCSV.zip`, from which the Friday DDoS file is used.
2. Whether a persistent private copy may sit in your Google Drive, and its folder.
3. That the folder is unshared. CIC's data is "publicly available for researchers", but we must not re-host it.
4. The date and who authorized it.

**Proposed arrangement, effective only after the amendment:**

- **Stored once on Drive:**
  - the verified archive in `MyDrive/cnet-data/<dataset id>/` (only what the milestone needs);
  - no extracted CSVs on Drive (slow and large).
- **Each session:**
  - copy the archive from Drive to the VM's local disk at `/content/cnet/data/raw/<dataset id>/`;
  - verify it (§6). The runner then extracts **only** the Friday DDoS member (77 MB) and checks its CRC; there is no need to unpack all 8 day files (844 MB).
  - Extracting the 235 MB archive takes seconds to a minute and avoids any repeated download from CIC, which would need the registration form again.

**Other sources:**

- UNSW-NB15, NF-UNSW-NB15-v2 and Engelen can also be re-downloaded in Colab from their official sources with `python -m src.data.acquire download <id>`.
- That still counts as processing on Google infrastructure and needs the same amendment.

## 6. Verifying checksums after transfer

Run the same command as locally:

```
python -m src.data.acquire verify cicids2017_original --file MachineLearningCSV.zip
```

**What it checks:**

- the exact byte size;
- the sha256 recorded in `configs/datasets.yaml`;
- the publisher's MD5 where one is recorded (CIC).

A file that fails is not used.

**Before each D-008 run:** the real-data test also checks the extracted Friday DDoS CSV against the zip member's CRC-32:

```
python -m pytest tests/test_real_data_smoke.py -k friday
```

## 7. Where outputs persist across disconnections (implemented)

**Storage root:** set with `--storage` (or the `CNET_STORAGE` variable). Locally it defaults to `results/`, which is Git-ignored for runs, splits and benchmarks; on Colab it is `MyDrive/cnet-runs`.

**Layout:**

| Path under the storage root | Contents |
|---|---|
| `splits/<experiment>-split.json` | Split indices + provenance + record digest; written once, verified on every later run |
| `runs/<run_id>/identity.json` | Config hash, device, Git commit, dataset sha256s |
| `runs/<run_id>/effective_config.json` | base.yaml + experiment file, as used |
| `runs/<run_id>/environment-<time>.json` | `src/env.py` snapshot per session (hardware, packages, commit, seed, dataset hashes) |
| `runs/<run_id>/data_report.json` | Recomputed counts: raw, per-rule, excluded source rows, sentinels, conflicts, partitions, overlaps |
| `runs/<run_id>/preprocessor.json` | Fitted train-only state (constants, medians, min/max, input dimension, overlap re-check) |
| `runs/<run_id>/checkpoints/ae_last.pt` | Model + optimizer + epoch + early-stopping state + RNG states + config |
| `runs/<run_id>/checkpoints/ae_best.pt` | Best weights by validation reconstruction MSE |
| `runs/<run_id>/ae_done.json` | AE training history |
| `runs/<run_id>/latent.npz` | Latent codes for train / val / test (so XGBoost never forces AE retraining) |
| `runs/<run_id>/xgb_model.json` | XGBoost model (early-stopped) |
| `runs/<run_id>/predictions_val.csv.gz`, `predictions_test.csv.gz` | `source_row`, true label, P(DDoS), predicted label |
| `runs/<run_id>/metrics.json` | Train (diagnostic only), validation and test metrics |
| `runs/<run_id>/run_record.json` | Summary: identity, split fingerprint, input dimension, AE/XGBoost outcome, augmentation decision, timings |
| `runs/<run_id>/log.txt` | Run log |
| `runs/<run_id>/DONE` | Written last |

**Writes:** every file is written atomically (`*.tmp`, then `os.replace`). A disconnect never leaves a half-written file under its real name.

**Size:** a full run is tens of MB, mostly `latent.npz` and predictions, which fits the free 15 GB Drive.

**What goes into Git:** only small, reviewed summaries, copied in deliberately.

## 8. Resuming interrupted experiments safely (implemented)

`run_id = <experiment>-seed<model_seed>-<device>-<first 8 hex of the config hash>`. The same config, seed and device always map to the same folder.

| Situation | Behaviour |
|---|---|
| `DONE` exists | Nothing is recomputed or overwritten |
| Folder exists without `DONE` | Config hash, device and dataset hashes must match, or the run refuses to start. A different Git commit is refused unless `--allow-code-change` is given (recorded) |
| AE interrupted | Resumes from `ae_last.pt`. Epoch e uses a batch order seeded by (seed, e), so a resumed run is **bit-identical** to an uninterrupted one on CPU (tested) |
| Interrupted after the AE | `latent.npz` and the best weights are reused; only later stages run (tested) |
| Different config | A different `run_id`; the saved split is verified and reused, so the evaluation population is the same (tested) |

## 9. CPU or CUDA at runtime

`src/env.py` provides `select_device(prefer)`:

| `prefer` | Behaviour |
|---|---|
| `"auto"` | Uses CUDA when torch reports a GPU, otherwise CPU |
| `"cpu"` | Always CPU |
| `"cuda"` | Fails immediately if no GPU is available |

- **Heavy Colab runs** should use `prefer="cuda"`, so a free-tier session without a GPU stops at once instead of silently running for hours on CPU.
- **Local development and tests** use `"auto"`; on this machine that means CPU.
- **Reproducibility caveat:** GPU and CPU results can differ slightly (non-deterministic kernels, floating-point order). `set_seeds(seed, deterministic=True)` sets the cuDNN deterministic flags, but results are compared only between runs on the same device type. The device is always recorded.

## 10. What every run records

| Item | Source |
|---|---|
| Python and OS version, CPU, core count, RAM | `src/env.py` (`snapshot`) |
| GPU name/memory, CUDA version, `nvidia-smi` output, chosen device, whether in Colab | `src/env.py` |
| Package versions (numpy, pandas, scikit-learn, PyYAML, pytest, torch, xgboost, lightgbm, shap) | `src/env.py` |
| Git commit and dirty flag | `src/env.py` (refuse training on a dirty tree in Colab) |
| Random seeds (partition seed, model seed) and what was seeded | `set_seeds()` + config |
| Dataset identity: manifest sha256 per file | `src/env.py` (`dataset_hashes`) + `split.json` source |
| Effective configuration (base + experiment) | `src/config.py` (`write_run_record`) |
| Split fingerprint, source, record digest; D-011 rule counts and excluded rows | `src/data/split.py`, run code |

Try it locally:

```
python -m src.env --dataset cicids2017_original
```

On this machine it prints Python 3.11.9, `Windows-10-10.0.26200-SP0` (build 26200 = Windows 11), 12 logical CPUs, 16.6 GB RAM, device `cpu`, no GPU, the current commit, and the manifest hashes.

---

## First Colab session checklist

Superseded by **First real run — exact steps** at the top of this document.

---

## Session steps from Milestone 3B-1 (verification and preflight)

1. **Build the bundle.** On the laptop, build the bundle for the approved commit H:
   `git archive --format=zip -o cnet_code_<H[:12]>.zip H`. Upload it to `MyDrive/cnet-data/`
   (the dataset zip is already there from session 1).
2. **Open the notebook** `notebooks/colab_runner.ipynb` in Colab and select the **T4 GPU** runtime.
   The frozen spec requires a Tesla T4.
3. **Fill in cell 1:** `D015_AMENDMENT_1_RECORDED = True` and `EXPECTED_COMMIT = "H"`. Leave every
   `AUTHORIZE_...` phrase empty. Then **Runtime → Run all**, and allow Drive access.
4. **Section 3** checks the runtime against `configs/environments/colab_env_v1.yaml`:
   - if it reports **pinned packages installed**, do *Runtime → Restart session* and *Run all* again;
   - if it reports **incompatible** (Python, torch/CUDA, GPU model), stop: no experiments may run in
     that runtime. A new spec version needs a decision.
5. **Records.** The session writes these to `MyDrive/cnet-runs/preflight/`:
   `env_check.json`, `environment.json`, `pytest_before_data.txt`, `dataset_verify.txt`,
   `split_population.json`, `pytest_with_data.txt`, `dry_run.txt`, and `MANIFEST.json` (SHA-256 of
   each). It also writes `benchmark_resources.json`, but only if the benchmark phrase was typed.
6. **Download** the `preflight` folder and give it to Claude for review. Never substitute locally
   regenerated output for Colab output.

Runs trained in different environments cannot be compared: the runner refuses to resume a run in a
changed environment, and aggregation refuses mixed environments before computing any metric.
