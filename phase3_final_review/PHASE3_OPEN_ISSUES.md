# Open issues (genuine only)

No essential result is missing. All 195 fits and 220 inference evaluations are present and verified. The issues below are reporting errors to fix in Phase IV, or residual reproducibility and scientific limits.

## Reporting errors (fix before or during Phase IV; values are correct)

**OI-1. Mislabelled r1 interval level.**
- The pre-registered and computed difference interval is **99.5%** (1 − 0.05/10).
- These label it "99%":
  - `results/milestone3b/tables_r1.md` header;
  - `paper/tables/main_r1.tex` header;
  - `paper/main.tex` Table `tab:main` caption, Fig. `fig:contrasts` caption, and the text at lines 301–302.
- The 99% level is the TOST interval.
- The fix is a label change. The frozen output and the paper were not edited (constraint).

**OI-2. MES-DNN pooled across incompatible populations.**
- `paper/main.tex` Table `tab:compare` reports ensemble accuracy and F1 as **means over the two networks**: 85.5% / 0.715 random, 61.7% / 0.445 duplicate-aware.
- The two networks have attack prevalence 4.0% vs 64.0%.
- Replace with the per-network values in `PHASE3_BASELINE_COMPARISON.md`.

**OI-3. Wardana scenario numbering. RESOLVED 2026-11-13.**
- Checked against the PDF text (`pypdf` extraction of `paper2.pdf`):
  - Scenario 1 = per-network DNNs, cross-tested (Table 9);
  - Scenario 2 = the integrated stack MES-DNN0, tested per network (Table 10; average 96.67% / F1 95.36%);
  - Scenario 3 = new-network integration (Table 11).
- The paper's Fig. 2/3 captions carry swapped labels.
- `docs/BASELINE_ADAPTATIONS.md` has been corrected. Our setting is the two-network analogue of Scenario 2.
- Original note follows.

- The handover records the 96.67% / 95.36% result as Table 10 "scenario 2", and the new-network result as Table 11 "scenario 3".
- `docs/BASELINE_ADAPTATIONS.md` calls our all-networks-integrated setting "scenario 1" and calls "scenario 2" the unseen network.
- Which author table matches our setting must be confirmed against the PDF (Tables 10–11) before citing it in the comparison.
- The laptop has no PDF renderer, so this audit could not re-read it.

**OI-4. "Union" means two different sets.**
- ARR "all registered" has 23 features, including the D hypotheses.
- Ablation group U has 20 features: A ∪ B ∪ C.
- Phase IV text must keep the two apart.

**OI-5. Stale header.**
- `configs/protocol/ablation_groups_3a_r1.yaml` still says "PROPOSED … NOT approved, NOT run".
- Approval is in `docs/decision_log.md`. Documentation only.

## Reproducibility limits

**OI-6. R4a run folders: PARTLY PRESERVED (status 2026-11-13; see `PHASE3_FINAL_SIGNOFF.md` §2).**
- The original Colab VM expired, and its complete copy is gone.
- 22 of 70 run folders are complete on Drive and now also on the laptop (`results/runs/r4a_drive_copy_2026-11-13/`, archive SHA-256 `3f74ff75…f4e0`). Their predictions re-score identically to the pre-expiry record.
- For the other 48, the surviving evidence is the pre-expiry, hash-matched prediction check and the committed aggregate.
- Original note follows.

**OI-6 (original). R4a run folders are not in the repository.**
- The 70 R4a-ii run folders (about 1.2 GB) exist only on the Colab VM (`/content/r4a_local`) and on a Drive that is full (`cnet-r4a/`).
- Their predictions were re-scored read-only on the VM; the packaged JSON's SHA-256 was matched.
- If the Colab session ends before a download, independent re-scoring from predictions will require Drive access. Drive holds 63 complete copies plus those flushed later; the VM copy is the complete one.
- **Recommended:** download `/content/r4a_local/runs/*/predictions_test.csv.gz` (small), or free Drive space and copy the folder.

**OI-7. DCNN feature selection not re-run in this audit.**
- `shap` imports `numba`, which the laptop's application-control policy blocks.
- Selection integrity was checked through hashes and internal consistency only.
- Re-running is possible on Colab.

**OI-8. Monday FPR was not re-scored from model inputs in this audit.**
- The local torch import is blocked, and Monday predictions are not stored.
- The committed record passes every internal check: run IDs, n, FP/n, Clopper–Pearson, and zero threshold crossings at an alternative batch size, recorded at scoring time.

**OI-9. Laptop and GPU environments differ.**
- DCNN and MES-DNN ran on the laptop CPU (fingerprint `50d4a357…`).
- AE-XGBoost r1 and R4a ran on the Colab T4 (`be81b4d6…`).
- Cross-family numbers are never compared, so this is a provenance note only.

## Scientific limits (state in the paper; not fixable by more analysis within scope)

**OI-10. Convergence: r1 part RESOLVED 2026-11-13 by the D-021 cap-200 sensitivity.**
- Both capped r1 fits (D s0, s5) were retrained at cap 200 and early-stopped (epochs 124, 114). Errors went 8→9 and 14→13, so group D's mean contrast and its Holm decision are unchanged.
- R4a's 17 capped fits fall outside D-021, because D-024 did not extend it. They remain a declared limitation.
- Original note follows.

**OI-10 (original). Convergence.**
- 19 autoencoders reached the 100-epoch cap without early stopping: 2 in r1 (group D, seeds 0 and 5) and 17 in R4a (in the B, B-control and U views).
- Their test errors are within the normal range.
- It is unknown whether longer training would change any contrast. Not re-run (constraint).

**OI-11. R4a-ii floor effect.**
- Corrected-data models make 0–4 errors (SESOI = 22).
- The equivalence verdicts rule out large harms only.

**OI-12. R4a-i confounding.**
- The transfer contrast cannot separate defect correction from the other definition changes, segmentation and label windows.
- It is descriptive by protocol (D-024).

**OI-13. Inspected test population.**
- The r1 test population was inspected during design, so H1 is a pre-registered estimate on a known population.

**OI-14. Seeds as the experimental unit.**
- Inference is conditional on one test set per dataset; ten seeds give a minimum p of 2/1024.
- The original-vs-corrected Welch comparison treats seeds from different datasets as samples of one quantity. It is descriptive only.

**OI-15. SHAP scope.**
- SHAP covers one AE-XGBoost model, in float64.
- No SHAP was computed on r1 or R4a models, so no corrected-data ARR exists.

**OI-16. DCNN attention ablation and K = 30 not run.**
- Both are listed as future work in the draft.
