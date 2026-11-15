# CNET project: working rules for Claude

**Project:** "How Real Is 99% Accuracy? Auditing Feature Reliance in Network Intrusion Detection". Authors: Ali Waseem Abbasi (i23-2630) and Muhammad Mudassir (i23-2562), DS-7A, FAST-NUCES.

**Status:** Phase III is closed (`phase3_final_review/PHASE3_FINAL_SIGNOFF.md`). Phase IV is the paper in `paper/main.tex`. Start it only when the user sends the start prompt.

## 1. Writing: every piece of prose uses the humanise skill

- **Use the skill everywhere.** That covers paper sections, reports, READMEs, commit message bodies and chat replies. The skill is `.claude/skills/humanise/SKILL.md`; the full sourced list of tells is in `references/signs.md`.
- **Check every paper section before calling it done:**
  ```
  .\.venv\Scripts\python.exe .claude\skills\humanise\scripts\humanise_check.py paper\main.tex --paper
  ```
  Targets: 0 kill-list hits (a technical term may stay, with a reason); sentence-length SD of at least 8; about 5.3 characters per word or fewer.
- **Paper register:** "we" is fine; no contractions, exclamation marks, emoji, bold in prose, or chatty qualifiers. Plain verbs (is, has, used, showed). One precise term per concept, repeated.
- **Humanising never changes substance.** It doesn't touch a number, a citation, a claim's strength or a caveat, and it never adds an invented anecdote or source.

## 2. Phase IV positioning (the user's guidance, 2026-11-14)

- **Lead with the contribution:**
  > near-perfect intrusion-detection performance can coexist with strong sensitivity to feature-extraction changes and with duplicate-driven score inflation.
  
  Don't write "dataset-specific shortcuts": the in-domain ablations don't show shortcut reliance.
- **Build the case from strength:** 110 controlled AE-XGBoost fits, independent statistical verification, 70 corrected-data fits, the transfer result, the duplicate audits, and attribution vs intervention.
- **Keep limitations precise and in their place.** They belong in the reproducibility and discussion sections. Don't repeat them through the abstract, introduction and conclusion, and don't hide them.
- **Never claim full reproducibility or a proven causal mechanism.**
- **Limitation paragraph to use, adapted only for flow:**
  > All 70 corrected-dataset fits were completed, and their predictions were re-scored and hash-recorded before the Colab runtime expired. Because the storage quota prevented a complete upload, full run artifacts (checkpoints, logs, predictions) are preserved for 22 of the 70 runs; for the remaining 48, results rest on that verified prediction record, which limits training-level reproducibility. In addition, 17 corrected-data autoencoders reached the 100-epoch limit; the corresponding extended-training check (cap 200) was performed only for the two capped original-data fits, where it changed no conclusion. These limitations constrain claims of checkpoint-level reproducibility and convergence robustness but do not by themselves invalidate the recorded comparisons.

## 3. Wording that must be right in the paper

| Topic | Rule |
|---|---|
| r1 intervals | The difference interval is **99.5%** and the TOST interval is **99%**. Fix the "99%" labels in `paper/tables/main_r1.tex`, the captions of `tab:main` and `fig:contrasts`, and the text. |
| R4a intervals | Difference **98.33%**; TOST **96.67%**. |
| Equivalence | Always "within the pre-declared margin" (SESOI 0.001: about 33 r1 errors and about 22 R4a errors, against baselines of about 6 and about 2). |
| R4a-i | Descriptive transfer result: "associated with", never "caused by" or "reliance on defects". |
| R4a-ii vs r1 | Observational comparison only. |
| MES-DNN | Report per network (attack prevalence 4.0% vs 64.0%); never the pooled 85.5% / 0.715. N1's own base model keeps MCC about 0.94 in both split modes, so the ensemble collapse is a stacking effect; only the N2 base drop (0.906 → 0.150) is tied to duplicate hold-out. |
| Wardana | Their **Scenario 2** (integrated stack, Table 10: 96.67% accuracy / F1 95.36%) is the analogue of our setting; Scenario 3 is new-network integration (Table 11). No unseen-network claim. |
| ARR vs ablation | ARR "all registered" covers 23 features; ablation group U covers 20 (A ∪ B ∪ C). Don't call both "union". |
| Baselines | Adaptations, not reproductions. Describe the differences from the published numbers; never rank against them. |
| D-021 | The cap-200 check on r1 D s0/s5 changed nothing (8→9 and 14→13 errors; same Holm decision). |

Every number in the paper must come from a verified record, with the source path in a `%` comment beside it. The records are in `results/`, `phase3_final_review/evidence/verification/`, `PHASE3_ALL_METRICS.csv` and `PHASE3_STATISTICAL_FINDINGS.csv`.

## 4. Standing project rules

- **Nothing fabricated or estimated.** Never invent, estimate or "fill in" results, logs, citations or statistics. Missing evidence is reported as missing.
- **Git:** commit locally only and never push. Leave `MILESTONE_0_HANDOVER.md` and `docs/external/` uncommitted. Scan for personal paths, emails and secrets before committing. Commit messages end with the `Co-Authored-By` line.
- **Frozen material:** frozen protocols and experimental outputs are not rewritten. Corrections go into new records or clearly marked notes.
- **Locations:** everything stays inside this project folder.
- **Tooling:**
  - Python is `.\.venv\Scripts\python.exe`.
  - Local torch, numba and shap are blocked by Windows Smart App Control. Don't change that setting; heavy runs use Colab.
  - Build the LaTeX with `Set-Location paper; ..\tools\tectonic\tectonic.exe --keep-logs main.tex`.
