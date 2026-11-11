# R4a run on Colab (about 10 minutes of your time, then ~2 h unattended)

Approved scope: D-024 (R4a-ii, 70 fits) and R4a-i (descriptive). Code commit
`b6297226d6dc0eb946603fc2f66c44b8db816fee`, bundle `cnet_code_b6297226d6dc.zip`
(SHA-256 `046dcf941fcfab8aaf1e0af3ff2dde12b38a84bdb1d27a022a6d135d02255149`).

## A. Upload two files (laptop -> Google Drive)
1. `cnet project implementation\cnet_code_b6297226d6dc.zip` -> **My Drive / cnet-data/** (next to the older bundles).
2. Already done last night: Engelen `dataset.zip` in **My Drive / cnet-data / cicids2017_engelen_wtmc2021/**.
   (The older bundle `cnet_code_9d65e0a49b3c.zip` is not needed any more; leave it.)

## B. Open the NEW notebook
1. Go to colab.research.google.com -> **File -> Upload notebook** -> choose
   `cnet project implementation\notebooks\colab_runner.ipynb`.
2. **Runtime -> Change runtime type -> T4 GPU -> Save.**

## C. Fill in section 1 (two lines only)
```python
D015_AMENDMENT_1_RECORDED = True
EXPECTED_COMMIT = "b6297226d6dc0eb946603fc2f66c44b8db816fee"
```
Change nothing else in the notebook.

## D. Run all
**Runtime -> Run all**, and approve the Drive popup.
- If section 3 stops with "Restart session": **Runtime -> Restart session**, then **Run all** again.
- Wait until section 9 finishes (~5-8 min). Section 4 must print `OK` for **both** datasets, and
  the tests must show `0 failed`. If anything is red, stop and send a screenshot.

## E. One cell for everything (press once, then leave)
Click **+ Code** at the very bottom, paste, press ▶:
```python
import subprocess, sys, os
for b in range(0, 7):          # R4a-ii: 70 fits in 7 batches (~1.5-2.5 h)
    subprocess.run([sys.executable, "-m", "src.experiments.matrix_3b", "run", "--design", "r4a", "--batch", str(b),
                    "--storage", STORAGE, "--device", "cuda", "--confirm-approved"], check=True)
os.makedirs(f"{STORAGE}/analysis_r4a", exist_ok=True)
subprocess.run([sys.executable, "-m", "src.evaluation.aggregate_3b", "--design", "r4a", "--storage", STORAGE,
                "--out", f"{STORAGE}/analysis_r4a/aggregate_r4a.json"], check=True)
subprocess.run([sys.executable, "-m", "src.evaluation.score_r4a_i", "--storage", STORAGE,
                "--out", f"{STORAGE}/analysis_r4a/r4a_i_scores.json"], check=True)
print("R4A ALL DONE")
```
- Keep the tab open. It is fine to leave the laptop (plugged in, not asleep) while at uni.
- If Colab disconnects: reconnect (T4), **Run all**, then press ▶ on this cell again. Finished
  runs are skipped; an interrupted run resumes.

## F. When it prints `R4A ALL DONE`
In Google Drive: **cnet-runs -> right-click `analysis_r4a` -> Download**, and upload the zip in the chat.
