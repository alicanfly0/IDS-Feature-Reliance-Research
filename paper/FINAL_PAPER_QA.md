# Final QA: Phase IV paper (revision for the updated rubric)

- **Paper:** "How Real Is 99% Accuracy? Auditing Feature Reliance in Network Intrusion Detection".
- **PDF:** `paper/CNET_PhaseIV_Research_Paper.pdf`, 15 pages. The SHA-256 is in `BUILD_LOG.md`.
- **Checked on:** 2026-11-15.
- **Corrections:** each change for M1–M9, with its page, is in `CHANGELOG_UPDATED_RUBRIC.md`.

## 1. Summary

| Check | Result |
|---|---|
| Compiles with bibliography | Yes. Tectonic 0.17.0 and IEEEtran.bst: no errors, no undefined references or citations, no overfull boxes. |
| Required parts in order | Title and authors, abstract, keywords, I–IX, declarations, references, then appendices A and B. |
| Abstract | One paragraph, 248 words. |
| Keywords | 6. |
| Figures | 12: five TikZ diagrams (Figs. 1–5) and seven vector plots (Figs. 6–12). |
| Tables | 14 (I–XIV): XIII and XIV are in the appendix. |
| Equations and algorithms | 9 numbered equations; one algorithm. |
| References | 20, all cited; no uncited or missing keys. |
| Placeholders | None in the PDF. |
| AI-use declaration | Not included. The updated rubric does not require one, and the authors asked that none appear. |
| Humanise checker (`--paper`) | 0 kill-list hits. Sentence-length SD 11.9. 5.16 characters per word. |
| Smallest type | **Figures:** 7 pt. **Tables:** `\footnotesize` (8 pt) or larger. **Body:** 10 pt, unchanged. |

## 2. Visual QA, page by page

Every page was rendered at 100 dpi with PyMuPDF and inspected. Diagrams and plots were also rendered on their own at 150–170 dpi.

| Page | Content | Finding |
|---|---|---|
| 1 | Title, authors, abstract, keywords, introduction | Clean. Two author footnotes (affiliation; e-mail and phone). |
| 2 | Contributions, related work A–E, hypotheses | Clean. The Geirhos et al. sentence is restored. |
| 3 | Table I, Fig. 1 (new framework), tracks, preprocessing | Fig. 1 legible at full width. The three strands are clearly separated, and the dashed registry line crosses nothing. |
| 4 | Figs. 2–4, partitioning, Eq. (1), groups | Labels at 8–9 pt. The Monday sentence continues within the page. |
| 5 | ARR, ablation estimand, statistics, corrected-data evaluation | Clean. Eqs. (2)–(8) fit the column. |
| 6 | Table II (both member sets), Fig. 5, Phase II changes, setup | Clean. |
| 7 | Tables III–IV, Algorithm 1, runs, metrics, Eq. (9) | Clean. |
| 8 | Figs. 6–7, results V-A to V-C | Fig. 7 prints the 0–87.9% range beside the mean. |
| 9 | Tables V–VIII, Fig. 8, results V-D and V-E | Clean. |
| 10 | Figs. 9–10, comparison with base papers | Fig. 9 separates own-base and ensemble rows. |
| 11 | Table IX, ablation VII-A to VII-D, discussion VIII-A | Author-reported values marked †. |
| 12 | Table X, Fig. 11, Table XI, discussion VIII-B and VIII-C | Interval levels: 99.5/99% (r1) and 98.33/96.67% (R4a). |
| 13 | Fig. 12, reproducibility, threats, conclusion | Clean. |
| 14 | Table XII, conclusion end, declarations, references | Clean. |
| 15 | Appendix A (Table XIII), Appendix B (Table XIV) | Clean. |

## 3. Scientific claim checks

| Item | How the paper handles it | Check |
|---|---|---|
| Same-model vs retrained | **DCNN:** same checkpoints, two populations. **MES-DNN:** separately retrained under two split protocols, with the confounds stated. | Pass |
| Fang protocol | Published MCC is tied to their Tables 3, 4 and 6. The protocol behind Table 6 is reported as not stated. No claim of the same split. | Pass |
| Corrected-task difficulty | No difficulty ranking. Both within-capture protocols give near-zero error on independently built populations. | Pass |
| Registry independence | Fig. 1 separates the branches. §VIII-E states when the flag-count family entered the registry. | Pass |
| Interval levels | r1: 99.5% difference, 99% TOST. R4a: 98.33% difference, 96.67% TOST. `make_tables.py` asserts both from the CSV. | Pass |
| ARR set (23) vs group U (20) | §III-F and the Fig. 10 legend. | Pass |
| float64 explanation vs float32 inference | §III-F. | Pass |
| R4a-i | Descriptive and "associated with"; confounders listed. All 110 models are shown in Fig. 5 and Table VI. | Pass |
| MES per network; Wardana Scenario 2; no unseen-network claim | Tables VIII and IX, §VI. | Pass |
| R4a preservation (22 of 70); 17 capped R4a fits | Stated once in §VIII-D (agreed paragraph) and Table XII. | Pass |
| Base papers are adaptations, not ranked | §I, §III-J, Table III, §VI. | Pass |
| Every number traced | `%` source comments in `main.tex`; `PAPER_CLAIM_EVIDENCE_MAP.md`. | Pass |

## 4. Author details and their sources

- **Names and affiliation:** CLAUDE.md and the Phase II title block. Roll numbers and section are omitted at the authors' request.
- **E-mail addresses and phone numbers:** supplied by the authors in chat on 2026-11-15. (The Phase II PDF lists university addresses of the form `{i232630, i232562}@isb.nu.edu.pk`. The paper uses the addresses the authors supplied.)
- **Funding and conflicts:** "no external funding" and "no competing interests". The authors confirmed both in chat on 2026-11-15.

## 5. Items left open

1. **Assignment file.** `CNET_PHASE4_UPDATED_ASSIGNMENT.txt` was not found on this machine. The rubric was taken from the review that quotes it. If the file adds anything that the review does not mention, it has not been checked.
2. **Reference [8].** Engelen et al.'s online extended documentation is attributed to the paper's authors.
3. **Reference [9].** Lanvin et al. is cited without an LNCS volume number, because two conflicting numbers were found earlier.
4. **Standard references.** Eight of these were not checked against local copies: [1], [2], [10], [11] and [14]–[17]. No new references were added; the review allowed this only for verified, relevant work, and none was needed.
5. **Page count.** The paper is 15 pages, against the brief's guidance of about 8–12. The brief says not to shrink type to reach a page target. The extra pages hold the requested legibility changes and the reproducibility appendix.
6. **Institutional AI-use policy.** None is applied. The updated rubric does not require a declaration. If a separate university or venue policy applies to the authors, that is theirs to check.
