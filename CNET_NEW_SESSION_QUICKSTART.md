# CNET — New session quickstart

Full context: `CNET_COMPLETE_PROJECT_HANDOVER.md` (read it first). This page is the short version.

## Current status (2026-11-08)

- Branch `main`. HEAD = "Add the complete project handover for a new Claude Code session" (adds only the two handover files; parent `fbd10cd`, the last research commit). No remote; nothing pushed.
- Untracked on purpose: `MILESTONE_0_HANDOVER.md`.
- Done: Milestone 0 (data + tooling), 1A (AE-XGBoost baseline, test F1 0.999870 on 33,877 rows, one seed), 1B (Destination Port ablation: F1 0.999870 vs 0.999818 on 33,486 common rows, McNemar p = 0.625), 2A (artifact registry, permutation SHAP pilot on 6 variants, ARR@K).
- Tests: 122 passed at HEAD (with data).
- **Active task: registry correction for the CICFlowMeter TCP flag-count defect (ACK/PSH Flag Count). NOT STARTED.** Handover §8 has the step list.

## Important paths

| What | Path |
|---|---|
| Project root | `C:\Users\aliwa\OneDrive\Desktop\FAST NUCES\semester 7\CNET\cnet project implementation` |
| Decisions | `docs/decision_log.md` (D-001 … D-019) |
| Latest report | `docs/MILESTONE_2A_REPORT.md` |
| Registry | `configs/artifact_registry.yaml`, `src/audit/registry.py` |
| ARR / SHAP | `src/audit/arr.py`, `src/audit/composite.py`, `src/audit/shap_explain.py`, `tests/test_audit.py` |
| SHAP pilot | `results/shap/ae_xgb_d008_trackB-seed0-cpu-565a8b9e/` (arrays `variant-*/shap_values.npz`, ignored) |
| Baseline run (ignored, do not touch) | `results/runs/ae_xgb_d008_trackB-seed0-cpu-565a8b9e/` |
| Ablation run (ignored, do not touch) | `results/runs/ae_xgb_d008_trackB_noDstPort-seed0-cpu-3054b399/` |
| Datasets (ignored) | `data/raw/<dataset id>/` |
| Papers / Phase II | `../project/` (sibling folder) |
| Review package | `MILESTONE_2A_REVIEW.zip` (incl. `review/recompute_from_arrays.py`) |

## Immediate next actions

1. Verify the repo state against the handover (`git status`, `git log --oneline -5`, test suite).
2. Ask the user for the Milestone 2A independent review document. Get permission to read Engelen's extended documentation: `https://intrusion-detection.distrinet-research.be/WTMC2021/extended_doc.html`.
3. Propose the registry change (multi-mechanism entries, web-source evidence rule, flag-column reconciliation) and wait for approval.
4. Recalculate ARR@K from the **existing** six SHAP summaries/arrays into new files (keep the originals), update the docs, run the tests, commit, don't push, STOP.

## Safe commands

```powershell
git status
git log --oneline -8
.\run.cmd -m pytest -q
.\run.cmd -m pytest tests\test_audit.py -q
.\run.cmd -m src.data.acquire verify all
.\run.cmd -m src.audit.shap_explain --config configs/experiments/ae_xgb_d008_trackB.yaml --run results/runs/ae_xgb_d008_trackB-seed0-cpu-565a8b9e --summarize
```

Re-running completed experiment configs is safe: they print "already complete" or "cached". **Still, do not launch new runs without approval.**

## Outstanding blockers

- The Milestone 2A review text and Engelen's extended documentation have not been read.
- Phase III/IV assignment brief and rubric not found locally (ask the user).
- Open decisions: D-004, D-005, D-006, D-007 (statistics, track A), D-009, D-010, D-012 (confirm levels), D-013.
- Colab has never run. The user must sign in and upload the dataset zip and code bundle to their private Drive (D-015 Amendment 1 authorized). The assistant never enters passwords.
- No GitHub remote. Pushing needs explicit approval.
- Budget: PKR 0.

## Initial prompt for the incoming assistant

```
You are taking over the CNET Phase III/IV research project from a previous Claude Code account.
The repository is at:
C:\Users\aliwa\OneDrive\Desktop\FAST NUCES\semester 7\CNET\cnet project implementation

Read CNET_COMPLETE_PROJECT_HANDOVER.md in the project root first, completely, and follow its
"START HERE" section. Continue from the existing repository; do NOT rebuild the project, do NOT
redo Milestones 0, 1A, 1B or 2A, do NOT retrain the baseline or ablation, and do NOT recompute SHAP.

Then:
1. Check git status and HEAD (expected: the handover commit on top of fbd10cd; only MILESTONE_0_HANDOVER.md untracked), run the test suite
   (.\run.cmd -m pytest -q, expected 122 passed), and confirm the local datasets, run folders and
   SHAP arrays listed in the handover exist.
2. Report a short verified status and any difference from the handover.
3. Propose a plan for the pending registry correction (TCP flag-count defect: ACK/PSH Flag Count,
   section 8 of the handover), and wait for my approval before editing files.

Constraints: PKR 0 budget, free resources only; no uploads, no Git push, no new training or
expensive experiments without my explicit approval; never type my passwords; never fabricate
results or citations; keep all existing artifacts.
```
