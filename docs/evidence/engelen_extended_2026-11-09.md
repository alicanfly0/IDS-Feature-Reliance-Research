# Engelen extended documentation — evidence record, 2026-11-09

Primary source: https://intrusion-detection.distrinet-research.be/WTMC2021/extended_doc.html

Read on 2026-11-09. Locator: **CICIDS2017 and CICFlowMeter tool → Flow Construction → TCP flag count**.
This is HTML, so there is no PDF page number. The opening scope paragraph applies the findings to original CICIDS2017 CSVs.

The aggregate counters process only the first packet of a flow. The source dates the authors' fix to
15 October 2019. It separately identifies incorrect directional PSH/URG increments, without specifying
the same patch date or implementation details. Our schema mapping covers FIN, SYN, RST, PSH, ACK, URG,
CWE and ECE aggregate fields and Fwd/Bwd PSH and URG fields. `CWE Flag Count` is the literal original
schema spelling; the mapping to this field is by membership in the aggregate flag-count family,
not a claim that the page explicitly lists that spelling.

The Friday DDoS CSV belongs to this release. A binary count alone cannot demonstrate an erroneous
row: a flow with zero or one flag occurrence can be correct by coincidence. Actual row errors need
packet reconstruction. Zero-on-train fields remain recorded but carry no pilot attribution.

Additional relevant locator: **Duplicate Fwd Header Length**, documenting the repeated column.
**Absolute timestamp** explicitly excludes the original CICIDS2017 release from that separate bug;
Active/Idle features are therefore not promoted on that evidence.

SYN also retains the paper's TCP-appendix shortcut mechanism (paper7.pdf, physical p.5).
These mechanisms overlap in feature membership; ARR unions count SYN once. The existing Lanvin
packet-duplication evidence is unchanged. No other extension-page claim is generalized to Friday DDoS.
