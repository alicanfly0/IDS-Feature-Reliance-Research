# Changelog: revision for the updated Phase IV rubric (2026-11-15)

**Inputs:**
- `CNET_PHASE4_REVISED_CLAUDE_PROMPT.md`;
- `CNET_PHASE4_UPDATED_BRIEF_QA_REVIEW.md`;
- `CNET_PHASE4_PDF_QA_REVIEW.md`.

The assignment text itself (`CNET_PHASE4_UPDATED_ASSIGNMENT.txt`) was not on disk. This revision follows the rubric as the review quotes it.

**Result:** `paper/CNET_PhaseIV_Research_Paper.pdf`, 15 pages.

**What did not change:**
- No experiment was rerun.
- No result was changed.
- No AI-use declaration was added, because the updated rubric does not ask for one.

**Page count.** The paper is now 15 pages. It was 13 before the revision. The growth comes from:
- larger type in the figures and tables;
- Table II widened to full page width, with the corrected-capture memberships added;
- Appendix B, the reproducibility record.

Body type was not reduced.

## M1–M9

| ID | Defect | Change made | PDF page(s) |
|---|---|---|---|
| M1 | No contact e-mail; no funding or conflict statement | Added a second author footnote with both authors' e-mail addresses and phone numbers, as supplied by the authors. Added to the Declarations: "This work received no external funding" and "The authors declare no competing interests", both confirmed by the authors. Code availability now points to Appendix B. There is no AI-use declaration. | 1, 14 |
| M2 | DCNN and MES-DNN were both called "same-model" comparisons | **DCNN** is now described as the same five trained models scored on two populations. **MES-DNN** is described as separately retrained models under two split protocols; partitions, meta samples and the stacking step change with the split. Rewritten in the abstract, contribution 3, H4, §V-D, §VI (last paragraph, which replaces "model and data are held fixed"), §VIII-C and §IX. Fig. 4 and Fig. 9 captions and plot labels mark the two protocols as separately trained. | 1, 2, 4, 8–9, 10, 12–14 |
| M3 | Fang et al.'s MCC was described as coming from "the same official partition" | Claim removed. §VI now says that Fang et al. describe a stratified 70/30 split and report MCC 0.9355 in three places: Table 6 (ablation), Table 3 (held-out test with sizes close to the official partition) and Table 4 (nested five-fold CV). Their paper does not say which protocol produced Table 6. Checked against the paper's PDF (pp. 7, 13, 17, 18, 22). Table IX states the source protocol the same way. | 2, 10–11 |
| M4 | "The corrected task is at least as easy"; causal duplicate wording | Replaced with: both within-capture protocols give near-zero error on independently built populations, so the error counts do not rank task difficulty. The MES-DNN N2 drop is now described as sensitivity to the split protocol, measured together with retraining, not as an isolated duplicate effect. Abstract and conclusion use "duplicate handling changed the scores". | 1, 8, 9, 12, 14 |
| M5 | Fig. 1 suggested SHAP → registry → ablation | Fig. 1 redrawn with three strands. **Literature branch:** forensic literature → evidence registry → frozen groups and controls, marked as not SHAP-based and frozen before ablation training. **Explanation branch:** SHAP → ARR@K. These join only at stage 7, attribution vs intervention. The registry reaches ARR@K only as its feature set (dashed line). The caption explains the logic. A sentence in §VIII-E states honestly that the flag-count family entered the registry after an earlier SHAP pilot, that its members are the whole documented family, and that all groups were frozen before ablation training. | 3, 13 |
| M6 | Broken "Geirhos et al." sentence; proofreading | **Cause:** three source comments added in the previous build had absorbed the text after them. **Restored text:** the start of the Geirhos et al. sentence (p. 2), "Their extended documentation adds that the aggregate TCP …" (p. 1), "The pre-declared readings are …" (p. 5) and "Second, the sign-flip *p*-values are exact only …" (p. 13). Every inline comment was then checked for absorbed prose. **Other proofreading:** all 29 "et al." made non-breaking; one section heading and one figure caption corrected. | 1, 2, 5, 13 |
| M7 | Corrected R4a memberships and provenance underreported | Table II is now full width and lists both member sets: r1 and corrected R4a (A 9, B 8, U 20). New Appendix B with Table XIV covers: control-draw rule `RandomState(b + 100g + d)` with b = 3000 (r1) and b = 7000 (R4a); group order; control pools (46 and 52); proxy rule; split seed and fingerprints; test-population hashes; dataset archive hashes; environment fingerprint; code commits; group file paths; fit counts. Access is described as a local repository, available on request. No public URL is given. | 6, 14, 15 |
| M8 | Small labels in figures and tables | **Diagrams:** Figs. 2–5 redrawn at 8–9 pt, with wider boxes and a residual-skip label. Fig. 3 notes K = 22 against the 30 that the 95% rule would keep. Fig. 4 shows the split protocols as separately trained. **Plots:** Figs. 6–12 regenerated at 7.5–8.5 pt with larger markers. **Fig. 7** now shows each view's min–max range, and the full models' 0–87.9% range is printed beside the mean of 8.8%. **Fig. 8** caption gives class counts and "same five trained models". **Fig. 9** separates own-base and ensemble rows. **Fig. 10** legend reads "all registered (23; not group U)". **Figs. 11–12** carry a legend for seeds, mean, interval level and SESOI band. **Tables:** no table uses `\scriptsize` any more. Tables V and II are full width; others moved to `\footnotesize`, with extra row spacing in Tables I, III, IX and X. | 3–15 |
| M9 | Monday sentence split by a page of floats | The architecture diagrams and Table II are re-flowed. The paragraph containing the Monday exclusion (34,526 rows) now continues in the next column of the same page (p. 4), not after a full page of floats. | 4 |

## Updated 14-part rubric

| # | Component | Status | Where |
|---|---|---|---|
| 1 | Title, authors, affiliation, contact e-mail | Done | p. 1 (title, names, footnotes) |
| 2 | Abstract, one paragraph, 150–250 words, real measurements | Done, 248 words | p. 1 |
| 3 | Four to six keywords | Done, 6 | p. 1 |
| 4 | Introduction with gap, contributions, roadmap | Done | §I, pp. 1–2 |
| 5 | Thematic related work with comparison table | Done, themes A–E, Table I | §II, pp. 2–3 |
| 6 | Methodology: architecture, mathematics, objectives, pseudocode, Phase II evolution | Done; Figs. 1–5, Eqs. (1)–(9), Algorithm 1, Phase II paragraph | §III, pp. 3–7 |
| 7 | Experimental setup: data, splits, features, settings, environment, seeds | Done; Tables III–IV, Appendix B | §IV, pp. 6–7, 15 |
| 8 | Results with metrics, figures, variability | Done; Tables V–VIII, Figs. 6–10 | §V, pp. 7–10 |
| 9 | Comparison with base papers, with non-comparability warnings | Done; Table IX | §VI, pp. 10–11 |
| 10 | Ablation study with controls and statistical tests | Done; Tables X–XI, Figs. 11–12 | §VII, pp. 11–13 |
| 11 | Discussion with implications, strengths, limitations, threats | Done; Table XII | §VIII, pp. 11–14 |
| 12 | Conclusion and future work | Done | §IX, pp. 13–14 |
| 13 | Declarations: data, code, conflicts, funding; acknowledgement | Done | p. 14 |
| 14 | References | Done, 20, all cited | p. 14 |
| – | Optional appendix | Done: A (per-seed matrices), B (reproducibility) | p. 15 |
