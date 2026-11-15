# Final print QA: Phase IV paper

- **Paper:** "How Real Is 99% Accuracy? Auditing Feature Reliance in Network Intrusion Detection".
- **PDF:** `paper/CNET_PhaseIV_Research_Paper.pdf`, 312,078 bytes, SHA-256 `281936d72fdd06a3560c13a16a271abec2c284b3a73c2e4854cd8bbfe96dcecf`.
- **Checked:** 2026-11-15, after the edits in `CHANGELOG_FINAL.md`.

## Counts

| Item | Value |
|---|---|
| Pages | 15 (references on pp. 14–15; appendices A and B on p. 15) |
| Figures | 12: five TikZ diagrams (Figs. 1–5) and seven vector plots (Figs. 6–12) |
| Tables | 14 (I–XIV) |
| Equations; algorithms | 9 numbered; 1 |
| References | 20, all cited, none missing |
| Abstract | one paragraph, 238 words |
| Keywords | 6 |

## Build preflight

- **Engine:** Tectonic 0.17.0 (XeTeX), IEEEtran class, BibTeX with IEEEtran.bst 1.14.
- **Problems:** no errors, no undefined references or citations, no overfull boxes.
- **Fonts:** all embedded. Nimbus Roman for text, Computer Modern for mathematics, STIX inside the plots.
- **Remaining log messages, all harmless:**
  - TU/ptm font-shape notices while the class loads, before T1 is selected.
  - Three underfull vertical boxes from IEEEtran's bottom-aligned columns.
  - Loose spacing in the long URL of reference [8].

## Type size at print scale (PyMuPDF span sizes)

| Pages | Characters below 7.2 pt | What they are |
|---|---|---|
| 1–15 | 1–4% per page; earlier version up to 15% (p. 12) and 10% (p. 9) | the 7 pt IEEE running head, and mathematical sub- and superscripts |

**Floor sizes:**
- Table bodies and captions: 8 pt.
- Figure text: 7.5–9 pt.
- Body: 10 pt, unchanged.

## Page-by-page visual check (rendered at 100 dpi; plots also at 170 dpi)

| Page | Content | Result |
|---|---|---|
| 1 | Title, names, abstract, keywords, introduction; footnotes with affiliation and the two e-mail addresses | Clean. No phone numbers. The e-mail addresses are not hyphenated. |
| 2 | Contributions, related work A–E, hypotheses | Clean. The Geirhos et al. sentence is intact. |
| 3 | Table I, Fig. 1, §III-B, §III-C | Fig. 1 labels at about 7.6 pt after scaling. Branch labels clear of arrows. |
| 4 | Figs. 2–3, §III-D (twin exclusion) through §III-F | The twin-exclusion paragraph continues directly at the top of the right column. |
| 5 | Table II, Fig. 4, §III-G and §III-H | Clean. |
| 6 | Algorithm 1, §III-H to §IV-C | Clean. |
| 7 | Fig. 5, Table III, §IV-C to §V-A | "AE-XGBoost" fits on one line in Table III. |
| 8 | Table IV, Figs. 6–7, §V-A to §V-C | Fig. 6 legend per panel. Fig. 7 shows the 0–87.9% range. |
| 9 | Tables V–VII, Fig. 8, §V-D and §V-E | Clean. |
| 10 | Table VIII, Figs. 9–10, §V-E and §VI | Clean. |
| 11 | Table IX, §VI to §VIII-A | Author-reported values marked †. |
| 12 | Table X, Fig. 11, Table XI, §VIII-A and §VIII-B | Interval levels read 99.5/99% (r1) and 98.33/96.67% (R4a). |
| 13 | Fig. 12, §VIII-C to §IX | Clean. |
| 14 | Table XII, conclusion, declarations, references [1]–[17] | Clean. |
| 15 | References [18]–[20], Appendix A (Table XIII), Appendix B (Table XIV) | Clean. White space at the end of the appendix is normal. |

## Unchanged results

All number tokens extracted from this PDF were compared with the previous version (commit `1864341`). The only tokens that differ are the removed phone digits. Every metric, population size, interval, p-value and count is identical.

## F1–F4 and P1–P6

| Item | Status | Where |
|---|---|---|
| F1 phone numbers | Removed; e-mail addresses kept | p. 1 |
| F2 small tables and figure labels | Captions upright at 8 pt; Fig. 1 and Fig. 5 labels at footnote size; Table III widened | pp. 3–15 |
| F3 page-4 flow | Fig. 4 moved; paragraph contiguous | pp. 4–5 |
| F4 declarations | As given by the authors; listed below for re-confirmation | pp. 1, 14 |
| P1 abstract length | 238 words | p. 1 |
| P2 page count | Kept at 15; no hard cap in the brief | — |
| P3 Fig. 6 legend | One legend per panel | p. 8 |
| P4 observational wording | Three lines rephrased | pp. 2, 10, 12 |
| P5 float proximity | Improved on pp. 4–5 | pp. 4–5 |
| P6 preflight | Build, references, fonts, visual check and number comparison done | all |

The writing-style checker reports three "vague association" hits. All three are the intended observational wording ("associated with") required for the descriptive transfer result R4a-i, so they stay.

## For the authors to re-confirm before submission

These items were stated by the authors in chat. Nothing has been assumed beyond that.

1. **E-mail addresses:**
   - aliwaseemabbasi@gmail.com (A. W. Abbasi);
   - mudassir7323@gmail.com (M. Mudassir).
2. **Funding and conflicts:** "no external funding" and "no competing interests".
3. **Code availability:** "available from the authors on request". You must be able to share the local repository and its records if asked.
4. **Affiliation:** Department of Artificial Intelligence and Data Science, FAST-NUCES, Islamabad, as in the Phase II title block.
5. **AI-use policy:** none is included, following the updated assignment. If a separate university or venue policy applies, that is your call.
