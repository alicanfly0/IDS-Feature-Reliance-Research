# Build log: Phase IV paper

**Date:** 2026-11-15. **Machine:** the project laptop (Windows 11). **Engine:** Tectonic 0.17.0 (XeTeX-based), run from the repository copy at `tools/tectonic/tectonic.exe`. BibTeX 0.99d with `IEEEtran.bst` 1.14 was run automatically by Tectonic.

## Commands

From the repository root:

```
.\.venv\Scripts\python.exe paper\tables\make_tables.py
.\.venv\Scripts\python.exe paper\figures\make_paper_figures.py
Set-Location paper; ..\tools\tectonic\tectonic.exe --keep-logs main.tex
Copy-Item main.pdf CNET_PhaseIV_Research_Paper.pdf
```

The two Python scripts read only the verified Phase III records and rewrite `paper/tables/tab_*.tex` and `paper/figures/fig_*.pdf`. The five diagrams (`paper/figures/diag_*.tex`) are TikZ sources compiled with the paper.

## Result

| Item | Value |
|---|---|
| Output | `paper/CNET_PhaseIV_Research_Paper.pdf` (copy of `main.pdf`) |
| Pages | 13 (the end of the declarations, the references and a one-table appendix are on page 13) |
| Size | 293,718 bytes |
| SHA-256 | `ff3dde928fc9b8fd92e5aec484419bcc794c50957d3f836b1a60811f45a02b32` |
| Errors | none |
| Undefined references or citations | none |
| Overfull boxes | none |
| Fonts | all embedded (Nimbus Roman for text, Computer Modern for mathematics, STIX inside the matplotlib figures) |

## Remaining log messages and why they are harmless

Full log: `paper/main.log`; BibTeX log: `paper/main.blg`.

- `Fontconfig error: Cannot load default config file` (stderr): Tectonic looks for a system font configuration that Windows lacks. No system font is used, so the PDF is unaffected.
- `LaTeX Font Warning: Font shape TU/ptm/... undefined` (four lines, plus a summary line): raised while the class loads, before `fontenc` switches to T1. The body text is set in T1 Times (Nimbus Roman), which the font list of the PDF confirms.
- `Underfull \vbox ... while \output is active` (two): IEEEtran balances columns to the bottom of the page; two pages have slightly stretched vertical space.
- `Underfull \hbox` in `main.bbl` lines 64–68: the long URL of reference [8] breaks with loose spacing.

## History of fixes made during the build

- TikZ style name `out` clashed with a TikZ key; renamed to `concl` in `diag_framework.tex`.
- Overlapping labels and crossing lines in the AE-XGBoost and protocol diagrams; boxes re-placed, the comparison label moved into its own box, and the transfer label given a white background.
- Equations (3)–(4) and (9) exceeded the column width; the error-rate equation was split into two lines and the MCC denominator written with class-size symbols.
- Tables I, III, V, IX and XIII were up to 30 pt too wide; column widths and `\tabcolsep` reduced.
- Figure order: the three architecture diagrams were moved into Section III so that Figs. 1–5 are the framework, AE-XGBoost, DCNN, MES-DNN and protocol diagrams.
- The R4a figure legend covered a data point; it was moved to the middle right of panel (b).
- A hyperref bookmark warning for the math in a subsection title was removed with `\texorpdfstring`.
