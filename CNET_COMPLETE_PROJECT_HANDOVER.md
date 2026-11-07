# CNET Phase III/IV — Complete Project Handover

**Project:** *How Real Is 99% Accuracy? Auditing Feature Reliance in Network Intrusion Detection Across Benchmark Datasets*

| | |
|---|---|
| Handover written | 2026-11-08, by the outgoing Claude Code session (account approaching its usage limit) |
| Repository state described | branch `main`, HEAD `fbd10cd4eb4f827d5d6946f480fb1c197263e259` ("Record D-015 Amendment 1 as authorized (Colab Free + private Drive)"); the following commit "Add the complete project handover for a new Claude Code session" adds only this file and the quickstart |
| Working tree | clean, except the intentionally untracked `MILESTONE_0_HANDOVER.md` (and Git-ignored review ZIPs, data, runs, venv) |
| Most recent completed milestone | **Milestone 2A** (artifact registry, original-feature SHAP pilot, ARR@K) plus its review package |
| Active task | **Registry correction for the TCP flag-count defect (ACK/PSH Flag Count): NOT STARTED in the repository** (§8) |

**Evidence labels used throughout:**

- **[REPO]** confirmed from the repository or local files during this handover.
- **[EARLIER]** reported by earlier handovers or conversation, not re-verified here.
- **[OPEN]** open, uncertain, unavailable or UNKNOWN.

---

## Table of contents

0. [START HERE — instructions for the new Claude Code account](#0-start-here--instructions-for-the-new-claude-code-account)
1. [Project identity and academic requirements](#1-project-identity-and-academic-requirements)
2. [Literature and research evidence](#2-literature-and-research-evidence)
3. [Repository and development environment](#3-repository-and-development-environment)
4. [Dataset provenance](#4-dataset-provenance)
5. [Research decision history (D-001 … D-019)](#5-research-decision-history-d-001--d-019)
6. [Milestone-by-milestone history](#6-milestone-by-milestone-history)
7. [Actual experimental results](#7-actual-experimental-results)
8. [CRITICAL: pending scientific correction (TCP flag-count defect)](#8-critical-pending-scientific-correction-tcp-flag-count-defect)
9. [Computational and financial constraints; Colab](#9-computational-and-financial-constraints-colab)
10. [Scientific integrity and engineering rules](#10-scientific-integrity-and-engineering-rules)
11. [Remaining work for Phase III (roadmap)](#11-remaining-work-for-phase-iii-roadmap)
12. [Phase IV paper strategy](#12-phase-iv-paper-strategy)
13. [Exact current project status](#13-exact-current-project-status)
14. [Ready-to-copy initial prompt for the new session](#14-ready-to-copy-initial-prompt-for-the-new-session)
15. [Risks, failure modes and lessons learned](#15-risks-failure-modes-and-lessons-learned)
16. [Quality assurance of this document](#16-quality-assurance-of-this-document)

---

## 0. START HERE — INSTRUCTIONS FOR THE NEW CLAUDE CODE ACCOUNT

You are taking over a research codebase that is **already far along**. Do not rebuild anything. Work in this order:

1. **Open the project root** (Windows): `C:\Users\aliwa\OneDrive\Desktop\FAST NUCES\semester 7\CNET\cnet project implementation`. All commands below run from there.
2. **Read this file first**, completely. It replaces the previous conversation, which you cannot see.
3. **Read** `README.md` and `docs/decision_log.md` (the decision log is the authority for every research decision).
4. **Read the latest reports:** `docs/MILESTONE_2A_REPORT.md`, `docs/DIAGNOSTIC_D008_SHORTCUTS.md`, `docs/MILESTONE_1A_HANDOVER.md`, `docs/COLAB_EXECUTION_PLAN.md`.
5. **Check Git:** `git status`, `git log --oneline -8`. Expected: HEAD = the commit "Add the complete project handover for a new Claude Code session" (parent `fbd10cd`), only `MILESTONE_0_HANDOVER.md` untracked. If HEAD has moved, someone continued the work: read the new commits before anything else.
6. **Look for partial changes** (`git diff`, `git status`). At handover there were none.
7. **Inspect only the relevant code.** For the active task: `configs/artifact_registry.yaml`, `src/audit/registry.py`, `src/audit/arr.py`, `src/audit/shap_explain.py`, `tests/test_audit.py`. Do not reread every file.
8. **Confirm local artifacts exist** (all Git-ignored):
   - `data/raw/cicids2017_original/MachineLearningCSV.zip` (and the other three datasets);
   - `results/runs/ae_xgb_d008_trackB-seed0-cpu-565a8b9e/` (baseline: checkpoints, predictions, latent codes, XGBoost model);
   - `results/runs/ae_xgb_d008_trackB_noDstPort-seed0-cpu-3054b399/` (ablation);
   - `results/shap/ae_xgb_d008_trackB-seed0-cpu-565a8b9e/variant-*/shap_values.npz` (6 SHAP arrays).
9. **Run the fast tests:** `.\run.cmd -m pytest -q` (about 30 s; expected **122 passed** with data present; real-data tests skip without data).
10. **Reconcile** what you find with §13 of this document. Report any difference to the user before acting.
11. **Preserve all artifacts.** Never overwrite or delete anything under `results/runs/`, `results/baselines/`, `results/ablations/`, `results/comparisons/`, `results/diagnostics/`, `results/shap/`, `results/splits/`.
12. **Continue the unfinished task in §8** (TCP flag-count registry correction), after showing the user a short plan.
13. **Do not restart** Milestone 0, 1A, 1B or 2A. Do not retrain the baseline or the ablation.
14. **Do not start expensive training or new experiments without the user's explicit approval.** Every milestone so far ended with "STOP"; the user approves each next step.
15. **Present a short verified status and the next action** to the user, then wait for approval.

**Working style the user expects** (from the whole history): honest reporting (say what was not verified), PKR 0 budget, no uploads or pushes without explicit permission, small purposeful commits, plain-language summaries, and the user can run everything themselves (`run.cmd`, documented commands). The user may be away and ask you to continue autonomously; then do only safe local work and document blockers.

---

## 1. Project identity and academic requirements

### 1.1 Identity

| Item | Value | Source |
|---|---|---|
| Title | *How Real Is 99% Accuracy? Auditing Feature Reliance in Network Intrusion Detection Across Benchmark Datasets* | `CNET_FULL_PAPER_AUDIT.md` header; README [REPO] |
| Course | Computer Networks (CNET), semester 7 | folder name; Phase II title [REPO] |
| University | FAST-NUCES, Islamabad, Pakistan; Department of Artificial Intelligence & Data Science, Section DS-7A | Phase II PDF title block [REPO] |
| Team | Ali Waseem (23i-2630) and Muhammad Mudassir (23i-2562) | Phase II PDF title block [REPO] |
| Roles | **UNKNOWN** — not established in any document. The user (Git user `ALICANFLY0`) drives the implementation with Claude Code. Decisions are recorded as "team" or "user" decisions in the decision log. | [OPEN] |

### 1.2 Phases

| Phase | What it was | Local evidence |
|---|---|---|
| Phase I | Literature review | `i232630_i232562_PHASE_I_CNET.pdf` and `Phase1_Literature_Review (1).docx` in the user's Downloads folder (not in the repo; not read for this handover) |
| Phase II | Submitted paper: *Computer Networks Project Phase II: Extended Literature Review and Explainable AI (XAI) Auditing Methodology for Network Intrusion Detection Systems* — extended literature review, refined research gap, 12-step methodology, architecture figure | `../project/i232630_i232562_PHASE_II_CNET.pdf` (also in Downloads) [REPO] |
| Phase III | Implementation and evaluation of the Phase II methodology (this repository) | this repo |
| Phase IV | Final research paper | README describes `paper/` as "IEEE LaTeX manuscript"; `paper/` holds only `.gitkeep` [REPO] |

- **No instructor feedback on Phase II was received** (user statement recorded in `CNET_FULL_PAPER_AUDIT.md` §F) [EARLIER].
- **The official Phase III and Phase IV assignment briefs, rubric and deadlines were NOT found** on this machine (searched the Downloads folder and the CNET folder). Requirements below come from the Phase II paper and the user's milestone briefs. **[OPEN] Ask the user for the Phase III/IV assignment text, rubric and deadlines.**

### 1.3 Source documents and their locations

| Document | Location | Role |
|---|---|---|
| Phase II submission | `../project/i232630_i232562_PHASE_II_CNET.pdf` (sibling folder `project` next to the repo) | The submitted methodology |
| Paper PDFs `paper1.pdf` … `paper10.pdf`, `CNETPAPER1–3.pdf` | `../project/` | Anchor papers (mapping in §2) |
| `CNET_FULL_PAPER_AUDIT.md` (7 Nov 2026) | user's Downloads folder (not in repo) | Critical full-text audit of the 10 papers vs Phase II; the main literature evidence register |
| `CNET_MILESTONE_0_INDEPENDENT_AUDIT.md` | Downloads | Independent review of Milestone 0 (verdict PASS WITH CONDITIONS, fixes F1–F5) |
| `CNET PROJECT.md`, `cnet-explanation-2026-09-22.md` | Downloads | Earlier chat exports (Gemini) about Phase I; **not authoritative** |
| Milestone 2A independent review (raised the ACK/PSH issue) | **NOT available locally.** Only the user's summary exists (§8) | [OPEN] |
| `MILESTONE_0_HANDOVER.md` | repo root, untracked on purpose | Milestone 0 report with addenda |
| `docs/*.md` | repo | Decision log, reports, Colab plan, checklist |

**Suggested action:** copy `CNET_FULL_PAPER_AUDIT.md`, `CNET_MILESTONE_0_INDEPENDENT_AUDIT.md` and the Milestone 2A review into the repo (e.g. `docs/external/`) once the user agrees, so the next session does not depend on the Downloads folder.

### 1.4 Research motivation and problem

Phase II abstract (paraphrased): DL-based NIDS report ≈99% accuracy on CICIDS2017 and UNSW-NB15, but forensic studies show these benchmarks contain packet-capture anomalies, flow-construction bugs and testbed biases. Classifiers may learn **shortcuts** (non-semantic artifacts) instead of attack behaviour, which then fails to transfer. Phase II proposes to turn SHAP from a passive visualization into an **active auditing tool**: cross-reference top-attributed features against a forensic artifact registry, quantify reliance (ARR@K), and ablate documented artifacts.

**Research questions as refined by the paper audit (§D1 of `CNET_FULL_PAPER_AUDIT.md`)** — these are the working RQs:

- **RQ1 — Attribution:** how much of top-K explanation magnitude goes to features the forensic literature links to known CICIDS2017 flow-construction / label / capture issues? (ARR@K; not a causal proof.)
- **RQ2 — Ablation:** what happens to in-domain and corrected-data evaluation after removing a documented suspect-feature group, compared with a **matched-size control group**? Retrained ablation and test-time masking are different analyses.
- **RQ3 — Transfer:** where shared input semantics and labels exist, do the changes reduce sensitivity to corrected capture pipelines or other environments?

**Hypotheses** (Phase II, to be treated as testable, not assumed): high benchmark scores are partly sustained by documented artifacts; removing them reduces in-domain scores and/or improves transfer. The audit warns: artifact removal may lower, keep or raise in-domain scores; any outcome is a result.

**Intended contributions** (Phase II Step 12, reframed): (1) an empirical quantification of shortcut reliance in reproduced baselines; (2) an evidence-tagged forensic artifact registry and a sanitized feature specification; (3) a reproducible auditing pipeline. Phase II's "no existing study has…" novelty claim must be softened to "the reviewed studies do not combine…" (audit §C).

### 1.5 Why 99%+ accuracy does not establish trustworthy NIDS

- **Shortcut learning:** a model can separate classes using features that are artifacts of how the dataset was recorded (e.g. in the Friday DDoS file 99.998% of DDoS flows go to port 80; the rule "port 80 → DDoS" alone gives test MCC 0.924 [REPO, diagnostics]).
- **Duplicates inflate scores:** random splits put identical vectors in train and test (93.5% of NF-UNSW-NB15-v2 test rows have a training twin under a random 70/15/15 split [REPO, D-007]).
- **Extraction defects:** CICFlowMeter errors (TCP appendices, duplicated packets, possibly flag counting) change feature values or create meaningless flows.
- **Single-capture evaluation:** train and test from one recording share session, host and timing properties; the score says nothing about other networks (Catillo: recall collapses to 0.00 for some attack/defence combinations on USB-IDS-1).
- Our own baseline reaches test F1 0.99987 under a duplicate-aware split — which shows that duplicates alone do not explain the score, **not** that the model learned attack behaviour.

### 1.6 Key research distinctions (use these terms consistently)

| Concept | Meaning in this project | Example |
|---|---|---|
| Genuine attack-characteristic learning | Model uses properties the attack necessarily produces in any network | packet rates/sizes that the attack tool generates — only claimable after transfer tests |
| Dataset-specific shortcut | A correct feature value that happens to separate classes only in this recording | `Destination Port` = 80 for DDoS in the Friday capture |
| Metadata leakage | Identifiers or recording metadata that encode the label (IPs, timestamps, Flow ID, possibly ports) | MachineLearningCVE already drops IPs/Flow ID; `Destination Port` remains |
| Flow-generation / extraction defect | The extractor computes wrong values or wrong flows | Engelen TCP appendices; Lanvin duplicated packets; reported flag-count defect (§8) |
| Duplicate contamination | Identical feature vectors in train and evaluation partitions | solved here by content-group splitting (track B) |
| Session-specific correlation | Features tied to one session/host/time window that leak across a random split | not yet assessed (needs `TrafficLabelling` keys; §11) |
| Generalization across recordings/datasets | Performance on another capture or dataset with aligned features and labels | R4a (original → Engelen-corrected), R4b (cross-dataset) — not yet run |

### 1.7 Phase II methodology as submitted (preserve exactly) and approved deviations

Phase II's 12 steps (from the PDF):

1. Input: flow vectors xᵢ ∈ ℝᵈ, d ∈ [43, 78], binary and multi-class labels.
2. Data: CICIDS2017 original + corrected (Engelen, Lanvin); UNSW-NB15; NF-UNSW-NB15-v2.
3. Preprocessing: purge NaN/Infinity/negative duration; strip identifiers and constant columns (Phase II names Fwd/Bwd URG Flags); one-hot; min–max.
4. Forensic artifact registry A: **A_meta** = Destination Port, Init_Win_bytes_forward, Init_Win_bytes_backward; **A_bug** = min_seg_size_forward, Fwd Header Len, SYN Flag Count, Bwd Pkt Len Mean; **A_dup** = Flow IAT Min, Flow Packets/s, Bwd Packets/s.
5. SHAP values φⱼ, global importance Iⱼ = mean |φⱼ|, ARR@K = Σ_{j∈TopK∩A} Iⱼ / Σ_{j∈TopK} Iⱼ.
6. Baselines: AE-XGBoost (TreeExplainer), MES-DNN (DeepExplainer), DCNN + self-attention (DeepExplainer/KernelExplainer).
7. Stratified 70/15/15; regimes **R1** full features, **R2** F \ A_meta, **R3** F \ (A_meta ∪ A_bug), **R4** cross-dataset / corrected-PCAP transfer.
8. Metrics: Precision, Recall, Macro-F1, AUROC, MCC; E-XAI descriptive accuracy, sparsity, stability.
9. Wilcoxon signed-rank over 10-fold CV, p < 0.05.
10. Ablation k ∈ {0, 2, 5, 10, 20}: top-k artifact vs top-k non-artifact, retrained from scratch.
11. Error analysis on R3/R4 (Attempted attacks, TCP appendices, slow DoS).
12. Outputs: quantification, sanitized feature spec, reproducible benchmark.

**Deviations already recorded** (cumulative; details in the decision log):

| Phase II | Now | Decision |
|---|---|---|
| d ∈ [43, 78] shared space | per-dataset dimensions (78 / 77 / 42–47 / 39) | D-006 |
| "43-feature" NetFlow input | 39 model inputs (43 features, 40 columns with label) | D-001 APPROVED |
| [1] used 2.83M flows | [1] used the 225,745-row Friday DDoS file | D-008 |
| Fwd URG Flags constant everywhere | constant in the DDoS file only, not across CICIDS2017 | D-011 |
| stratified random 70/15/15 | duplicate-aware group split (track B) + paper-comparable track A | D-007 PARTIALLY APPROVED |
| Wilcoxon over 10 folds | seed-level and cluster-bootstrap comparisons (proposal) | D-007 |
| R4 single regime | R4a corrected-capture / R4b cross-dataset | D-005, D-006 |
| AE-XGBoost via TreeExplainer | composite raw → AE → XGBoost explanation (permutation SHAP) | D-002, D-019 |
| AE input 120 | 68 (78 − 10 constant-on-train) | D-003 APPROVED |
| Registry A as fact | evidence-tagged registry; Destination Port & Init_Win_bytes_backward are hypotheses | D-012 |
| Ablation without controls | size-matched control groups recommended (audit) | not yet decided |

---

## 2. Literature and research evidence

**Authority:** `CNET_FULL_PAPER_AUDIT.md` (Downloads) is the full-text audit; page numbers are **physical PDF pages**. Below is a condensed but complete record. Numbers are **author-reported** unless marked "ours".

### 2.1 Inventory

| Phase II ref | Local file(s) in `../project/` | Paper | Disposition |
|---|---|---|---|
| [1] | `CNETPAPER1.pdf` = `paper1.pdf` | Nezhadsistani et al. 2026, AE–XGBoost | Core baseline |
| [2] | `CNETPAPER2.pdf` = `paper2.pdf` | Wardana et al. 2026, SNI-CIDS / MES-DNN | Core baseline |
| [3] | `CNETPAPER3.pdf` = `paper3.pdf` | Fang et al. 2026, SHAP + DCNN + self-attention | Core baseline |
| [4] | **not available** | Bilal et al. 2026 | Unverified (D-013) |
| [5] | **not available** | Wang et al. 2025 | Unverified (D-013) |
| [6] | **not available** | Ebrahimi et al. 2025 | Unverified (D-013) |
| [7] | `paper4.pdf` | Kalasampath et al. 2025, XAI literature review | Background only |
| [8] | `paper5.pdf` | Senevirathna et al., XAI for 5G/B5G survey (arXiv v3 copy) | Background only |
| [9] | `paper6.pdf` | Arreche et al. 2024, E-XAI | Core XAI-evaluation method |
| [10] | `paper7.pdf` | Engelen et al. 2021, CICIDS2017 troubleshooting | Essential forensic evidence |
| [11] | `paper8.pdf` | Lanvin et al. 2022/2023, CICIDS2017 errors | Essential forensic evidence |
| [12] | `paper9.pdf` | Catillo et al. 2023, transferability | Essential generalization evidence |
| [13] | `paper10.pdf` | Lundberg & Lee 2017, SHAP | Essential theory |

`paper1/2/3.pdf` have identical text to `CNETPAPER1/2/3.pdf` (audit dedup check): 13 files = 10 unique papers.

### 2.2 Per-paper records

#### [1] Nezhadsistani, Tajgardan, Rabbani, Niu, Stiller — AE-XGBoost
- **Citation:** "Design and evaluation of a robust and explainable intrusion detection framework for 5G/B5G networks", *Computer Networks* 278 (2026) 112100, doi 10.1016/j.comnet.2026.112100 (DOI from the Gemini notes; article number confirmed by the audit).
- **Purpose:** robust, explainable IDS for 5G/B5G; AE compression + latent Gaussian minority augmentation + XGBoost + SHAP.
- **Data:** CIC-IDS2017 **DDoS subset, 225,745 samples, 78 features + label**; 5G-NIDD; a 5G dataset (686,021 samples, 56 features). AE input 120 incl. one-hot (composition across datasets not shown).
- **Model:** AE 120→80→40→80→120, ReLU, Adam 1e-3, batch 256, ~50–100 epochs with early stopping (§4.2.1 p.5); XGBoost lr range 0.01–0.30, max depth 6, L1/L2/subsample/colsample tuned (Table 5); latent augmentation Eq. 4 for minority attacks (σ, count, acceptance unstated).
- **Protocol:** 5-fold CV (Table 7), also synthetic-sample testing (Table 6).
- **Reported:** Table 6 p.7: CIC-IDS2017 original F1 **0.9993**; 5G-NIDD 0.9836; 5G dataset 0.9695; leave-one-dataset-out acc 0.9386, precision 0.8810, recall 0.9386, F1 0.9089. Table 7 p.7 gives five fold F1 values + mean/STD/variance (**Phase II's "no fold variance" claim is false**).
- **XAI:** Fig. 5 pp.9–10: `min_seg_size_forward` appears in a **local** explanation; the **global** CICIDS plot is led by **ACK Flag Count** and Min Packet Length. XGBoost sees 40 latent codes, yet SHAP plots show raw feature names; the propagation is not explained (methodological ambiguity, not misconduct).
- **Our use:** baseline 1, documented adaptation (D-003, D-017).
- **Do NOT attribute:** "min_seg_size_forward dominates globally"; "performance degraded substantially" (the paper calls LODO F1 0.9089 promising); 2.83M flows / 15 classes.
- **Our result vs theirs:** our test F1 0.999870 (track B, one seed, Friday file only) is **not comparable** to their 0.9993 (joint training with two 5G datasets, 5-fold CV).

#### [2] Wardana, Kołaczek, Warzyński, Sukarno, Adiwijaya — SNI-CIDS / MES-DNN
- **Citation:** *Future Generation Computer Systems* 177 (2026) 108252.
- **Purpose:** collaborative detection across five heterogeneous networks, including integrating a new network.
- **Data:** NF-UNSW-NB15-v2, NF-ToN-IoT-v2, NF-BoT-IoT-v2, NF-CSE-CIC-IDS2018-v2, NF-UQ-NIDS-v2 (binary). Table 3 counts are below official totals (e.g. N1 1,986,745 vs 2,390,275); no filtering described.
- **Features:** §4 p.5: 45 fields, 40 used; Table 6 p.9: input **39** (resolved D-001: 43 features − 4 IP/port fields).
- **Model:** five base DNNs (hidden 9-7-5-3, ReLU), frozen; meta-model 1 hidden layer of 10 (ReLU), sigmoid; Adam, BCE, batch 1000, 10 epochs (Tables 6–7; Algorithm 1 p.10).
- **Protocol:** 70/30; 10% of train as meta-sample; 10% of test as validation.
- **Reported:** Table 10 p.12 (scenario 2): acc 96.67%, recall 95.17%, precision 95.82%, F1 95.36% (**abstract swaps recall/precision**). Table 11 (scenario 3, new network): acc 89.23%, recall 86.55%, precision 71.52%, F1 71.09%; MES-DNN2 on TS2 recall 4.92%. Averages over scenarios, not pooled (so "28.48% FDR" is only the complement of mean precision).
- **Our use:** baseline 2 — **not implemented** (D-010 scale open).

#### [3] Fang, Xuan, Ding — SHAP + DCNN + self-attention
- **Citation:** *PLOS One* 21(8) e0356069 (2026).
- **Pipeline:** LightGBM + TreeSHAP on training data selects 22 of 47 features (95% cumulative mean |SHAP|; Fig. 2 p.9), then DCNN with 4-head self-attention. **The SHAP stage explains LightGBM, not the DCNN.**
- **Preprocessing:** median imputation, "Unknown" categories, IQR + 1st/99th winsorizing, min–max fit on train, one-hot.
- **Settings:** Adam lr 0.0005, batch 128, 50 epochs, L2 0.001, patience 10, 4 heads, BCE, seed 42, 20% validation (Table 5 p.18).
- **Data:** UNSW-NB15 Normal vs DoS: 92,998 normal / 16,353 DoS; train 55,998 + 12,264, test 37,000 + 4,089 (p.22) — **not** the stated stratified 70/30; matches the **official partition** except 2 train-Normal rows (D-009, measured).
- **Reported:** AUROC 0.999, AUPRC 0.992; Table 6 p.18 MCC 0.9015 (DCNN) → 0.9275 (+SHAP) → 0.9235 (+SA) → 0.9355 (both); abstract's "6.1%/3.9%" conflicts with §3.4 (2.6 pp MCC, 3.8 pp precision). Reports 5-fold CV, CI plots (Fig. 9 p.22), Wilcoxon p<0.01 (p.24).
- **Polarity:** normal = positive class (p.14).
- **Code:** `github.com/ZHF123775838/WSN-DCNN-SHAP` claimed; **not accessed**.
- **Our use:** baseline 3 — **not implemented** (D-009 open).

#### [7] Kalasampath et al. — XAI literature review
*IEEE Access* 13 (2025), doi 10.1109/ACCESS.2025.3546681 (Phase II lists pp. 41725–41753). Survey (PRISMA-inspired, 121 candidate papers). Background only; no NIDS experiment, no artifact evidence.

#### [8] Senevirathna et al. — XAI for 5G/B5G security survey
Local copy is **arXiv:2204.12822v3 (30 Sep 2024)**; Phase II cites the IEEE COMST 2025 version (vol. 27(2), pp. 941–973) — version difference unverified. Conceptual trade-offs and explanation attacks; background only.

#### [9] Arreche, Guntur, Roberts, Abdallah — E-XAI
*IEEE Access* 12 (2024) 23954–23988, doi 10.1109/ACCESS.2024.3365140. SHAP vs LIME over 7 models and 3 datasets (incl. CICIDS2017); six metrics: descriptive accuracy (k = 0,5,10,25,50,70 removals, p.8), sparsity, stability (top-k intersection / k across runs), efficiency, robustness, completeness. Evaluates **explanation quality**, not feature legitimacy. Our use: metric design for stability / descriptive accuracy (adapt k grid; do not copy blindly).

#### [10] Engelen, Rimmer, Joosen — CICIDS2017 troubleshooting
- **Citation:** 2021 IEEE Security and Privacy Workshops (SPW), pp. 7–12, doi 10.1109/SPW53761.2021.00009 (manifest).
- **Findings (paper7.pdf):** CICFlowMeter ends TCP flows at the first FIN → **TCP appendices = 25.9%** of flows (p.3); RST handling; direction reversals; over-broad labels; payload-less attempted attacks (p.3); Hulk misconfiguration. Corrected extractor and re-labelled data with `- Attempted` classes; RF 75/25.
- **Feature evidence (§IV-B.1 p.5):** RF uses `Fwd Header Len`, `Total Fwd Pkt`, `Min Seg Size Fwd`, `Init Win bytes Fwd` to separate appendix subcategories; `SYN Flag Count` and `Bwd Pkt Len Mean` separate appendices from regular flows. These are **shortcut indicators**, not universally invalid features.
- **§III-D p.4:** feature extraction discussion; leaves Destination Port's status open (registry R01 cites this).
- **Extended documentation** `https://intrusion-detection.distrinet-research.be/WTMC2021/extended_doc.html` reportedly describes a **TCP flag-count defect** (§8). **Not read by us.** The 6-page paper text does not mention ACK/PSH counting (grep of the extracted pages found only FIN/SYN mentions) [REPO-level check of extracted text, earlier session].
- **Our use:** registry R02, R04–R08, F01–F03, L01, I01; corrected dataset (WTMC2021) downloaded for R4a.

#### [11] Lanvin, Gimenez, Han, Majorczyk, Mé, Totel — CICIDS2017 errors
- **Citation:** CRiSIS 2022, Springer LNCS 2023, doi 10.1007/978-3-031-31108-6_2. **Volume discrepancy:** Phase II says LNCS 13723; the registry/audit say LNCS 13857 — verify before Phase IV.
- **Findings (paper8.pdf):** misordered packets reverse direction (§3.1 pp.6–7); **duplicated packets ≈5%, per day 3.48–5.96% (Table 5, p.9)**; unlabelled port scan during Thursday infiltration (§3.4 p.9). Variants R/P/D (Table 7 p.13); ~20 pp recall drop is specific to adding port-scan labels in their evaluation. Duplicated packets affect **Flow IAT Min/Mean, Flow Packets/s, Bwd Packets/s** (§4.2 Q3 p.15).
- **Fixes:** `gitlab.inria.fr/mlanvin/crisis2022` (not accessed; Lanvin data not downloaded).
- **Do NOT attribute:** "duplication inflates recall by 20%" as a general effect; Phase II's "4.5%" duplication figure (paper reports ~5%, 3.48–5.96%).
- **Our use:** registry R09–R12 (direct extraction error), F03, F04, L02.

#### [12] Catillo, Del Vecchio, Pecchia, Villano — transferability
*Software Quality Journal* 31 (2023), doi 10.1007/s11219-022-09587-0 (local file = accepted manuscript). Trains on CICIDS2017, tests on USB-IDS-1 (Hulk, TCP flood, slowloris, slowhttptest × no defence / mod_evasive / mod_reqtimeout). Table 2 p.24: e.g. Hulk + mod_evasive recall DT 0.06, RF **0.00**, DNN 0.05; TCP flood ≈0.00 for all. Zero recall is for **specific** model/attack/defence cells. Does not attribute failure to any feature. USB-IDS-1 not acquired.

#### [13] Lundberg & Lee — SHAP
NeurIPS 2017. Additive feature attribution; local accuracy, missingness, consistency; Kernel SHAP, Deep SHAP. Attributions depend on the background/masking model; they explain **the model**, not the data's validity. ARR@K is our post-processing indicator, not part of SHAP theory.

#### [4]–[6] Unavailable
Bilal 2026 (federated IDS, "30 pp Macro-F1 drop"), Wang 2025 (claim that SHAP on UNSW-NB15 flagged `Init_Win_bytes` — a CICFlowMeter name; UNSW uses `swin/dwin`), Ebrahimi 2025 ("99.47% F1"): **uncertified (D-013)**. Obtain PDFs or soften/drop in Phase IV.

### 2.3 Critical corrections to Phase II (from the audit, still binding)

Wardana 39 inputs not 43; Fang's TreeSHAP is on LightGBM; AE-XGB raw-name SHAP needs the composite explanation; global vs local `min_seg_size_forward`; Fang has CV/CIs/Wilcoxon; Fang abstract vs Table 6; Fang split counts; Wardana recall/precision swap; artifact names are dataset/mechanism specific; R4 split into two questions; random 70/15/15 leaks; "no study has…" too strong; Lanvin 20% is specific; Wilcoxon over dependent folds is invalid; ablation need not reduce F1; E-XAI is not an artifact registry.

---

## 3. Repository and development environment

### 3.1 Machine and environment [REPO]

| Item | Value |
|---|---|
| Project root | `C:\Users\aliwa\OneDrive\Desktop\FAST NUCES\semester 7\CNET\cnet project implementation` (under OneDrive\Desktop; OneDrive sync depends on user settings) |
| OS / hardware | Windows 11 Pro; Dell Latitude 7430, Intel i7-1265U, 16 GB RAM, Intel Iris Xe; **no CUDA** |
| Python | CPython 3.11.9 (python.org per-user install); **venv at `.venv/`** in the project (Git-ignored) |
| Running | `.\run.cmd -m <module>` uses `.venv\Scripts\python.exe` without activation (PowerShell or cmd) |
| Setup | `powershell -ExecutionPolicy Bypass -File scripts\setup_env.ps1` (creates/reuses `.venv`, installs `requirements.txt` + editable package, runs tests) |
| Pinned dependencies (`requirements.txt`) | numpy 1.26.4, pandas 2.3.3, scikit-learn 1.9.0, PyYAML 6.0.3, pytest 9.1.1, torch 2.15.0 (CPU wheel on Windows), xgboost 3.2.0, shap 0.49.1 (newest release supporting numpy<2), matplotlib 3.11.2 |
| Full freeze | inside `MILESTONE_2A_REVIEW.zip` → `review/pip_freeze.txt` (42 lines) |
| Colab note | do **not** install `requirements.txt` on Colab (numpy downgrade breaks preinstalled torch); the notebook installs only what is missing |
| Shell quirks | The Claude Code Bash tool is Git Bash; PowerShell 5.1 also available. Heredocs containing apostrophes broke once in this session; prefer writing scripts with the Write tool |

### 3.2 Git [REPO]

- Branch `main` only. **No remote configured; nothing has ever been pushed.** No GitHub repo exists for this project. `gh` CLI is not installed.
- Commit attribution used: `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>` at the end of messages.
- Full history (oldest last):

| Hash | Date | Message |
|---|---|---|
| `fbd10cd` | 2026-11-08 | Record D-015 Amendment 1 as authorized (Colab Free + private Drive) |
| `93c1a83` | 2026-11-08 | Record the SHAP/ARR@K pilot and document D-002, D-012 and D-019 |
| `ca8e51b` | 2026-11-08 | Milestone 2A: original-feature SHAP for the AE-XGBoost baseline |
| `29c9b52` | 2026-11-08 | Milestone 2A: forensic artifact registry and ARR@K |
| `f759499` | 2026-11-08 | Record and verify the D-018 Destination Port ablation (seed 0, CPU) |
| `fd65ad5` | 2026-11-08 | Milestone 1B: shortcut diagnostics and Destination Port ablation design (not run) |
| `2fd0a57` | 2026-11-08 | Fix Colab notebook install order and dataset location |
| `c96aec6` | 2026-11-08 | Record the first AE-XGBoost CPU baseline run (made at 6fed9b0) |
| `6fed9b0` | 2026-11-08 | Milestone 1A: AE-XGBoost baseline and Colab-first workflow (not yet trained) |
| `98620bd` | 2026-11-08 | Finalize Milestone 0: audit fixes, approved decisions, Colab preparation |
| `4d00314` | 2026-11-07 | Complete Milestone 0: acquire and inspect Engelen's corrected CICIDS2017 |
| `bf0efed` | 2026-11-07 | Acquire, verify and inspect CICIDS2017, UNSW-NB15 and NF-UNSW-NB15-v2 |
| `366f144` | 2026-11-07 | Keep the environment and data inside the project folder |
| `174aed7` | 2026-11-07 | Set up a reproducible Python environment for running without assistance |
| `bb69358` | 2026-11-07 | Milestone 0: repository skeleton, dataset manifest and leakage-safe data tooling |

### 3.3 Ignore rules (`.gitignore`) [REPO]

Ignored: `data/raw/*`, `data/processed/*` (except `.gitkeep`), `*.csv`, `*.parquet`, `*.pcap*`, `*.zip`, `*.tar.gz`, `*.7z`, `*.pt/.pth/.ckpt/.joblib/.pkl/.npy/.npz`, `results/runs/`, `results/cache/`, `results/splits/`, `results/benchmarks/`, Python caches, `.venv/`, `.env`, notebook checkpoints, editor/OS files, LaTeX build files. Exception: `results/baselines/…/confusion_matrices.csv` and the D-018 `paired_test.csv.gz` were **force-added** deliberately. `.gitattributes`: `* text=auto`; `.cmd/.bat/.ps1` CRLF.

### 3.4 Files that must never be overwritten or deleted

- `data/raw/**` (verified datasets; re-download needs CIC registration).
- `results/runs/ae_xgb_d008_trackB-seed0-cpu-565a8b9e/` and `results/runs/ae_xgb_d008_trackB_noDstPort-seed0-cpu-3054b399/` (trained models; sha256 of 32 artifacts recorded in `results/comparisons/…verification.json`; `tests/test_d018_records.py::test_run_artifacts_unchanged` checks them).
- `results/splits/*.json` (pinned split records).
- `results/baselines/`, `results/ablations/`, `results/comparisons/`, `results/diagnostics/`, `results/shap/` (committed results; SHAP `variant-*` folders are a cache — **never recompute in place**).
- `MILESTONE_0_HANDOVER.md` (untracked by the user's choice; do not commit, do not delete).
- `MILESTONE_0_REVIEW.zip`, `MILESTONE_1A_REVIEW.zip`, `MILESTONE_2A_REVIEW.zip` (review packages; Git-ignored).

### 3.5 Repository tree (important parts)

```
cnet project implementation/
├── README.md                     overview, setup, usage, status
├── CNET_COMPLETE_PROJECT_HANDOVER.md   this file
├── MILESTONE_0_HANDOVER.md       untracked on purpose (M0 report + addenda)
├── MILESTONE_{0,1A,2A}_REVIEW.zip  review packages (ignored)
├── run.cmd                       runs .venv python without activation
├── pyproject.toml                package "cnet-xai-audit"; pytest config (testpaths tests, pythonpath .)
├── requirements.txt              pinned versions (above)
├── configs/
│   ├── base.yaml                 project defaults (paths, seed, split/preprocessing policy), read by src/config.py
│   ├── datasets.yaml             acquisition manifest: sources, sizes, sha256, MD5/SHA-1, licences, measured facts
│   ├── artifact_registry.yaml    forensic artifact registry (Milestone 2A)
│   └── experiments/
│       ├── ae_xgb_d008_trackB.yaml          baseline (device: cuda by default → use --device cpu locally)
│       ├── ae_xgb_d008_trackB_noDstPort.yaml  D-018 ablation (device: cpu; extra_drop_cols; exclude_eval_twins)
│       ├── ae_xgb_d008_smoke.yaml           tiny smoke config (results meaningless)
│       └── smoke_unsw_official.yaml         UNSW plumbing check (not a baseline)
├── src/
│   ├── config.py      load_config (base + experiment overlay), validate_config, make_preprocessor, check_no_leaky_outputs, write_run_record, excluded_columns
│   ├── env.py         select_device, set_seeds, snapshot (Python/OS/CPU/RAM/GPU/packages/Git/dataset hashes), in_colab; CLI
│   ├── data/
│   │   ├── manifest.py    load/validate manifest, local_status, sha256; CLI (--hash)
│   │   ├── acquire.py     download/verify/extract per manifest (official sources only; safe zip extraction; MD5/sha256)
│   │   ├── load.py        read_flow_csv (strips padded headers, BOM, duplicate column naming), read_names_file
│   │   ├── inspection.py  schema/labels/missing/infinite/duplicates/leakage-candidate report; CLI
│   │   ├── preprocess.py  invalid_row_mask (D-011 rules), TrainOnlyPreprocessor (train-only median/constant/min-max/one-hot; rejects undeclared text)
│   │   ├── split.py       Split, stratified/group/temporal/predefined splits, content_groups, conflicting_groups, partition_overlap, exclude_eval_twins, cross_split_duplicates, save_split/load_split (record digest)
│   │   └── ddos.py        D-008 scope: verified_csv (sha256 + MD5 + member CRC), prepare (D-011 rules, conflicts, track-B split), load, subsample
│   ├── models/
│   │   ├── autoencoder.py AutoEncoder, build, train (resumable per-epoch checkpoints, RNG state, early stopping, best weights), encode, reconstruction_mse
│   │   ├── augment.py     latent Gaussian augmentation (paper Eq. 4; implemented, disabled for D-008)
│   │   └── xgb.py         fit (early stopping on validation), predict_positive, save/load, check_within_paper_ranges, cuda_build
│   ├── evaluation/metrics.py  binary_metrics (accuracy, precision, recall, F1, macro-F1, MCC, AUROC, confusion matrix; DDoS = 1)
│   ├── experiments/
│   │   ├── ae_xgb.py            runner: prepare_data → preprocess → AE → (augment) → XGBoost → metrics; resumable stages; --benchmark; refuses resume under changed Git commit unless --allow-code-change
│   │   ├── shortcut_diagnostics.py  port association, single-feature trees, port-80-conditional trees, removal overlap, baseline errors
│   │   └── compare_ablation.py  paired comparison on common rows, exact McNemar
│   └── audit/
│       ├── registry.py      load_registry, validate (evidence rules), column_entries, feature_sets (direct/shortcut/hypothesis/all/missing)
│       ├── arr.py           merge_columns, top_k (ties by name), arr_at_k (NaN on zero denominator), arr_table
│       ├── composite.py     CompositeModel: raw 78 features → saved preprocessing → saved AE encoder → saved XGBoost; precision float32|float64
│       └── shap_explain.py  stratified_sample, explain_rows (PermutationExplainer + checks), run_variant (cached by settings hash), local_explanations, stability, summarize_cached, plot_global; CLI
├── tests/  (122 tests, see §13)
├── scripts/ setup_env.ps1, inspect_all.ps1, make_colab_notebook.py (generates the notebook)
├── notebooks/colab_runner.ipynb   thin Colab launcher (generated; D-015 switch; code bundle or GitHub)
├── docs/   decision_log.md, MILESTONE_1A_HANDOVER.md, DIAGNOSTIC_D008_SHORTCUTS.md, MILESTONE_2A_REPORT.md, COLAB_EXECUTION_PLAN.md, milestone0_checklist.md
├── data/raw/<dataset id>/        datasets (ignored)
├── data/processed/               empty (ignored)
├── paper/                        .gitkeep only (Phase IV manuscript to come)
└── results/
    ├── inspection/   28 dataset inspection reports (.json + .txt)
    ├── baselines/ae_xgb_d008_trackB-seed0-cpu-565a8b9e/   committed run summary
    ├── ablations/ae_xgb_d008_trackB_noDstPort-seed0-cpu-3054b399/   committed ablation summary
    ├── comparisons/…-vs-full.{json,paired_test.csv.gz,verification.json}
    ├── diagnostics/ae_xgb_d008_trackB-shortcuts.json
    ├── shap/ae_xgb_d008_trackB-seed0-cpu-565a8b9e/   pilot (committed JSON/PNG; npz ignored)
    ├── runs/ (ignored)   full run folders incl. smoke run ae_xgb_d008_smoke-seed0-cpu-40678c1c
    ├── splits/ (ignored)  pinned split records
    └── benchmarks/ (ignored) benchmark-cpu-20261108T011412.json
```

### 3.6 Verified commands (CLI interfaces checked in source)

```powershell
.\run.cmd -m pytest -q                                      # all tests (~30 s)
.\run.cmd -m pytest tests\test_audit.py -q                  # Milestone 2A tests
.\run.cmd -m pytest tests\test_real_data_smoke.py -v        # real-data checks (skip without data)
.\run.cmd -m src.data.manifest --hash                       # manifest + local file sha256
.\run.cmd -m src.data.acquire verify all                    # sizes/checksums vs manifest (also: download | extract; --file, --force)
.\run.cmd -m src.data.inspection <csv or dir> --label Label --json <out.json> --txt <out.txt>
.\run.cmd -m src.env --dataset cicids2017_original          # environment + provenance snapshot (--json <file>)
.\run.cmd -m src.experiments.ae_xgb --config configs/experiments/ae_xgb_d008_smoke.yaml
.\run.cmd -m src.experiments.ae_xgb --config configs/experiments/ae_xgb_d008_trackB.yaml --device cpu --benchmark
.\run.cmd -m src.experiments.shortcut_diagnostics --config configs/experiments/ae_xgb_d008_trackB.yaml --baseline-run results/runs/ae_xgb_d008_trackB-seed0-cpu-565a8b9e
.\run.cmd -m src.experiments.compare_ablation --full results/runs/ae_xgb_d008_trackB-seed0-cpu-565a8b9e --ablated results/runs/ae_xgb_d008_trackB_noDstPort-seed0-cpu-3054b399
.\run.cmd -m src.audit.shap_explain --config configs/experiments/ae_xgb_d008_trackB.yaml --run results/runs/ae_xgb_d008_trackB-seed0-cpu-565a8b9e --summarize   # reads cached variants only
```

- `ae_xgb` flags: `--config` (required), `--device {auto,cpu,cuda}`, `--storage <dir>` (default `$CNET_STORAGE` or `results/`), `--benchmark`, `--allow-code-change`. **Re-running a completed run prints "already complete" and recomputes nothing.** Running the baseline config without `--device cpu` locally fails fast (config says cuda).
- `shap_explain` flags: `--config`, `--run`, `--background`, `--explain`, `--permutations`, `--variants bg_seed:sample_seed …`, `--no-local`, `--out`, `--summarize`. Re-running pilot settings reads the cache (prints "cached, not recomputed").
- **Independent recomputation of rankings/ARR from the SHAP arrays** (no SHAP): in the extracted `MILESTONE_2A_REVIEW.zip`, `python review/recompute_from_arrays.py` (script also in the zip; not in the repo).

---

## 4. Dataset provenance

All four were downloaded on 2026-11-07 from official sources, verified and inspected [REPO: `configs/datasets.yaml`, `results/inspection/`]. **Full details (every hash, every quirk) live in `configs/datasets.yaml`; do not duplicate or change them without re-verification.** Licences: none permits re-hosting; keep all copies private.

### 4.1 CICIDS2017 original (`cicids2017_original`)

| Item | Value |
|---|---|
| Source | landing `https://www.unb.ca/cic/datasets/ids-2017.html`; download behind a **registration form** at `https://cicresearch.ca/CICDataset/CIC-IDS-2017/` (session cookie). Registrant details deliberately not recorded |
| Files | `MachineLearningCSV.zip` 235,102,953 B, sha256 `c3f26274b36c837ccf28ffd2dbf4582941c30b3ee70a635c6e5b2f87c4727928`, publisher MD5 `4f83860afbf29cac8163854095bf6cf7` (CIC's .md5 names it MachineLearningCVE.zip); `GeneratedLabelledFlows.zip` 283,876,488 B, sha256 `7bdbef28…` |
| Local | `data/raw/cicids2017_original/` (+ `extracted/`), ~2.5 GB on disk |
| Representation | CICFlowMeter v3-era CSVs, **78 features + Label** (MachineLearningCVE has no IP/time/Flow ID; GeneratedLabelledFlows/TrafficLabelling has them) |
| Rows | 2,830,743 over 8 day files; Friday-Afternoon-DDos 225,745 |
| Labels | 15 (BENIGN 2,273,097; DoS Hulk 231,073; PortScan 158,930; DDoS 128,027; …; Heartbleed 11). Web-attack labels contain a literal U+FFFD |
| Quirks | leading spaces in 65 of 79 column names; `Fwd Header Length` duplicated (`.1`, identical values); Infinity in Flow Bytes/s (1,509) and Flow Packets/s (2,867); `Init_Win_bytes_*` = −1 sentinel in 1,001,189 / 1,441,552 rows; negative Flow Duration 115 rows; negative Fwd Header Length / min_seg_size_forward 35 rows; 8 columns constant in every day file (Bwd PSH/URG Flags, 6 bulk columns); Fwd URG Flags **not** constant overall |
| Duplicates | per day 2.0% (Friday DDoS) to 58.3% (Friday PortScan) content duplicates |
| Licence / citation | no named licence; cite Sharafaldin, Lashkari, Ghorbani, ICISSP 2018; do not re-host |
| Not downloaded | PCAPs (only needed to re-extract flows) |
| Known issues | Engelen (TCP appendices 25.9%, labels, attempted attacks); Lanvin (~5% duplicated packets, unlabelled port scan); **reported TCP flag-count defect (§8, unverified)** |

**D-008 file** (`MachineLearningCVE/Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv`, sha256 `6ff1580f…7b411ee`): 225,745 rows (DDoS 128,027 / BENIGN 97,718); after D-011 rules 225,709 (DDoS 128,025 / BENIGN 97,684); 223,080 distinct vectors; 0 conflicting-label groups.

### 4.2 Engelen corrected CICIDS2017, WTMC2021 (`cicids2017_engelen_wtmc2021`)

| Item | Value |
|---|---|
| Source | `https://intrusion-detection.distrinet-research.be/WTMC2021/`; `…/WTMC2021/Dataset/dataset.zip`; fixed extractor `github.com/GintsEngelen/CICFlowMeter` |
| File | `dataset.zip` 333,841,436 B, sha256 `4d535da19795d853…` (full value in manifest) |
| Version | WTMC2021 with page-logged updates 20/10/2021, 22/10/2021 (CICFlowMeter fix), 24/11/2021 (Down/Up ratio fix). A **newer CNS2022 version exists and was NOT adopted** (D-004) |
| Rows / columns | 2,100,814 rows in 5 day files (Mon 371,749; Tue 322,003; Wed 496,779; Thu 362,368; Fri 547,915); 77 features + 6 identifiers (84 columns), **renamed** vs original |
| Labels | 25 incl. 10 `- Attempted` (9,144 rows); measured counts minus 793 Infinity/NaN rows equal the landing-page table exactly |
| Quirks | Infinity/NaN in rate and IAT columns; negative Flow IAT Min (2,922 rows); no column constant everywhere; duplicates 3.9% (Wed) to 32.4% (Fri; 596 conflicting-label groups) |
| Licence | **UNCONFIRMED** (no licence text); cite the paper; do not re-host |
| Alignment | needs a **hand-checked name map** (77 shared features expected), not positional (D-005). Not built yet |

### 4.3 UNSW-NB15 (`unsw_nb15`)

| Item | Value |
|---|---|
| Source | `https://research.unsw.edu.au/projects/unsw-nb15-dataset` → official SharePoint share (CSV folder only) |
| Files | `UNSW-NB15_1..4.csv` (no header), `NUSW-NB15_features.csv`, `NUSW-NB15_GT.csv`, `UNSW-NB15_LIST_EVENTS.csv`, `UNSW_NB15_training-set.csv` (175,341 rows), `UNSW_NB15_testing-set.csv` (82,332 rows); sizes and sha256 in manifest; ~688 MB |
| Representation | Argus/Bro features: 49 columns in full CSVs; partition files 45 columns (id + 42 features + attack_cat + label); categorical proto/service/state |
| Labels | Normal + 9 attack categories; full CSVs 2,540,047 rows measured (page says 2,540,044) |
| Quirks | attack_cat whitespace variants and Backdoor/Backdoors; ct_flw_http_mthd / is_ftp_login mostly empty in files 2–4; ports partly text; duplicates: training-set 42.4%, testing-set 34.5% (id ignored); 10.4% of test rows have an exact training twin; UTF-8 BOM |
| Licence | free academic use; commercial by agreement |
| Fang relation | Fang's counts equal the official partition (except 2 train-Normal rows); DoS-vs-Normal leakage: 4.9% DoS and 3.2% Normal test rows have a twin (D-009) |

### 4.4 NF-UNSW-NB15-v2 (`nf_unsw_nb15_v2`)

| Item | Value |
|---|---|
| Source | `https://staff.itee.uq.edu.au/marius/NIDS_datasets/` → UQ RDM API (signed URL) |
| File | `NF-UNSW-NB15-v2.zip` 33,877,423 B (BagIt; manifest-sha1 of the CSV verified) |
| Rows / columns | 2,390,275 rows (attack 95,053; benign 2,295,222), 45 columns = 43 NetFlow-v2 features + Label + Attack |
| Model inputs | Wardana's 39 = 43 − {IPV4_SRC_ADDR, L4_SRC_PORT, IPV4_DST_ADDR, L4_DST_PORT} (D-001) |
| Quality | no missing/infinite; 0 full-row duplicates, but **90.1% duplicates on the 39 inputs** (2,153,276 rows); random 70/15/15 puts 93.5% of test rows in train |
| Licence | UQ "Permitted Re-Use with Commercial Use Restriction"; cite Sarhan, Layeghy, Portmann 2022 |
| Note | v1, v3 and CIC-UNSW-NB15 are different datasets on the same page |

### 4.5 Representations and why alignment cannot be assumed

- **CICFlowMeter (original):** bidirectional flows, 78 statistics; known FIN/RST/ordering/duplication defects.
- **Corrected CICFlowMeter (Engelen):** same family, fixed flow termination, re-labelled, renamed columns, different row population (no row key; flows re-segmented).
- **Argus/Bro (UNSW-NB15):** different feature definitions (e.g. `swin/dwin`, `sttl/dttl`, `proto/service/state`).
- **NetFlow v2 (NF-*):** 43 nProbe-style fields (bytes/packets in/out, TCP flag bitmasks, TTLs, throughput, packet-size bins).
- A model trained on one schema cannot be evaluated on another without explicit feature engineering, unit and label harmonization (D-006). NF-UNSW-NB15-v2 vs UNSW-NB15 is the same traffic in two representations (schema comparison, not transfer).

### 4.6 Unverified / open about the data

Engelen licence; CNS2022 vs WTMC2021 (D-004); `Attempted` policy and column map (D-005); Lanvin's corrected data and USB-IDS-1 not acquired; the other four NF datasets for MES-DNN not acquired (D-010); which Friday flows are affected by duplicated packets or appendices (not identified); whether the reported flag-count defect affects the Friday DDoS file (§8).

---

## 5. Research decision history (D-001 … D-019)

Status as written in `docs/decision_log.md` at HEAD. **Do not mark OPEN or DEFERRED items as approved.** Anything marked APPROVED/DECIDED needs fresh user approval to change.

| ID | Title | Status (date) | Decision / state | Open questions |
|---|---|---|---|---|
| D-001 | NetFlow feature count 43 vs 40 vs 39 | **APPROVED** (2026-11-08) | Model inputs = 39 (43 features − 4 IP/port); keep 43/40/39 distinct; fix "43-feature" wording in Phase IV | — |
| D-002 | SHAP on AE-XGBoost: latent vs original features | Originally **DEFERRED**; **DECIDED** in Milestone 2A (2026-11-08): option (a) composite-model explanation | Options considered: (a) composite, (b) separately labelled raw-feature XGBoost proxy, (c) latent-only. Rule: latent SHAP never relabelled with raw names | (b) not used; could be added as a labelled sanity check |
| D-003 | AE input dimension | **APPROVED** (2026-11-08) | Input = train-fitted pipeline output: 68 on D-008 (78 − 10 constant); hidden/latent 80/40 kept; wording "documented reproduction/adaptation" | Whether to rescale widths (80 > 68 input) — kept 80 |
| D-004 | Engelen WTMC2021 vs CNS2022 | **OPEN** | WTMC2021 downloaded; CNS2022 and Lanvin's version not | which corrected version(s) |
| D-005 | Correction-induced record/label changes | **OPEN** | R4 split into R4a (corrected-capture) and R4b (cross-dataset); measured Engelen counts and renames | `Attempted` policy; hand-checked column map; retrain on corrected? |
| D-006 | Incompatible cross-dataset schemas | **OPEN** | Proposal: R4 limited to CICIDS2017 original → corrected; R4b only after a written field map | which pairs, if any |
| D-007 | Evaluation design | **PARTIALLY APPROVED** (2026-11-08) | Approved: two tracks (A paper-comparable, B leakage-resistant), same test set for comparable ablations, train-only fitting, no fold-based statistics. **Track B split approved and implemented** (content groups, `group_split` 70/15/15 seed 42, fingerprint `50bd9948…`) | Track B statistics (seeds 0–4, cluster bootstrap over test groups, 2,000 resamples) and track A (StratifiedKFold 5, shuffle, rs 42) are **proposals** |
| D-008 | First baseline dataset | **APPROVED** (2026-11-08) | Friday DDoS file, binary, DDoS = 1 | extension to full corpus = separate declared work |
| D-009 | Fang UNSW-NB15 subset and split | **OPEN** | Fang used the official partition (2 rows unexplained); normal is Fang's positive class | which split; inspect author repo first? |
| D-010 | MES-DNN scale / five NetFlow datasets | **OPEN** | ~2.4M/16.9M/37.8M/18.9M/76.0M flows; only NF-UNSW-NB15-v2 acquired | reduced scope vs acquiring all five (storage, RAM, D-015) |
| D-011 | Invalid row handling | **APPROVED for D-008** (2026-11-08) | Exclude missing / infinite / negative Flow Duration (36 rows); keep −1 sentinels; constants on train only; log everything | other datasets decided per experiment |
| D-012 | Artifact registry evidence levels | **OPEN**; registry **built** in Milestone 2A | Levels assigned conservatively (see §6, §8); Destination Port retained in baseline | team must confirm levels; Lanvin applicability to Friday file; **ACK/PSH flag-count correction pending (§8)** |
| D-013 | Unverifiable Phase II citations | **OPEN** | [4]–[6] not available | obtain PDFs or soften claims |
| D-014 | Python environment | **DECIDED** (2026-11-07) | python.org 3.11.9, `.venv` in project, `run.cmd`, `setup_env.ps1` | — |
| D-015 | Storage location | **DECIDED** (2026-11-07): everything local | **Amendment 1 AUTHORIZED** (2026-11-08, user: "for all of the heavy lifting i will need colab"): CICIDS2017 zip + code bundle + run outputs may go to the user's **private** Drive for Colab Free; user uploads and signs in; anything else needs new approval | Stale text remains in the entry ("Amendments: none in effect" and the old "To authorize…" line) — doc fix pending |
| D-016 | Compute: local CPU + Colab GPU | **DECIDED** (2026-11-08, team requirement) | Laptop for dev/tests; Colab Free for GPU-heavy work; thin notebook | Colab never executed |
| D-016 Am.1 | Small baselines on laptop CPU | **DECIDED** (2026-11-08, user "Laptop CPU instead") | First baseline (and later the ablation) run on CPU (minutes) | — |
| D-017 | AE-XGBoost adaptations vs paper | **DOCUMENTED** (2026-11-08) | Full deviation table (scope, input 68, linear output, patience 10, augmentation implemented but disabled, fixed XGB params lr 0.11 depth 6 α0 λ1 subsample/colsample 0.8, ≤2000 trees, early stop 50, track B instead of 5-fold CV, threshold 0.5) | grid search not done (deliberate) |
| D-018 | Destination Port ablation | **APPROVED and EXECUTED** (2026-11-08, "Approve and run"), independently re-verified | Same split/training rows; `exclude_eval_twins` in each model's input view; common test population 33,486 rows; full model not retrained | more seeds; reduced-validation retrain of full model (optional asymmetry fix) |
| D-019 | Original-feature SHAP method | **DECIDED** (2026-11-08, Milestone 2A) | Permutation SHAP on composite model, log-odds output, independent (interventional) masker, train-partition stratified background, test-partition stratified explained rows, float64 evaluation, caching, merged duplicate column, ARR@K tiers, stability across variants | duplicate-merge rule and flag-count tiering to revisit (§8) |

**Note on ordering:** in the log file, D-019 appears **before** D-018 (inserted there in Milestone 2A). Content is complete; only order is unusual.

---

## 6. Milestone-by-milestone history

### Milestone 0 — Research infrastructure (2026-11-07 → 11-08) — **COMPLETE**

- **Repository & environment:** skeleton, `.gitignore`, pinned deps, `.venv` via `setup_env.ps1`, `run.cmd`; everything local (D-014, D-015).
- **Acquisition:** manifest with official sources only (no silent mirrors); all four datasets downloaded, size/sha256/MD5/SHA-1 verified, safely extracted. CIC original required the registration form (filled by Claude with user-typed details; details not recorded). Engelen download initially corrupted by overlapping curl processes → re-downloaded and verified.
- **Inspection:** `src/data/inspection.py`; 28 reports in `results/inspection/` (paths made repository-relative).
- **Preprocessing/splitting:** `TrainOnlyPreprocessor`, `invalid_row_mask`, split utilities with leakage checks, `save_split/load_split` with record digest.
- **Config system:** `src/config.py` overlays experiment YAML on `base.yaml`, rejects unimplemented settings.
- **Independent audit** (`CNET_MILESTONE_0_INDEPENDENT_AUDIT.md`): **PASS WITH CONDITIONS**; fixes F1 (undeclared text → error), F2 (split record integrity), F3 (config wired), F4 (real-data smoke test), F5 (no absolute paths/personal metadata) — all fixed and tested.
- **Finalization:** decisions D-001, D-003, D-008, D-011 approved; D-007 partially; D-002 deferred; Colab plan and notebook scaffold; commit `98620bd`. Tests then: 79 passed.
- Report: `MILESTONE_0_HANDOVER.md` (untracked), `docs/milestone0_checklist.md`.

### Milestone 1A — AE-XGBoost implementation (commit `6fed9b0`) — **COMPLETE**

- AE 68 → 80 → 40 → 80 → 68 (ReLU hidden/latent, linear output), Adam 1e-3, batch 256, ≤100 epochs, patience 10 on validation MSE, best weights restored; per-epoch atomic checkpoints with RNG state (resumable); latent augmentation implemented (training-only, σ = 0.1 × latent std, 1:1 balance, keep within 95th percentile of reconstruction error) but **disabled** (DDoS is the majority: 89,577 vs 68,421).
- XGBoost: fixed a priori within paper Table 5 ranges (D-017); early stopping on validation; `check_within_paper_ranges` records violations (none).
- Runner: resumable stages, run identity = experiment + seed + device + config hash, refuses to resume under a different Git commit, records environment, split and evaluation fingerprints, logs names only (no absolute paths).
- Track-B split pinned (fingerprint in config).
- CPU benchmark: AE 0.92 s/epoch, XGBoost 9 ms/round, data 12.8 s → full run ≈ minutes (D-016 note).
- Colab notebook made runnable (later fix `2fd0a57`: install before import; dataset path).
- Report: `docs/MILESTONE_1A_HANDOVER.md`.

### Milestone 1A — Actual baseline training — **COMPLETE, verified**

| Item | Value [REPO: run record, metrics, identity] |
|---|---|
| Run ID | `ae_xgb_d008_trackB-seed0-cpu-565a8b9e` |
| Commit | `6fed9b06b85170e00ebc0c2e0e1fadbea42e0d4e` (recorded "dirty" only because of the untracked M0 handover) |
| Config hash | `565a8b9e62065f93ce62198b059432dab7ab4030d7abcd8d252d593679f5571f` |
| Data | `MachineLearningCSV.zip` sha256 `c3f26274…727928`; DDoS CSV sha256 `6ff1580f…7b411ee` |
| Split | fingerprint `50bd994880abbe151738993e299b90a6e50fb5ffae235a72677bb7813c447f44`; train 157,998 (DDoS 89,577) / val 33,834 (19,215) / test 33,877 (19,233); overlap 0/0/0 raw and preprocessed |
| Input / latent | 68 / 40 |
| AE | `epochs_run` 61, message "early stopping at epoch 60 (patience 10)", best epoch 50, best val MSE 3.595e-6 |
| XGBoost | best iteration 204 |
| Hardware / time | laptop CPU (D-016 Am.1); 1.45 min (data 13.0 s, AE 65.2 s, XGB 3.2 s) |
| Seed | model seed 0; split seed 42 |
| Metrics | §7 |
| Files | summary: `results/baselines/<run>/` (config, identity, data report, preprocessor with feature list, AE history, metrics, environment, log, confusion matrices); full artifacts: `results/runs/<run>/` (`checkpoints/ae_best.pt`, `xgb_model.json`, `latent.npz`, `predictions_val.csv.gz`, `predictions_test.csv.gz`, `preprocessor.json`, `DONE`) |
| Verification | metrics recomputed from saved predictions in Milestone 1B; composite model reproduces saved test probabilities to 8.6e-8 (Milestone 2A) |

### Milestone 1B — Shortcut diagnostics and Destination Port ablation (commits `fd65ad5`, `f759499`) — **COMPLETE, verified**

- **Why the port was suspected:** Phase II A_meta; diagnostics: DDoS on port 80 = 128,022 / 128,025 (99.998%); benign on port 80 = 9.13%; "port 80 → DDoS" rule: test accuracy 0.9616, MCC 0.9238; no single feature reaches depth-1 validation MCC 0.90; only the port at depth-2 (0.922 val / 0.924 test). Report `docs/DIAGNOSTIC_D008_SHORTCUTS.md`, data `results/diagnostics/ae_xgb_d008_trackB-shortcuts.json`.
- **Design (D-018):** same pinned split, identical training rows; removing the port creates new cross-partition duplicates (357 train–val, 364 train–test, 163 val–test, all BENIGN) → `exclude_eval_twins` in each model's own input view; ablated validation 33,477 (357 removed), test 33,486 (391 removed: 228 twin of train, 27 twin of val, 136 both; all BENIGN, mostly ports 137/80/443); both models scored on the **same 33,486 rows** (evaluation fingerprint `0435302bf798010dec7b4251f3a489b81ea17cbe5c9078784d5306d9d9796319`); full model not retrained, predictions restricted.
- **Ablated run:** `ae_xgb_d008_trackB_noDstPort-seed0-cpu-3054b399`, commit `fd65ad5`, input 67, AE **100 epochs (cap), best 98** (val MSE 1.586e-6) — convergence concern; XGB best iteration 166; 2.36 min (AE 119.9 s).
- **Results:** §7. McNemar exact p = 0.625 (3 vs 1 discordant).
- **Verification:** recomputed independently (scikit-learn, SciPy exact binomial, independent duplicate grouping) — exact match; baseline's 16 pre-existing artifacts byte-identical; sha256 of 32 run artifacts in `…verification.json`.
- **Asymmetry:** full model early-stopped on all 33,834 validation rows, ablated on 33,477 (optional fix: retrain full model on reduced validation, ~1.5 CPU min; not done).

### Milestone 2A — Forensic registry, SHAP, ARR@K (commits `29c9b52`, `ca8e51b`, `93c1a83`) — **COMPLETE (pilot); correction pending (§8)**

- **Registry** `configs/artifact_registry.yaml` (12 feature entries R01–R12 + 7 non-feature issues F01–F04, L01, L02, I01), loader/validator `src/audit/registry.py`. Fields per entry: id, name, columns (exact CICIDS2017 names), source_names, phase2_category, evidence_level, target (feature/flow/label/generation_process), scope, mechanism, sources (ref, section, page, finding), local_evidence, validation_required. Sources: engelen2021 (paper7.pdf), lanvin2023 (paper8.pdf), phase2, local.

  | ID | Column(s) | Level | Source |
  |---|---|---|---|
  | R01 | Destination Port | unverified_hypothesis | Engelen §III-D p.4; Phase II; local D-018 |
  | R02 | Init_Win_bytes_forward | shortcut_indicator | Engelen §IV-B.1 p.5 |
  | R03 | Init_Win_bytes_backward | unverified_hypothesis | Phase II only |
  | R04 | min_seg_size_forward | shortcut_indicator | Engelen §IV-B.1 p.5 |
  | R05 | Fwd Header Length + Fwd Header Length.1 | shortcut_indicator | Engelen §IV-B.1 p.5 |
  | R06 | Total Fwd Packets | shortcut_indicator | Engelen §IV-B.1 p.5 |
  | R07 | SYN Flag Count | shortcut_indicator | Engelen §IV-B.1 p.5 |
  | R08 | Bwd Packet Length Mean | shortcut_indicator | Engelen §IV-B.1 p.5 |
  | R09 | Flow IAT Min | direct_extraction_error | Lanvin §3.3 pp.8–9 (Table 5), §4.2 Q3 p.15 |
  | R10 | Flow IAT Mean | direct_extraction_error | Lanvin §4.2 Q3 p.15 |
  | R11 | Flow Packets/s | direct_extraction_error | Lanvin §4.2 Q3 p.15 |
  | R12 | Bwd Packets/s | direct_extraction_error | Lanvin §4.2 Q3 p.15 |

  Validation rules in code: levels/targets from fixed lists; unique ids; sources must exist and carry section + finding; Engelen/Lanvin sources need a page; **any level above hypothesis needs a paged source**; no column mapped twice; feature entries need columns. **Current limitation:** one evidence level per entry and one entry per column (a column cannot carry two mechanisms) — relevant for §8.
- **Composite predictor** `src/audit/composite.py`: rebuilds the model from saved artifacts; checks raw columns = numeric ∪ constant-on-train; float32 reproduces saved probabilities (max diff 8.6e-8, latent 4.8e-7, predictions identical).
- **SHAP** (D-019): Permutation explainer, margin output, independent masker; background = stratified **train** sample; explained = stratified **test** sample (200 rows); misclassified rows explained separately; float64 evaluation; caching by settings hash.
- **Pilot:** 6 variants, all checks passed; results §7.
- **Float32 vs float64** (record `review/float32_vs_float64.json` in `MILESTONE_2A_REVIEW.zip`; inference only): float32 output depends on batch composition (1 of 50 background rows changed by 0.083 log-odds); float64 batch-invariant; float64 vs saved: predictions identical, max prob diff 8.9e-4; 16 of 33,877 test rows changed margin by > 1e-3 (max 1.57 log-odds).
- **Review package:** `MILESTONE_2A_REVIEW.zip` (181 files, 1,104,524 B, sha256 `be205142cb53887d9b1e2a31d61faa0cc2617da2c4e34dd81779ca6c2871bb5f`, built from `fbd10cd`); includes SHAP arrays, recompute script (rankings/ARR reproduced to ≤ 6e-9), precision record, test logs.
- **Independent review of 2A:** done by the user/reviewer outside this repo; identified the ACK/PSH omission (§8). Review text not available locally.
- **Current corrective task:** NOT STARTED (§8).

---

## 7. Actual experimental results

All numbers below are **ours**, from recorded files, one model seed. "Test used once" = validation chose the model; test not used for any choice.

### 7.1 Classification results (paper-ready table)

| Exp. | Model / features | Seed | Population | Acc | Prec | Rec | F1 | Macro-F1 | MCC | AUROC | TN / FP / FN / TP | Runtime | Commit | Validated |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| E1 val | AE-XGB, 78 raw → 68 inputs | 0 | val, 33,834 | 0.999852 | 0.999792 | 0.999948 | 0.999870 | 0.999849 | 0.999699 | 1.000000 (0.9999997) | 14,615 / 4 / 1 / 19,214 | 1.45 min | 6fed9b0 | yes |
| **E1 test** | AE-XGB, 68 inputs | 0 | **full test, 33,877** | 0.999852 | 0.999844 | 0.999896 | **0.999870** | 0.999850 | **0.999699** | 0.999992 | 14,641 / 3 / 2 / 19,231 | — | 6fed9b0 | yes |
| E1 on common | same model, predictions restricted | 0 | **common test, 33,486** | — | — | — | **0.999870** | — | **0.999695** | 0.999992 | 14,250 / 3 / 2 / 19,231 | — | 6fed9b0 | yes |
| E2 val | AE-XGB without Destination Port, 67 inputs | 0 | val, 33,477 | 0.999791 | 0.999792 | 0.999844 | 0.999818 | 0.999786 | 0.999572 | 0.999999 | 14,258 / 4 / 3 / 19,212 | 2.36 min | fd65ad5 | yes |
| **E2 test** | without Destination Port | 0 | **common test, 33,486** | 0.999791 | 0.999844 | 0.999792 | **0.999818** | 0.999786 | **0.999572** | 0.999980 | 14,250 / 3 / 4 / 19,229 | — | fd65ad5 | yes |

- Exact stored test F1 of E1: **0.9998700184573791**; MCC 0.9996992960534733 (full test). On the common rows MCC is 0.999695 (different population — **do not mix 33,877 and 33,486 figures**).
- Train metrics (overfitting diagnosis only): E1 train F1 0.999983 (TN 68,421 / FP 0 / FN 3 / TP 89,574).
- **Paired E1 vs E2 on 33,486 rows:** both correct 33,478; both wrong 4 (5245, 5246, 99515, 110943); only full correct 3 (187242, 190967, 210451); only ablated correct 1 (155712); **exact McNemar p = 0.625** — not significant, **not evidence of equivalence** (4 discordant rows → very low power).
- **Author-reported (not comparable):** Nezhadsistani CIC-IDS2017 F1 0.9993 (Table 6; joint 3-dataset training, 5-fold CV).
- Limitations: one seed; one capture; duplicate-aware but not session-aware; ablated AE hit epoch cap; restricted population for E2.
- Files: `results/baselines/…`, `results/ablations/…`, `results/comparisons/…-vs-full.json` (+ `paired_test.csv.gz`, `verification.json`).

### 7.2 Diagnostics (association only, D-012)

| Analysis | Result |
|---|---|
| Rule "port = 80 → DDoS" (test) | acc 0.9616, MCC 0.9238, 13,344 / 1,300 / 1 / 19,232 |
| Port lookup fitted on train (test) | acc 0.8817, MCC 0.7752 |
| Best depth-1 single feature (val MCC) | Fwd Packet Length Max 0.763; none > 0.90 |
| Depth-2 single feature | only Destination Port > 0.90 (0.922 val / 0.924 test) |
| Baseline test errors | FPs 5245, 5246, 155712 (BENIGN, port 443); FNs 99515 (port 80), 110943 (port 64869) |

### 7.3 SHAP / ARR@K pilot (E3) — exploratory attribution, not confirmatory

- **Settings:** baseline run E1; 78 raw columns; Permutation SHAP (shap 0.49.1); output = log-odds of DDoS; independent masker; background stratified from **train**; 200 stratified **test** rows explained; float64 evaluation; antithetic permutations; `max_evals = permutations × (2·78+1)`.
- **Variants** (`results/shap/ae_xgb_d008_trackB-seed0-cpu-565a8b9e/variant-*`; arrays `shap_values.npz` Git-ignored but in the review ZIP):

  | Variant | Background n × seed | Explained n × seed | Perm. | Runtime |
  |---|---|---|---|---|
  | `variant-bg100x0-ex200x0-p5-b7c52b2147b1` | 100 × 0 | 200 × 0 | 5 | 39.9 s |
  | `variant-bg100x1-ex200x0-p5-23b830722e20` | 100 × 1 | 200 × 0 | 5 | 33.9 s |
  | `variant-bg100x0-ex200x1-p5-70f2da7216d3` | 100 × 0 | 200 × 1 | 5 | 33.9 s |
  | `variant-bg100x1-ex200x1-p5-17ca221e1e36` | 100 × 1 | 200 × 1 | 5 | 35.6 s |
  | `variant-bg200x0-ex200x0-p5-572ea7658299` | 200 × 0 | 200 × 0 | 5 | 91.0 s |
  | `variant-bg100x0-ex200x0-p10-6739863fb0a7` | 100 × 0 | 200 × 0 | 10 | 118.6 s |

  Plus `local-bg100x0-p5-s0/local.json` (5 misclassified + 4 correct test rows). Total ≈ 6 min CPU.
- **Checks (all variants):** shape (200, 78); finite; additivity |Σφ + base − f(x)| ≤ 5.3e-15; base = mean background margin (≤ 9e-16); the 10 unused columns get exactly 0.
- **Global importance (mean |SHAP|, log-odds, mean of 6 variants, merged duplicate):** 1 ACK Flag Count 2.35; 2 Average Packet Size 1.69; 3 Packet Length Mean 1.47; 4 PSH Flag Count 1.18; 5 Bwd Packet Length Max 1.10; 6 Destination Port 1.08; 7 Fwd IAT Total 0.92; 8 Idle Max 0.92; 9 Init_Win_bytes_forward 0.90; 10 Flow Duration 0.89; … 15 min_seg_size_forward 0.58. Registered ranks: Bwd Packet Length Mean 28–30, SYN Flag Count 32–35, Fwd Header Length 41–45, Total Fwd Packets 50–54; direct-error features 33–62.
- **Stability:** rank correlation over the Top-20 union (22 features) ≥ 0.9729; Top-5 shared 4/5, Top-10 8/10, Top-20 18/20; Destination Port rank 4–6; Init_Win_bytes_forward 7–11.
- **ARR@K as committed (registry at HEAD; range over 6 variants):**

  | K | direct extraction errors | shortcut indicators | all registered |
  |---|---|---|---|
  | 2 | 0.00 | 0.00 | 0.00 |
  | 5 | 0.00 | 0.00 | 0.00–0.15 |
  | 10 | 0.00 | 0.00–0.08 | 0.08–0.16 |
  | 20 | 0.00 | 0.07–0.09 | 0.13–0.15 |

  **These committed ARR values are expected to change** once the flag-count correction (§8) is applied.
- **Local:** FPs 5245/5246 pushed to DDoS mainly by ACK Flag Count; 155712 by PSH Flag Count and Max Packet Length; FN 110943 (port 64869): Destination Port second-largest push to benign (−2.2).
- **Limits:** one model/seed/file; 200 rows; interventional masking creates unrealistic flows; credit split among correlated features; descriptive only; feature rankings were computed on **test** rows (selection-bias risk for later ablations, §8).

---

## 8. CRITICAL: pending scientific correction (TCP flag-count defect)

### 8.1 What is known

- According to the user's summary of the **Milestone 2A independent review** (the review document itself is **not available locally**):
  - Engelen et al.'s extended documentation `https://intrusion-detection.distrinet-research.be/WTMC2021/extended_doc.html` describes a **CICFlowMeter TCP flag-count defect** affecting original CICIDS2017 features.
  - Two top-ranked SHAP features, **ACK Flag Count (rank 1)** and **PSH Flag Count (rank 4)**, are missing from the registry.
  - The reviewer's **preliminary** sensitivity estimate: direct-error ARR@20 from 0 to ≈19–20%; all-registered ARR@20 from 13–15% to ≈32–35%. Not approved results.
- **Neither this session nor any earlier session read the extended documentation.** Its exact content (which flags, which direction counters, which CICFlowMeter versions, whether values are wrong or double-counted, whether it affects the MachineLearningCVE release) is **UNVERIFIED**.
- The 6-page Engelen paper (paper7.pdf) does **not** mention ACK/PSH counting (only FIN/SYN) per earlier extracted-text search.
- Note the CICIDS2017 flag columns: `FIN/SYN/RST/PSH/ACK/URG/CWE/ECE Flag Count`, `Fwd/Bwd PSH Flags`, `Fwd/Bwd URG Flags`. `SYN Flag Count` is already R07 (shortcut indicator via appendices) — a second mechanism (flag-count defect) may apply to it too, which the current registry cannot represent (one entry per column).

### 8.2 Status in the repository — **NOT STARTED**

Verified at HEAD `fbd10cd` with a clean tree: no registry change, no code change, no new results, no notes for this task. The task brief listing the ten steps below was never executed in any session.

### 8.3 Exploratory arithmetic done during this handover (NOT saved, NOT approved)

Using the committed `summary.json` importances (no SHAP recomputed), adding `ACK Flag Count` and `PSH Flag Count` to the direct tier gives:

| Variant | direct ARR@2 / 5 / 10 / 20 | all-registered ARR@2 / 5 / 10 / 20 |
|---|---|---|
| bg100x0-ex200x0-p10 | 0.579 / 0.451 / 0.282 / 0.194 | 0.579 / 0.451 / 0.444 / 0.336 |
| bg100x0-ex200x0-p5 | 0.584 / 0.453 / 0.283 / 0.193 | 0.584 / 0.596 / 0.447 / 0.335 |
| bg100x0-ex200x1-p5 | 0.550 / 0.437 / 0.275 / 0.188 | 0.550 / 0.437 / 0.426 / 0.319 |
| bg100x1-ex200x0-p5 | 0.608 / 0.461 / 0.287 / 0.197 | 0.608 / 0.607 / 0.451 / 0.346 |
| bg100x1-ex200x1-p5 | 0.574 / 0.449 / 0.274 / 0.190 | 0.574 / 0.449 / 0.359 / 0.327 |
| bg200x0-ex200x0-p5 | 0.594 / 0.459 / 0.289 / 0.196 | 0.594 / 0.459 / 0.446 / 0.335 |

- Direct ARR@20 0.188–0.197 and all-registered 0.319–0.346 — **consistent with the reviewer's estimate**. If every `*Flag*` column were added to the direct tier, direct ARR@20 would be 0.213–0.222.
- **Duplicate-column merge:** for ARR@20 it makes no difference here (merged = unmerged shortcut ARR@20 in all variants, because `Fwd Header Length` ranks ~41–45). Column-level importances: `Fwd Header Length` 0.022–0.036, `.1` 0.014–0.024.
- This arithmetic is a check of the reviewer's figure only. The correct tier depends on what the extended documentation actually says.

### 8.4 Exact instructions to finish the task (each step small; no retraining, no SHAP recompute)

1. **Verify the source.** Ask the user for the review document; read `https://intrusion-detection.distrinet-research.be/WTMC2021/extended_doc.html` (web fetch; save the exact quoted lines, section headings and retrieval date into the registry `sources` and a short note under `docs/`). Determine precisely: which flag counters are affected, the mechanism (e.g. counting in only one direction / counting per packet incorrectly), and whether the original MachineLearningCVE CSVs are affected. If the page cannot be fetched, stop and tell the user; do not guess.
2. **Reconcile all flag columns** against the evidence (FIN, SYN, RST, PSH, ACK, URG, CWE, ECE Flag Count; Fwd/Bwd PSH/URG Flags). Register only what the source supports; list the others as checked-and-not-affected or unclear.
3. **Extend the registry schema minimally** so a column can carry **multiple mechanisms/evidence entries** (e.g. `SYN Flag Count`: shortcut indicator via appendices *and* possibly direct error via flag counting). Define how ARR tiers use them (e.g. a column counts in a tier if any of its entries has that level; report both the strongest-level assignment and per-mechanism sets). Update `validate()` and `feature_sets()`; keep the "paged/verifiable source" rule (a web page needs a URL + section + retrieval date + quoted finding instead of a page number — add an explicit rule, do not weaken the existing one).
4. **Add tests** for multi-mechanism entries, the new source type, and the expected tier membership.
5. **Recalculate ARR@K from the EXISTING six arrays** — use the cached `summary.json` importances or `shap_values.npz` (as in `review/recompute_from_arrays.py`). **Do not call the explainer.** Write the corrected tables to new files (e.g. `results/shap/<run>/arr_registry_v2.json`) and keep the original `summary.json` / `stability_all_variants.json` untouched for provenance; record the registry version/hash used for each.
6. **Duplicate-column merging:** document the choice explicitly (merged sum vs keep max vs column-level) and report both; currently it does not change ARR@20.
7. **Selection-bias guard:** the SHAP rankings were computed on **test** rows. Any ablation chosen from these rankings (e.g. "remove the Top-5 SHAP features") is **exploratory**. For confirmatory ablations, pre-register feature groups from the **literature registry** (not from test-set SHAP), or recompute rankings on train/validation rows only, and fix groups before looking at test outcomes. Write this rule into the decision log (new D-020 or an amendment to D-019).
8. **Document the float32/float64 limitation:** SHAP explains the float64 evaluation of the weights; 16 test rows differ from the saved float32 model by > 1e-3 log-odds; predictions identical. Put this in D-019 and in the report.
9. **Update docs:** D-012 (new levels, still OPEN for team confirmation), D-019, `docs/MILESTONE_2A_REPORT.md` (new section "Registry correction", keep the old numbers marked as superseded), README status.
10. **Run** `.\run.cmd -m pytest -q`, check that baseline artifacts are unchanged (`tests/test_d018_records.py` does this), then **commit** in purposeful commits (registry+code+tests; recalculated results+docs). **Do not push.** Report to the user and STOP.

---

## 9. Computational and financial constraints; Colab

### 9.1 Non-negotiable constraints (user)

- **Total additional compute budget: PKR 0.** Free resources only. No Colab Pro, paid GPUs, VPS, APIs, credits or subscriptions.
- Colab Free is the preferred venue for expensive GPU training, large SHAP workloads, repeated experiments and ablations. The laptop is for development, tests and genuinely short CPU jobs. **Do not waste Colab sessions** on work that is faster locally (e.g. the AE-XGBoost baseline costs ~1.5–2.5 CPU minutes; permutation SHAP is CPU-bound and gains nothing from a GPU).
- No unnecessary retraining; reuse checkpoints, splits, preprocessing and outputs; benchmark before expensive work; justified sampling and stability checks; no automatic large sweeps.

### 9.2 D-015 authorization (as of HEAD)

- **Authorized (Amendment 1, 2026-11-08):** the user's **private** Google Drive may hold `MyDrive/cnet-data/cicids2017_original/MachineLearningCSV.zip`, code bundles `MyDrive/cnet-data/cnet_code_<12-char hash>.zip`, and run outputs under `MyDrive/cnet-runs/`, for Colab Free runs.
- **The user uploads files and signs in.** The assistant must never type passwords, create accounts, or upload on its own. Uploading from the laptop needs a Windows file picker the assistant cannot operate. Granting the Drive-mount permission in Colab needs the user (or the user's explicit chat permission to click it).
- **Not authorized:** any other dataset, sharing the folder, pushing to GitHub (no remote exists; a push needs explicit approval), paid tiers.
- **Nothing has been uploaded so far.** Colab has **never** been executed.
- The user said "i allow you to use my account"; the assistant explained it still cannot enter passwords. Discussion ended with the user asking for this handover; **no Colab session was started**.

### 9.3 Working Colab approach (prepared, unexecuted)

`docs/COLAB_EXECUTION_PLAN.md` "First real run" steps:

1. Commit; note full hash `H`.
2. On the laptop: `git archive --format=zip -o cnet_code_<first 12 chars of H>.zip H` (no data; hash stored in the zip comment).
3. User uploads the bundle to `MyDrive/cnet-data/` and the dataset zip to `MyDrive/cnet-data/cicids2017_original/`.
4. Open `notebooks/colab_runner.ipynb` in Colab; Runtime → T4 GPU.
5. Cell 1: `D015_AMENDMENT_1_RECORDED = True`, `EXPECTED_COMMIT = "H"` (40 chars); `USE_GITHUB = False` (default: code bundle). Approve the Drive prompt.
6. Cells: test suite on Colab packages; dataset sha256 + MD5; GPU benchmark; run. Outputs persist to `MyDrive/cnet-runs/runs/<run_id>/` and `MyDrive/cnet-runs/splits/`; reruns resume from checkpoints.
7. User downloads results back into the laptop's `results/runs/` for verification and commit.

The notebook is generated by `scripts/make_colab_notebook.py` (edit the script, regenerate; `tests/test_notebook.py` checks it). Only the CICIDS2017 workflow exists; other baselines need new configs/runners first.

---

## 10. Scientific integrity and engineering rules

**Standards established in this project (all binding):**

- No fabricated results, sources, citations, page numbers or implementation details. Label author-reported vs ours. Say UNKNOWN when unknown.
- No causal conclusions from SHAP or ARR@K; no claim of faithful reproduction (wording: "documented adaptation").
- Never relabel latent SHAP dimensions with raw feature names.
- All preprocessing, augmentation, feature selection, thresholds fitted on training data only; validation for model selection; test used once.
- No shortcut/artifact claim without evidence; Destination Port stays a hypothesis.
- No unnecessary retraining; never overwrite completed artifacts; never delete unrelated work; keep the untracked M0 handover.
- No excessive dependencies, speculative features, redundant code or large architecture changes; respect the existing structure (`src/data`, `src/models`, `src/experiments`, `src/audit`, configs, decision log).
- No repeated full-dataset operations without reason.
- Real end-to-end checks matter more than mocked tests; tests must be targeted (synthetic fixtures + real-data tests that skip without data).
- Meaningful, atomic commits with the attribution line; never push without explicit approval; no absolute local paths, personal or registration data in committed files (hygiene scan used before each review package).
- Preserve provenance: run identity (config hash, commit, dataset hashes, split fingerprint), environment snapshot, logs with names only.

**Descriptive vs exploratory vs confirmatory:**

- *Descriptive*: measurements of data or models without inference (dataset counts, port association, one-seed metrics).
- *Exploratory*: analyses that generate hypotheses, including anything chosen after looking at results (SHAP rankings on test rows, the ARR pilot, single-seed ablations, the §8.3 arithmetic).
- *Confirmatory*: pre-specified hypotheses, feature groups, populations, seeds and tests fixed **before** outcomes are seen, with adequate replication (multiple seeds, uncertainty intervals). Nothing in this project is confirmatory yet.

**Fair evaluation population for feature ablations:** removing columns can make previously distinct rows identical. Recompute content groups in each model's own input view; exclude validation/test rows that duplicate an earlier partition in that view (`split.exclude_eval_twins`); score **all** compared models on the **same** remaining rows (common population, evaluation fingerprint); keep training rows, labels, split, hyperparameters, seed and threshold identical; report exclusions and the full-population metrics separately; use paired tests (exact McNemar) and never treat non-significance as equivalence.

---

## 11. Remaining work for Phase III (roadmap)

**Mandatory Phase II commitments** (from the 12 steps; deviations as recorded): registry (done, correcting), SHAP + ARR@K for each baseline, **three baselines**, regimes R1–R4 (R4 as R4a/R4b), classification + XAI metrics, statistical comparison, top-k artifact vs non-artifact ablations (retrained), error analysis on R3/R4, final outputs. **Do not drop required experiments to save compute;** reduce scope only with a recorded decision.

| # | Work item | Depends on | Where to run | Status |
|---|---|---|---|---|
| 1 | Registry flag-count correction + ARR recalculation (§8) | review doc, extended doc | laptop (minutes) | NEXT |
| 2 | Team confirmation of registry levels (D-012) | 1 | — | open |
| 3 | Decide D-007 statistics (seeds 0–4, cluster bootstrap) | — | — | proposal |
| 4 | Pre-registered literature-defined group ablations on D-008: R2 (A_meta), R3 (A_meta ∪ A_bug), flag-count group, duplication group, each with a **size-matched control group**, retrained, common population, seeds 0–4 | 1–3 | laptop CPU is feasible (≈2–3 min per run; ~10 groups × 5 seeds ≈ 2–3 h) or Colab | not started |
| 5 | More seeds for E1/E2; uncertainty intervals | 3 | laptop | not started |
| 6 | Descriptive-accuracy curve (E-XAI) and stability metrics; SHAP on train/val rows for unbiased rankings | 1 | laptop (SHAP CPU-bound) | not started |
| 7 | Session/host/time-aware split sensitivity using `TrafficLabelling` (GeneratedLabelledFlows) keys | — | laptop | not started |
| 8 | Original ↔ Engelen column map (hand-checked, 77 shared) and `Attempted` policy (D-005); R4a evaluation of the D-008 model on Engelen Friday DDoS flows | D-004, D-005 | laptop | not started |
| 9 | Track A (paper-comparable 5-fold CV) for AE-XGBoost | D-007 | laptop | not started |
| 10 | MES-DNN (Wardana) implementation; scale decision (D-010); 39 NetFlow inputs; DeepExplainer or model-agnostic SHAP on the stacked model | D-010, data acquisition | Colab GPU for training at scale | not started |
| 11 | DCNN + self-attention (Fang): inspect author repo first; LightGBM/TreeSHAP selector then DCNN; separate explainer for DCNN; D-009 split; polarity | D-009 | Colab GPU | not started |
| 12 | Cross-dataset R4b only after a written field map (D-006) | D-006 | — | not started |
| 13 | Error analysis (Attempted, appendices, slow DoS) on R3/R4 | 4, 8 | laptop | not started |
| 14 | Figures and tables for Phase IV (§12) | all | laptop | partial (3 SHAP plots) |

**Minimum scientifically defensible plan (if time is short):** items 1–5 + 8 (R4a) on AE-XGBoost with 5 seeds, plus at least one more baseline implemented faithfully enough to compute SHAP/ARR; declare any baseline not completed as a limitation rather than silently omitting it. This needs the team's explicit agreement because Phase II promised three baselines.

---

## 12. Phase IV paper strategy

**Required structure:** the Phase IV assignment text was **not found** (§1.2). README says IEEE LaTeX. Use a standard IEEE research structure unless the brief says otherwise: Abstract, Introduction, Related Work, Datasets and Provenance, Methodology (registry, baselines, splits, SHAP, ARR@K, ablation, statistics), Results, Discussion, Threats to Validity, Reproducibility, Conclusion, References.

**Framing:** testable question "how much of near-perfect benchmark performance rests on documented recording artifacts?"; contributions = evidence-tagged registry, composite-model attribution for latent-space models, fair ablation protocol under duplicate-aware splitting, empirical results. Avoid absolute novelty claims.

**Related work narrative:** forensic dataset critique (Engelen, Lanvin) → transfer failures (Catillo) → XAI evaluation (Arreche) and theory (Lundberg & Lee) → modern baselines (Nezhadsistani, Wardana, Fang) that use XAI passively. Background only: Kalasampath, Senevirathna. Uncertified: [4]–[6].

| Section | Can be drafted now from verified evidence | Must wait |
|---|---|---|
| Datasets & provenance | yes (`configs/datasets.yaml`, inspection reports, D-008/D-011 counts, duplicate rates) | corrected-data alignment |
| Evaluation protocol | yes (track B, fingerprints, exclusion rule, McNemar) | statistics policy (D-007) |
| AE-XGBoost adaptation | yes (D-003, D-017 table) | — |
| Registry & SHAP method | method yes (D-019); registry table **after §8 correction** | — |
| ARR@K definition & limitations | yes | final values after §8 |
| Baseline results | single-seed E1/E2 yes, labelled as one seed | multi-seed results, other baselines |
| Ablations | D-018 only (exploratory, one seed) | group ablations with controls |
| Generalization | no | R4a/R4b |
| Threats to validity | partly (one capture, one seed, masking assumptions, float64 evaluation, test-set-selected rankings, restricted populations) | — |
| Reproducibility | yes (commands, hashes, environment, review packages) | Colab verification |

**Rules:** every number in the abstract must come from our experiments; quote author numbers only as author-reported with table/page; verify all citations (Lanvin LNCS volume, Senevirathna version, Nezhadsistani DOI, [4]–[6]).

**Figures/tables still needed:** dataset table; split/duplication table; baseline metrics with CIs; ARR@K vs K per tier per model; SHAP Top-20 with registry colouring (exists for AE-XGB, regenerate after §8); ablation deltas with controls and CIs; R4a results; error-analysis table.

---

## 13. Exact current project status

### 13.1 Confirmed from the repository [REPO] (checked during this handover, 2026-11-08)

- Branch `main`; HEAD `fbd10cd4eb4f827d5d6946f480fb1c197263e259` "Record D-015 Amendment 1 as authorized (Colab Free + private Drive)".
- No Git remote. Nothing pushed.
- `git status --short`: `?? MILESTONE_0_HANDOVER.md` (intentional). The two handover files (`CNET_COMPLETE_PROJECT_HANDOVER.md`, `CNET_NEW_SESSION_QUICKSTART.md`) were committed at the user's request in the commit right after `fbd10cd` ("Add the complete project handover for a new Claude Code session"); that commit changes no code, config or result.
- Ignored local artifacts present: datasets (`data/raw/*`, ~5 GB), three run folders in `results/runs/` (baseline, ablation, smoke), three split records, one CPU benchmark, six SHAP `.npz` arrays, three review ZIPs.
- **Tests:** full suite **122 passed** (~28 s) at HEAD with data present, run earlier on 2026-11-08 for the review package (not rerun after writing this document, which changed no code). Per file: acquire 8, ae_xgb 13, audit 16, config 10, d018_records 3, env 4, inspection 20, manifest 6, notebook 6, preprocess 13, real_data_smoke 3, split 20. On a data-free copy, real-data tests skip.
- Most recent completed milestone: Milestone 2A + review package `MILESTONE_2A_REVIEW.zip`.
- Active task: §8 correction — **not started**.

### 13.2 Reported earlier, not re-verified here [EARLIER]

- Content of the Milestone 2A independent review (only the user's summary).
- Content of Engelen's extended documentation.
- Earlier test totals (73, 79, 106) are historical milestones; **122 is current**.
- Gemini chat exports about Phase I.

### 13.3 Open / uncertain / unavailable [OPEN]

- Phase III/IV assignment briefs, rubric, deadlines: not found.
- Team roles: unknown.
- Decisions open: D-004, D-005, D-006, D-007 (statistics, track A), D-009, D-010, D-012 (level confirmation), D-013.
- Colab: never executed; first session needs the user's sign-in and uploads.
- No GitHub remote.

### 13.4 Known minor issues (documentation)

- `docs/decision_log.md` D-015 still says "**Amendments:** none in effect" and keeps the old "To authorize: …" sentence under the now-AUTHORIZED amendment — stale text; fix in the next docs commit.
- D-016 Amendment 1 text says "AE early-stopped at epoch 60"; D-018's table says "61 epochs". Both come from the run record (`epochs_run` 61; message "early stopping at epoch 60") — an off-by-one in the log message's counting, not a data error.
- D-019 precedes D-018 in the log file.
- `configs/experiments/ae_xgb_d008_trackB.yaml` header comment says "First real run … on Colab GPU", but the run was made on CPU (D-016 Am.1); default `device: cuda`.
- `MILESTONE_2A_REPORT.md` and README cite the ARR values that §8 will supersede.

### 13.5 Next concrete action

Start §8.4 step 1: ask the user for the Milestone 2A review document and get permission to fetch Engelen's extended documentation page; then propose the registry schema change before editing.

### 13.6 Do not change until reviewed

`results/**` committed results and run folders; `configs/experiments/ae_xgb_d008_trackB*.yaml` (pinned fingerprint and config hash — any edit changes the run identity); `src/data/split.py` splitting logic; `src/audit/composite.py` (verified against saved outputs); the SHAP cache folders.

---

## 14. Ready-to-copy initial prompt for the new session

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

---

## 15. Risks, failure modes and lessons learned

| Problem | What happened | Resolution / rule |
|---|---|---|
| Embedded Python | Windows embeddable Python's `._pth` blocked imports | Use python.org 3.11.9 + `.venv` (D-014) |
| Engelen download | Overlapping curl processes corrupted the file | Re-downloaded; always verify sha256; never run parallel downloads to one file |
| CIC registration | Original CICIDS2017 behind a form; details must not be stored | Registrant details removed from manifest |
| Missing/infinite values, negative durations | 36 invalid rows in the DDoS file | Explicit logged rules (D-011); "64 infinities" were cells, 34 rows |
| −1 sentinels | `Init_Win_bytes_*` = −1 in ~half of CICIDS2017 rows | Valid "not observed" value; never a removal rule |
| Duplicates | Random splits leak heavily (up to 93.5% of test rows) | Content-group split; overlap checks before and after preprocessing |
| Undeclared text columns | Became all-NaN silently (audit F1) | Preprocessor raises `TypeError` |
| Split record edits | `load_split` accepted edited seeds (F2) | Record digest + expected source/row count |
| Version-dependent splitting | scikit-learn `GroupShuffleSplit` not guaranteed stable | NumPy legacy `RandomState(42).permutation`; fingerprint pinned |
| Commit identification | Colab bundles have no `.git` | Commit stored in bundle; `CNET_GIT_COMMIT` env fallback; runs refuse resume under a different commit |
| Checkpoint consistency | Resumes must reproduce training | RNG state saved; test proves resume = uninterrupted training |
| PyTorch/XGBoost | xgboost wheel is a CUDA build; torch CPU on Windows; CUDA requests fail fast without GPU | `--device cpu` explicit locally |
| Colab packages | Installing pinned numpy on Colab breaks torch; installs had to precede imports | Notebook installs only missing packages, before imports (`2fd0a57`) |
| `find_spec("google.colab")` raised | crashed outside Colab | `in_colab()` helper |
| Absolute paths in logs/reports | leaked local user paths (F5) | Names/relative paths only; hygiene scan before packaging |
| D-018 population | Removing a feature creates new duplicates | Exclude eval twins per input view; common population; report both populations |
| AE convergence | Ablated AE hit the 100-epoch cap (best 98) | Recorded as limitation; consider higher cap or more seeds in future ablations (needs approval) |
| SHAP batch dependence | float32 CPU matmul rounding changed a tree split depending on batch | Evaluate composite in float64 (batch-invariant, tested) |
| Float32 vs float64 | 16 test rows differ by > 1e-3 log-odds; predictions identical | Documented (D-019); explanations are of the float64 evaluation |
| shap version | shap ≥ 0.50 requires numpy ≥ 2 | Pinned shap 0.49.1 |
| Missing flag-count evidence | Registry built from the 6-page papers only; extended web documentation not consulted; ACK/PSH (SHAP ranks 1 and 4) missed | Check supplementary/extended documentation of every forensic source before assigning levels (§8) |
| Test-set-driven selection | SHAP rankings on test rows | Pre-register ablation groups from the literature; compute rankings on train/val for selection |
| Phase II over-claims | e.g. 43 features, 2.83M flows, global min_seg_size_forward, "no CV" claims | Use the paper audit's corrections; cite tables/pages |
| Heredoc quoting | Bash heredoc with apostrophes failed; Python `read_text` turned a lone `\r` into a newline in a path | Write scripts with the Write tool; check generated text |
| Stale docs after edits | D-015 still says "none in effect" | Re-read the whole entry after editing a decision |

---

## 16. Quality assurance of this document

Checked against the repository during this handover:

- **Commits:** all 15 hashes and messages taken from `git log` at HEAD `fbd10cd`.
- **Paths:** every repo path named in §3.5, §6, §7 listed by `git ls-files` or `ls` (ignored artifacts: `results/runs/*`, `results/splits/*`, `results/benchmarks/*`, SHAP `.npz`, `data/raw/*`, review ZIPs). External: `../project/*.pdf` (listed), Downloads documents (listed; not in repo).
- **Metrics:** taken from `results/baselines/…/metrics.json`, `results/ablations/…/metrics.json`, `results/comparisons/…-vs-full.json`, run records, `ae_done.json`, `docs/DIAGNOSTIC_D008_SHORTCUTS.md`, SHAP `summary.json`/`stability_all_variants.json`, and `docs/MILESTONE_2A_REPORT.md`.
- **Dataset facts:** from `configs/datasets.yaml` (read programmatically) and the decision log.
- **Paper facts:** from `CNET_FULL_PAPER_AUDIT.md` and the Phase II PDF text (extracted with `pdftotext`); not re-read from the paper PDFs in this session.
- **CLI flags:** from `argparse` definitions in `src/`.
- **Tests:** 122 collected (per-file counts from `pytest --collect-only`); 122 passed earlier on 2026-11-08 at the same HEAD.
- **Secrets / personal data:** none included (no passwords, tokens, emails or registration details). Author names come from the Phase II title block. The project root path is included once because the handover requires it.
- **UNKNOWN / unavailable:** Phase III/IV briefs and rubric; team roles; Milestone 2A review text; Engelen extended documentation content; [4]–[6] papers.
