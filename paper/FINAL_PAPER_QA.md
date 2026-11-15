# Final QA: Phase IV paper

**Paper:** "How Real Is 99% Accuracy? Auditing Feature Reliance in Network Intrusion Detection".
**PDF:** `paper/CNET_PhaseIV_Research_Paper.pdf`, 13 pages, SHA-256 `ff3dde928fc9b8fd92e5aec484419bcc794c50957d3f836b1a60811f45a02b32`.
**Checked on:** 2026-11-15.

## 1. Summary

| Check | Result |
|---|---|
| Compiles with bibliography (Tectonic 0.17.0, IEEEtran.bst) | yes; no errors, no undefined references, no overfull boxes (`BUILD_LOG.md`) |
| Sections in the required order | 1 title and authors, 2 abstract, 3 keywords, I introduction, II related work, III methodology, IV setup, V results, VI comparison with base papers, VII ablation, VIII discussion (with reproducibility and threats to validity), IX conclusion, declarations, references, appendix |
| Abstract | one paragraph, 246 words, real numbers only |
| Keywords | 6 |
| Figures | 12: five TikZ diagrams (Figs. 1–5) and seven result plots (Figs. 6–12) |
| Tables | 13 (Tables I–XIII, including one appendix table) |
| Numbered equations | 9; one algorithm |
| References | 20, all cited, none uncited |
| Placeholders | none in the PDF (`??` and `PENDING` absent); one bracketed author field (funding and competing interests) left on purpose |
| Humanise checker (`--paper`) | 0 kill-list hits; sentence-length SD 11.7 (target ≥ 8); 5.18 characters per word (target ≤ about 5.3) |

## 2. Visual QA, page by page

Every page was rendered at 100 dpi with PyMuPDF and inspected.

| Page | Content | Finding |
|---|---|---|
| 1 | Title, authors, abstract, keywords, introduction | clean; footnote with affiliation |
| 2 | Contributions, roadmap, related work A–E, start of methodology | clean |
| 3 | Table I, Fig. 1 (framework), preprocessing, partitioning, Eq. (1) | clean; Table I fits the text width after the column fix |
| 4 | Figs. 2–4 (architecture diagrams), Table II (groups) | labels readable at print size; no crossing lines |
| 5 | Algorithm 1, ARR and ablation equations, statistics, corrected-data evaluation | clean; equations within the column |
| 6 | Fig. 5 (protocol), Phase II changes, setup | slightly stretched vertical spacing in the right column (IEEEtran bottom alignment) |
| 7 | Tables III–V, Fig. 6, MCC equation, start of results | clean |
| 8 | Table VI, Fig. 7, Table VII, Fig. 8, results text | clean |
| 9 | Table VIII, Figs. 9–10, attribution, start of comparison | clean |
| 10 | Table IX, ablation study, start of discussion | author-reported values marked with † |
| 11 | Table X, Figs. 11–12 | interval labels read 99.5% / 99% (r1) and 98.33% / 96.67% (R4a) |
| 12 | Tables XI–XII, reproducibility, threats, conclusion, declarations | clean |
| 13 | Declarations (end), references, Appendix A with Table XIII | clean |

Figures are vector PDFs (plots) or TikZ (diagrams), set in grayscale; groups and series are told apart by marker shape and fill, so the paper prints correctly in black and white. Each plot shows population sizes in its title or caption, and the uncertainty is shown as intervals, ranges or per-seed points.

## 3. Part G claim validation

| Item | How the paper handles it | Check |
|---|---|---|
| r1 intervals | difference intervals 99.5%, TOST 99%; table header, Table X caption, Fig. 11 caption and §III-H agree; `make_tables.py` asserts the levels read from the CSV | pass |
| R4a intervals | difference 98.33%, TOST 96.67% (Table XI, Fig. 12, §III-H) | pass |
| ARR 23 vs group U 20 | §III-F states that "all registered" (23) is not group U (20) | pass |
| float64 explanation vs float32 inference | §III-F states that the explanations describe the float64 version of the composite model while the runner uses float32 inputs | pass |
| R4a-i limits | §III-I, §V-B and Table VI call it descriptive; "associated with" only; the confounders (definitions, encodings, segmentation, no test-side intervention) are listed | pass |
| Class-conditional recall | Table V gives DDoS and benign recall; Table VI gives DDoS recall and benign FPR; Table VII gives DoS recall, precision and Normal-class FPR | pass |
| Partial R4a preservation (22 of 70) | §VIII-D, using the agreed paragraph; Table XII; not repeated in abstract, introduction or conclusion | pass |
| 17 capped R4a fits | §VIII-D and Table XII; the r1 cap-200 check is reported in §VII-C (8→9, 14→13, same Holm decision) | pass |
| MES per network; Wardana scenario naming | Table VIII and Table IX per network; no pooled 85.5% / 0.715; Scenario 2 is the analogue, Scenario 3 has no counterpart, no unseen-network claim | pass |
| Accuracy vs generalisation | §VIII-A; Monday is described as a false-alarm test only; no claim of generalisation to unseen attacks or networks | pass |
| Equivalence wording | "equivalent within the pre-declared margin"; §VII-D explains the margin against baselines of about 6 and about 2 errors | pass |
| Adaptations, not reproductions | stated in §I, §III-J, Table III and §VI; Table IX is described as not a head-to-head benchmark | pass |
| No "dataset-specific shortcuts" claim | the phrase does not appear; the headline sentence from `CLAUDE.md` is used in the abstract, §I and §IX | pass |
| No full-reproducibility or causal-mechanism claim | §VIII-D limits reproducibility claims; §VII-B calls the original-vs-corrected difference observational | pass |

## 4. Evidence discipline

- Every number in `main.tex` has a `%` source comment on or beside its line, and `PAPER_CLAIM_EVIDENCE_MAP.md` lists each claim with its record.
- The result tables are generated by `paper/tables/make_tables.py` from the verification records; no table value was typed by hand.
- The figures are generated by `paper/figures/make_paper_figures.py` from the same records.
- No experiment was run, no SHAP was recomputed and no result was changed for this paper.

## 5. Items that need the authors' confirmation

1. **Author line.** The paper uses "Ali Waseem Abbasi (i23-2630)" and "Muhammad Mudassir (i23-2562)", as in `CLAUDE.md`. The Phase II title block reads "Ali Waseem (23i-2630)" and "Muhammad Mudassir (23i-2562)". Please confirm the name and roll-number format.
2. **Affiliation.** "Department of Artificial Intelligence and Data Science, FAST-NUCES, Islamabad, Pakistan (section DS-7A)", taken from the Phase II title block. Please confirm.
3. **Funding and competing interests.** Left as a bracketed placeholder in the Declarations; the paper does not assert either.
4. **Code availability.** The paper says the repository is local and that materials are "available from the authors on request". Please confirm that you are willing to share on request, or change the sentence.
5. **AI-assistance statement.** Please check that the wording matches what you want to declare.
6. **Reference [8]** (Engelen et al., extended online documentation). The page was read on 2026-11-09 (`docs/evidence/engelen_extended_2026-11-09.md`); its authorship is attributed to the paper's authors because it documents their corrected dataset. Please confirm, or cite it as an online resource without personal authors.
7. **Lanvin et al. [9].** The LNCS volume number is omitted because two different numbers (13723 and 13857) were found earlier; please confirm from the publisher page if the volume is wanted.
8. **Standard references** [1], [2], [10], [11], [14]–[17] were not checked against a local copy (marked "standard" in `references.bib`).
9. **Page count.** The PDF has 13 pages including references and the one-table appendix; the brief asked for about 8–12. Removing the appendix would not shorten it, because the references fill page 13. If 12 pages is a hard limit, the simplest cut is Fig. 8 (it repeats Table VII per seed) together with some tightening of §II.
