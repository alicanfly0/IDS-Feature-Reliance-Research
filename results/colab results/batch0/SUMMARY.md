# Milestone 3B batch 0: full model, seeds 0–9 (Colab T4, code 659c35d)

**Source:** read from the Colab notebook output of
`python -m src.evaluation.aggregate_3b --storage <cnet-runs>` on 2026-11-11. The full aggregate
JSON is on Drive at `cnet-runs/aggregate/batch0.json`. The run folders stay on Drive.

- **Runtime:** the batch cell ran for 19 min (about 1.9 min per fit), with no error.
- **Checks passed:** 10/110 runs aggregated on identical test rows (33,038); one training
  environment (fingerprint `be81b4d6da06…`, 10 runs); every run matched its committed config.

| Seed | Errors | Error rate | MCC | Log loss |
|---|---|---|---|---|
| 0 | 8 | 0.000242 | 0.999502 | 0.000978 |
| 1 | 6 | 0.000182 | 0.999627 | 0.000783 |
| 2 | 6 | 0.000182 | 0.999627 | 0.000684 |
| 3 | 6 | 0.000182 | 0.999627 | 0.000925 |
| 4 | 7 | 0.000212 | 0.999564 | 0.000972 |
| 5 | 3 | 0.000091 | 0.999813 | 0.000679 |
| 6 | 4 | 0.000121 | 0.999751 | 0.000648 |
| 7 | 5 | 0.000151 | 0.999689 | 0.001070 |
| 8 | 8 | 0.000242 | 0.999502 | 0.000806 |
| 9 | 5 | 0.000151 | 0.999689 | 0.000939 |

**Summary:** mean 5.8 errors (range 3–8), mean MCC ≈ 0.99964. These are reference runs only; no
group or control comparison exists yet.
