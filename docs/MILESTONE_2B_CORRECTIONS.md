# Milestone 2B — scientific correction (2026-11-09)

## Status and evidence

The original Milestone 2A registry omitted a documented TCP flag-count defect. Registry v2 adds eleven feature entries and adds a second mechanism to SYN Flag Count, preserving all original classifications. The original registry is archived byte-for-byte at `configs/history/artifact_registry_v1.yaml`. No original experiment output was edited.

Evidence: [Engelen official extended documentation](https://intrusion-detection.distrinet-research.be/WTMC2021/extended_doc.html), **Flow Construction / TCP flag count**. This HTML source has no page number. The detailed evidence record is `docs/evidence/engelen_extended_2026-11-09.md`.

Affected schema family: FIN, SYN, RST, PSH, ACK, URG, CWE and ECE Flag Count; Fwd PSH Flags, Bwd PSH Flags, Fwd URG Flags and Bwd URG Flags. Aggregate counts only update for the first packet. Directional increment defects are separately documented; their exact code path and fix date are not supplied. CWE is the original schema spelling; its inclusion follows the documented aggregate family, not an explicit spelling in the source.

The page scopes its findings to original CICIDS2017 CSVs, which includes this Friday DDoS release. This is documented measurement susceptibility, not identification of corrupt rows. Single-packet or flag-absent flows may be numerically correct. No packet reconstruction or corrected-row correspondence exists here. Zero-on-train counters receive no attribution but remain in the registry. The absolute-timestamp bug on that page explicitly excludes original CICIDS2017 and does not justify promoting Active/Idle fields.

SYN retains its paper-backed appendix shortcut mechanism while also entering the extraction-error set. Sets may overlap; the union deduplicates columns. Hypothesis-only excludes features with supported mechanisms. Lanvin classifications and the forward-window/appendix shortcut evidence remain unchanged.

## Versioned calculation and provenance

`results/corrections/milestone2b/corrected_arr_v2.json` is computed from the existing six arrays, cast from float32 storage to float64 for arithmetic. Its SHA-256 references identify the registry, previous registry, settings, and arrays. Each variant contains the actual sampling settings and IDs, full rankings, all tier memberships, old/new tables, differences and newly added top-K members. ARR is the top-K sum of mean absolute SHAP contributions belonging to a tier divided by all top-K importance. Ties are ordered by feature name. Zero denominators return NaN in the generic function; none occur here.

The primary aggregation remains the historical sum of individual mean absolute importances for continuity. The alternative signed-per-row aggregation is also fully reported. Cached summaries retain registry-v1 numbers: do not run the old SHAP launcher to obtain corrected tables. Use:

```powershell
.\run.cmd -m src.audit.correct_arr --verify
```

Creation uses the same command without `--verify` and refuses to overwrite existing corrected outputs. This command imports neither SHAP nor model/training code. Independent verification calculates the memberships and numerator/denominator separately from the production ARR function. Historical stored float64 summaries and recomputed float32-array importances differ by at most 6e-9.

## Corrected ARR@K for every variant

Values below are percentages; each cell is **extraction / shortcut / hypothesis-only / union**. Variant IDs are the full names in the JSON; concise names encode background-size/seed, explained-sample seed and permutation budget.

| Background size/seed; sample seed; permutations | K=2 | K=5 | K=10 | K=20 |
|---|---|---|---|---|
| 100/0; 0; 10 | 57.915 / 0.000 / 0.000 / 57.915 | 45.130 / 0.000 / 0.000 / 45.130 | 28.175 / 7.592 / 8.665 / 44.431 | 22.198 / 8.208 / 5.964 / 36.369 |
| 100/0; 0; 5 | 58.407 / 0.000 / 0.000 / 58.407 | 45.288 / 0.000 / 14.323 / 59.611 | 28.325 / 7.369 / 8.958 / 44.652 | 21.908 / 8.107 / 6.099 / 36.114 |
| 100/0; 1; 5 | 54.991 / 0.000 / 0.000 / 54.991 | 43.689 / 0.000 / 0.000 / 43.689 | 27.504 / 6.761 / 8.330 / 42.595 | 21.607 / 7.369 / 5.695 / 34.672 |
| 100/1; 0; 5 | 60.807 / 0.000 / 0.000 / 60.807 | 46.075 / 0.000 / 14.606 / 60.680 | 28.680 / 7.343 / 9.092 / 45.115 | 21.901 / 8.672 / 6.236 / 36.809 |
| 100/1; 1; 5 | 57.432 / 0.000 / 0.000 / 57.432 | 44.862 / 0.000 / 0.000 / 44.862 | 27.450 / 0.000 / 8.484 / 35.934 | 21.297 / 7.854 / 5.857 / 35.007 |
| 200/0; 0; 5 | 59.376 / 0.000 / 0.000 / 59.376 | 45.863 / 0.000 / 0.000 / 45.863 | 28.950 / 7.423 / 8.230 / 44.603 | 22.096 / 8.307 / 5.586 / 35.989 |

## Old versus new at K=20

Same saved arrays and historical aggregation isolate the registry correction. The earlier ACK/PSH-only estimate was incomplete: URG Flag Count also belongs to the documented defect family and enters the top 20. No other newly registered flag feature enters any requested top-K.

| Variant (same order as above) | V1 extraction | V2 extraction | V1 union | V2 union |
|---|---|---|---|---|
| 100/0; 0; 10 | 0.000% | 22.198% | 14.172% | 36.369% |
| 100/0; 0; 5 | 0.000% | 21.908% | 14.206% | 36.114% |
| 100/0; 1; 5 | 0.000% | 21.607% | 13.065% | 34.672% |
| 100/1; 0; 5 | 0.000% | 21.901% | 14.908% | 36.809% |
| 100/1; 1; 5 | 0.000% | 21.297% | 13.711% | 35.007% |
| 200/0; 0; 5 | 0.000% | 22.096% | 13.893% | 35.989% |

Shortcut and hypothesis-only scores do not change. Extraction ARR@20 is now 21.297–22.198%; union ARR@20 is 34.672–36.809%. The earlier zero direct-error and 13–15% union statements describe registry v1 only. The new result is increased attribution concentration on documented susceptible measurements, not increased measured classification error or proof of causal artifact reliance.

## Duplicate-column sensitivity

For duplicate columns a and b, historical importance is mean(|phi_a|)+mean(|phi_b|); signed grouping is mean(|phi_a+phi_b|), no larger by the triangle inequality.

| Variant | Historical importance | Signed importance | Historical rank | Signed rank |
|---|---|---|---|---|
| 100/0; 0; 10 | 0.05810219 | 0.05582761 | 41 | 41 |
| 100/0; 0; 5 | 0.05655877 | 0.05168431 | 42 | 42 |
| 100/0; 1; 5 | 0.05801471 | 0.05473161 | 42 | 43 |
| 100/1; 0; 5 | 0.04199703 | 0.03804457 | 44 | 44 |
| 100/1; 1; 5 | 0.04083577 | 0.03809583 | 45 | 45 |
| 200/0; 0; 5 | 0.05251020 | 0.04837339 | 42 | 42 |

All K=2,5,10,20 top-K lists and ARR values are unchanged across these two aggregation conventions in all six variants. One rank changes from 42 to 43. Signed grouping expresses net contribution and cancels opposing signs; historical aggregation expresses total individual attribution magnitude. Neither is a group Shapley calculation: masked duplicate columns can become inconsistent and off-manifold. Post-hoc merging cannot repair correlated-feature masking. Preserve both conventions; a future joint-mask experiment would require its own methodological decision and computation.

## Float32/float64 qualification

`docs/evidence/precision_comparison_2a.json` is extracted unchanged from the existing review ZIP, not newly measured. Its method compares the same trained weights, with the encoder evaluated in double precision and its latent output cast back to float32 for the saved XGBoost. Preprocessing still returns float32 before that cast. This is a numerically different evaluation function. It is not an exact explanation of the original float32 implementation.

Archived measurements on 33,877 test rows: float32 probability versus saved output max difference 8.63136e-8; float64 versus saved output 0.0008868888; float64 versus float32 max margin difference **1.570897579**; 16 margins differ by more than 0.001. Predicted classes match throughout. Background-50 batch comparison differs by 0.0826931 in float32 and 0 in float64; background-100 comparison is zero for both in that check. These are finite tested cases, not a proof of global batch invariance. Identical classes constrain only the side of the threshold, not margins, substituted-flow outputs, or SHAP values. We cannot bound attribution discrepancies from predicted-class agreement. No float32/float64 SHAP sensitivity sweep was conducted. ARR therefore describes the existing float64-encoder evaluation pilot under its recorded masking scheme.

## Exploratory and confirmatory boundaries

The pilot explained test rows and exposed their feature rankings. Removing the resulting top five and evaluating on those same rows is exploratory; the historical 2A recommendation must not be presented as confirmatory. A later validation-only ranking also cannot restore this already inspected test set to pristine status.

Before further training, prerecord literature-defined groups (flag-count measurement defects; Engelen appendix indicators; Lanvin duplication-affected features), explicit overlaps and size-matched controls; use independent capture/session/temporal evaluation or reserve new evaluation data untouched by group selection. Any selection by attribution belongs entirely in development partitions, with a frozen final evaluation population. Predefine seeds, stopping, metrics, uncertainty, multiplicity treatment and resource bounds. Original-versus-corrected testing needs D-004/D-005 schema and attempted-label decisions; cross-dataset transfer needs D-006. For ablations follow D-018: keep training rows and original split, exclude evaluation twins for every reduced input view, compare models on a declared common intersection and report exclusions/class shifts. Validation exclusions can alter early-stopping populations and must be disclosed or aligned prospectively. No ablation is started here.

McNemar p=0.625 in D-018 remains a low-power, single-seed non-significant comparison, not proof of equivalence. ARR is attribution concentration, not a causal or row-corruption metric. Rankings remain numerically those of the original pilot; their evidence labels changed.

## Verification and remaining decisions

See `results/corrections/milestone2b/verification.json` for executed tests and integrity records. The correction reads all six arrays, checks dimensions, source-row alignment, finiteness, stored additivity, historical importance consistency, independent ARR calculations and SHA-256 equality for 96 protected artifacts. No training of research models, SHAP recomputation or cloud transfer was performed. Synthetic model fixtures may run as part of the pre-existing test suite.

Next milestone should freeze an experimentally defensible ablation/generalization protocol and resolve the open dataset/statistical decisions before any resource-intensive runs. Additional model seeds, corrected-capture alignment and uninspected session evaluation remain outstanding. PKR 0 and Colab Free apply to expensive work.


### Executed checks and environment blocker

- Eight new correction tests pass (0.35 s). The independently implemented NumPy script
  `.\run.cmd scripts/verify_m2b_arr.py` verifies all 192 ARR values (6 variants × 2 methods × 4 K × 4 tiers),
  max absolute discrepancy 5.55e-17. Full Top-K orders also agree.
- All 96 protected original files match their pre-correction SHA-256 hashes.
- Full-suite collection is blocked by Windows Application Control refusing PyTorch `shm.dll` and
  compiled Numba modules. Retrying outside the sandbox reproduces those restrictions.
- A broad attempt with the two uncollectable modules omitted gave 96 passes and 4 failures,
  all four importing the blocked PyTorch library. After the final additional test, explicitly
  excluding those four cases gives **97 passed, 4 deselected**, with 29 tests in the two omitted
  modules. This does not establish a full-suite pass. Earlier 122-pass counts are historical.
- Temporary-file rename failures in sandboxed acquisition tests disappear outside the sandbox.
  No dependency reinstall, security-policy alteration, or conditional hiding of failures was added.

To close the test blocker: rerun the unchanged full suite in an environment permitted to load the
installed PyTorch and Numba binaries (or obtain user/administrator resolution of the Windows policy).
No Colab upload or security-policy change is authorized by this verification task.
The new postprocessing path requires neither of those libraries and is verified end to end here.

Implementation, evidence, tests and versioned numerical records: commit `037cb61`. The following documentation commit marks the original 2A interpretation historical and records the revised protocol boundaries.
