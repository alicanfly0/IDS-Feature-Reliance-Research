# Colab session 2: clean preflight (verification only)

These are actual Colab outputs, downloaded by the user from `MyDrive/cnet-runs/preflight/` as
`colab_session2.zip` and extracted here unchanged. Nothing was reconstructed.

- **Code:** commit `659c35d8349e4393e8c43ebda0d1ecd0391a414e` (git-archive bundle), session time
  2026-11-11T16:06:20Z.
- **Integrity:** all 7 files match the session's own `MANIFEST.json` SHA-256 values (checked on the
  laptop). No credentials or personal paths.
- **Environment check:** compatible with `configs/environments/colab_env_v1.yaml`; nothing was
  installed, nothing fatal.
- **Tests before data:** 167 passed, 12 skipped, 0 failed.
- **Tests with data:** 171 passed, 8 skipped, 0 failed. The skips are expected: local run folders,
  SHAP arrays, UNSW data, and git history (archive mode).
- **Split and population:** split `50bd9948…` reproduced; family-common validation 33,134 and test
  33,038 rows reproduced.
- **Dataset:** `MachineLearningCSV.zip` checksum OK.
- **Dry run:** 110 fits, 0 done.
- **No training:** the benchmark, legacy run and 3B batch cells were all disabled. No research run
  and no benchmark happened.

This session verifies the execution environment and data consistency only. It does not validate
the statistical assumptions, and it does not approve any research decision.
