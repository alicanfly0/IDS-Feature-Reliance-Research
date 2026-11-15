# Changelog: final print-quality polish (2026-11-15)

**Inputs:** `CNET_PHASE4_REVISION2_INDEPENDENT_QA.md` and `CNET_PHASE4_REVISION2_CLAUDE_FINAL_POLISH.md`.

**Base:** the 15-page PDF from commit `1864341`.

**Scope:** every change below was made and checked in the compiled PDF.
- No experiment was rerun.
- No result, citation or reference changed.
- No AI-use declaration was added.

| Item | Edit made | File(s) | PDF page |
|---|---|---|---|
| F1 | Phone numbers removed from the author footnote; it now gives only the two e-mail addresses. The addresses are set with `\nolinkurl`, so they no longer break with a hyphen. | `main.tex` | 1 |
| F2 | All 14 table captions changed from small caps (lowercase letters printed at 6.4 pt) to upright 8 pt text, via `\caption{\upshape …}`. | `main.tex` | 3–15 |
| F2 | Fig. 1: band labels, the arrow label and the registry-line label raised from `\scriptsize` to `\footnotesize`. The literature-branch label now runs over two lines, and the "views to retrain" label was moved so it no longer touches an arrow. | `figures/diag_framework.tex` | 3 |
| F2 | Fig. 5: the R4a-i label raised from `\scriptsize` to `\footnotesize`. | `figures/diag_protocol.tex` | 7 |
| F2 | Table III: first column widened from 1.9 to 2.2 cm, so "AE-XGBoost" no longer wraps. | `main.tex` | 7 |
| F2 (result) | Text below 7.2 pt was 15% of characters on p. 12 and 10% on p. 9. It is now 1–4% on every page, and consists only of the IEEE running head (7 pt) and mathematical sub- and superscripts. | — | all |
| F3 | Fig. 4 source moved from the end of §III-B to after the opening paragraph of §III-E. The twin-exclusion paragraph (§III-D) now runs from the bottom of the left column to the top of the right column on p. 4, with no float between. Fig. 4 is on p. 5. | `main.tex` | 4–5 |
| F4 | No change to the declarations. The e-mail addresses, "no external funding", "no competing interests" and "available from the authors on request" are the statements the authors gave in chat on 2026-11-15. They are listed for re-confirmation in `FINAL_PRINT_QA.md`. | — | 1, 14 |
| P1 | Abstract tightened from 248 to 238 words, with no numerical finding or qualification removed. One paragraph; 6 keywords. | `main.tex` | 1 |
| P2 | No change to length. The paper stays at 15 pages, because the brief sets no hard cap and asks for legibility over page count. | — | — |
| P3 | Fig. 6: the shared legend is replaced by one legend per panel. Panel (a) reads "FP/FN, original" and "FP/FN, corrected"; panel (b) reads "false pos." and "false neg.". Panel (b) gains the x-axis label "test rows". | `figures/make_paper_figures.py`, `figures/fig_errors.pdf` | 8 |
| P4 | Three emphatic lines on R4a-i rephrased as observational: contribution 4 ("decides" became "is associated with successful … transfer"), §V-E ("decided the outcome" became "was associated with success") and §VIII-B ("found them decisive" became "their absence was associated with success"). | `main.tex` | 2, 10, 12 |
| P5 | Float proximity improved where it did not cost legibility. The page-4 reflow (F3) brings Fig. 4 next to Table II. Other tables stay at page tops, as is usual in IEEE layout. | `main.tex` | 4–5 |
| P6 | Rebuilt with Tectonic 0.17.0 (IEEEtran, BibTeX). No errors, overfull boxes, or undefined references or citations. Every page was rendered and inspected. All number tokens in the PDF were compared with the previous version; the only differences are the removed phone digits. | — | all |

**Counts after the edits:**
- 15 pages;
- 12 figures (5 diagrams);
- 14 tables;
- 1 algorithm;
- 9 numbered equations;
- 20 references.

These are unchanged from the previous version. Figure and table numbering is also unchanged.

## Repository link (2026-11-15, after publishing)

The code-availability statement now gives the public repository, https://github.com/alicanfly0/IDS-Feature-Reliance-Research, and notes that the datasets and model checkpoints are not included. The opening sentence of Appendix B now points to that repository instead of a local copy. No other text, number or figure changed. Pages 14 and 15; still 15 pages.
