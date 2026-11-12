# R4a results and analysis notes (2026-11-12)

Internal analysis record. **Not paper text**: the paper sections are written only after
the authors' writing guidance. Every number below comes from `stats_r4a.json`,
`aggregate_r4a.json` or `r4a_i_scores.json` in this folder.

## Provenance

| Item | Value |
|---|---|
| Code commit | `b6297226d6dc0eb946603fc2f66c44b8db816fee` (bundle `cnet_code_b6297226d6dc.zip`) |
| Environment | Colab, Tesla T4, CUDA 13.0, torch 2.14.1+cu130, xgboost 3.4.1; fingerprint `be81b4d6…fbdb1a8b`, the **same fingerprint as the r1 main experiment** |
| Runs | 70/70 (`aggregate_3b`: "70/70 runs aggregated on identical test rows"), all `cuda` |
| R4a-ii test population | 22,049 rows, Engelen corrected Friday (family-common) |
| R4a-i | 110 r1 models scored on the same 22,049 rows (14,168 DDoS) |
| File SHA-256 | `aggregate_r4a.json` 3ac5e226…7c2c; `r4a_i_scores.json` deb00f46…3ae4 (byte-identical to the Colab copies) |

### Execution deviations (operational, not protocol)

- The 13 laptop-CPU R4a fits from the morning were **not used**: all 70 fits ran in the one Colab environment.
- Storage was the Colab account's own Drive (`cnet-r4a/`); the r1 models were read through a Drive shortcut (read-only).
- That Drive hit its 5 GB quota during the campaign, so some files never reached Drive:
  - **Eight runs were retrained:** `Actl2`–`Actl8` (batch 2, group-A controls) after their broken folders were moved to `cnet-r4a/quarantine/`, and `Actl9` on the VM's local disk.
  - Each retrain used the same config, seed, code and environment; the runner uses deterministic run IDs.
  - The broken first attempts were incomplete and were never scored, so no result was selected among attempts.
  - Aggregation and R4a-i scoring ran on the VM's local disk (`/content/r4a_local`).
- Four runs (`A-seed8`, `A-seed9`, `Actl0`, `Actl1`) lack only `latent.npz`. This is a training cache that aggregation does not read; all their scored artifacts are present.
- The run folders themselves stay on Colab/Drive (about 2 GB). Only the analysis records are in the repository, the same as for r1.

## R4a-ii (primary family, D-024): group removal on corrected data

Design D as in r1. The estimand is d = Δ_group − Δ_control on the error rate. Tests are exact sign-flip, Holm over 3, SESOI 0.001.

| Group (inputs removed) | mean Δ group | mean Δ control | mean d [95% interval] | p exact | p Holm | Reading |
|---|---|---|---|---|---|---|
| A: TCP flag-count defects (9) | +0.000005 | +0.000009 | −0.000005 [−0.000051, +0.000042] | 1.000 | 1.000 | practical equivalence at the SESOI |
| B: TCP appendix (8) | +0.000000 | −0.000014 | +0.000014 [−0.000021, +0.000048] | 0.453 | 1.000 | practical equivalence at the SESOI |
| U: union (20) | −0.000018 | −0.000000 | −0.000018 [−0.000085, +0.000048] | 0.641 | 1.000 | practical equivalence at the SESOI |

**Full model (10 seeds, 22,049 rows):**
- errors per seed: 2, 2, 2, 1, 3, 1, 2, 2, 1, 2 (mean 1.8);
- FP 1.5, FN 0.3 (means);
- MCC 0.99982 (range 0.99970–0.99990).

**Raw error counts:**

| Group | Group-removed models, per seed | Matched controls, per seed |
|---|---|---|
| A | 1, 3, 0, 2, 4, 2, 2, 1, 2, 2 | 2, 2, 1, 1, 2, 3, 2, 2, 2, 3 |
| B | 0, 2, 2, 2, 3, 2, 1, 2, 2, 2 | 1, 1, 1, 2, 2, 1, 1, 2, 3, 1 |
| U | 2, 2, 2, 2, 0, 2, 1, 1, 1, 1 | 1, 2, 1, 1, 4, 1, 2, 2, 2, 2 |

**Reading:**
- On the corrected capture, removing any documented-defect group costs nothing measurable relative to a size-matched random removal.
- All three intervals lie well inside ±SESOI, so this is **positive evidence of equivalence**, not just "not significant".
- The secondary endpoints (MCC, log loss) show no signal either: all sign-flip p ≥ 0.22, descriptive.

## Original vs corrected (observational, descriptive only)

Composition, segmentation, label windows, populations and definitions differ between the datasets (D-024). The intervals are Welch, for the mean d (corrected − original).

| Group | mean d original (r1) | mean d corrected | difference [Welch 95%] |
|---|---|---|---|
| A | +0.000097 | −0.000005 | −0.000101 [−0.000155, −0.000048] |
| B | −0.000012 | +0.000014 | +0.000026 [−0.000039, +0.000090] |
| U | +0.000182 | −0.000018 | −0.000200 [−0.000275, −0.000124] |

**Full-model error rate:**
- original: mean 0.000176 on 33,038 rows;
- corrected: mean 0.000082 on 22,049 rows.

**Reading:**
- The small r1 effects for A and U disappear on corrected data. In r1 they were Holm-significant but below the SESOI (about 3 and 6 extra errors).
- The direction is consistent with those r1 effects being tied to the defective extraction. It remains observational: the datasets differ in more than the defects.

## R4a-i (descriptive transfer, never read as artifact reliance)

The r1 models (trained on original CICIDS2017) were scored on the corrected rows. Definitions differ for ≥ 16 inputs. Values are mean [min, max] over 10 models per view.

| r1 view | DDoS recall | benign FPR | error rate | MCC |
|---|---|---|---|---|
| full | 0.088 [0.000, 0.879] | 0.023 | 0.594 | 0.017 |
| without A (flag defects) | **0.958** [0.800, 0.999] | 0.048 | 0.044 | 0.909 |
| without U (union A∪B∪C) | **0.994** [0.981, 1.000] | 0.0007 | 0.004 | 0.991 |
| without B | 0.000 [0.000, 0.000] | 0.0003 | 0.643 | −0.007 |
| without C | 0.158 [0.000, 0.830] | 0.041 | 0.555 | 0.068 |
| without D | 0.132 [0.000, 0.736] | 0.030 | 0.568 | 0.082 |
| controls (A, B, C, D, U) | 0.000–0.114 (means) | 0.012–0.081 | 0.595–0.652 | −0.084–0.031 |

An all-benign classifier would have an error rate of 14,168/22,049 = 0.643.

**Reading** (descriptive; candidate statement for the authors to decide on):
- **Full models.** The original near-perfect models mostly fail on the corrected capture: mean DDoS recall is 0.09 and they are close to all-benign. Their random-removal controls fail the same way.
- **Without A or U.** The only original models that transfer are those trained *without* the TCP flag-count features (A) or without the whole documented union (U). Their recall is 0.96 and 0.99 and their MCC 0.91 and 0.99.
- **Without B.** Removing B alone does not help: those models predict all-benign.
- **What this points to.** The full models' decision rules depend on the flag-count definitions that Engelen et al. corrected. This is the clearest result in the project for "99% accuracy rests on extractor artifacts".
- **Caveat.** Per D-024 it stays descriptive: input definitions changed, so this is a transfer result, not a controlled ablation. The very wide min–max ranges for the full models (0.00–0.88) show seed-level instability.

## Consequences for the paper (to discuss with the authors; nothing written yet)

- The R4a results subsection can now be filled. The table is generated at `paper/tables/r4a.tex`; it is **not** `\input` in `main.tex` yet.
- The abstract, conclusion and the discussion line on R4a can use:
  - (i) equivalence within corrected data (R4a-ii);
  - (ii) the r1 A/U effects disappearing, observationally;
  - (iii) the R4a-i transfer contrast between full and without-A/without-U models.
- Wording guards: "empirically supported +5:00 alignment assumption"; R4a-i is descriptive; no claim of source-paper reproduction.
