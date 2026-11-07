# Google Colab execution plan (Milestone 1 onward)

**Status (2026-11-07):**

- **Written:** this plan.
- **Done and tested locally (Windows, CPU):** `src/env.py`, which handles device selection, seeding and the environment snapshot.
- **Scaffold only:** `notebooks/colab_runner.ipynb`. It has **not** been run on Colab.
- **Not verified on Colab or Linux:** nothing here has been executed there.
- **No data uploaded:** no dataset, checkpoint or private file has been uploaded anywhere (D-015).

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
| Once, after the amendment | Upload `data/raw/cicids2017_original/MachineLearningCSV.zip` (235,102,953 bytes) to a **private, unshared** Drive folder, e.g. `MyDrive/cnet-data/cicids2017_original/`. |
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
  - verify it (§6), then extract it locally (`python -m src.data.acquire extract <dataset id>`).
  - Extracting the 235 MB archive takes seconds to a minute and avoids any repeated download from CIC, which would need the registration form again.

**Other sources:**

- UNSW-NB15, NF-UNSW-NB15-v2 and Engelen can also be re-downloaded in Colab from their official sources with `python -m src.data.acquire download <id>`.
- That still counts as processing on Google infrastructure and needs the same amendment.

## 6. Verifying checksums after transfer

Run the same command as locally:

```
python -m src.data.acquire verify cicids2017_original
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

## 7. Where outputs persist across disconnections

**Layout per run:** each run writes to `results/runs/<run_id>/`:

| File | Contents |
|---|---|
| `run_record.json` | Effective config, split fingerprint and source, preprocessor state, metrics summary |
| `environment.json` | `python -m src.env` snapshot |
| `split.json` | Saved split, with record digest (§8) |
| `checkpoints/` | Model state |
| `log.txt` | Run log |
| `metrics.json` | Final metrics |
| `figures/` | Plots |
| `DONE` | Written last, atomically |

**On Colab (after the amendment):**

- `results/runs/` is a symlink to a private Drive folder, e.g. `MyDrive/cnet-runs/`, so it survives disconnection.
- Checkpoints and logs are written there **atomically**: write `name.tmp`, then `os.replace`. A disconnect mid-write never leaves a half-written file under the real name.

**Locally:** `results/runs/` is Git-ignored (it may hold checkpoints).

**What goes into Git:** only small, reviewed summaries (tables, figures, run records without checkpoints), copied into the repository deliberately.

## 8. Resuming interrupted experiments safely

**Run identity:** each run gets a deterministic id:

    run_id = <experiment>-<track>-seed<model_seed>-<first 8 hex of sha256(effective config)>

The same config and seed always map to the same folder.

**Before starting, the runner:**

1. Skips the run if `DONE` exists. No duplicate work.
2. If the folder exists without `DONE`, checks that the saved record matches the current run:
   - effective-config hash;
   - **Git commit**;
   - dataset sha256s;
   - split record digest (`load_split(..., expected_source=..., n_rows=...)` refuses edited or mismatched splits).

   If anything differs, it refuses to resume and asks for a new run id. Code or data changed, so the results would mix.
3. Otherwise resumes from the newest complete checkpoint:
   - **AE:** per epoch (model, optimizer, early-stopping state, RNG states);
   - **XGBoost:** continue boosting from the saved booster, or retrain (it is fast) and document which.

**During the run:**

- Checkpoint at least every N epochs **or** every ~10 minutes, whichever comes first.
- `DONE` is written only after `metrics.json` and the final model are complete.

**Status:** this logic is Milestone 1 work and is **not implemented yet.** The building blocks exist: `save_split` / `load_split` with provenance checks, `write_run_record`, `src/env.py`.

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

## First Colab session checklist (Milestone 1)

**Do not start before all three are done:**

- D-015 Amendment 1 recorded;
- GitHub remote configured;
- D-007 fully signed off.

**Then:**

1. Open the notebook, select a GPU runtime, and run the GPU check cell.
2. Clone the repository at the agreed commit and install only the missing packages.
3. Run `python -m pytest -q` on Colab and record the result. This is the first real verification of Colab compatibility.
4. Mount Drive, copy the archive, run `python -m src.data.acquire verify cicids2017_original`, then `extract`.
5. Run `python -m src.env --dataset cicids2017_original --json results/runs/env_check/environment.json`.
6. Only then start the Milestone 1 experiment command (not yet written).
