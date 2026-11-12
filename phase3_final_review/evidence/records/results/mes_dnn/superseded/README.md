# Superseded: duplicate-aware partitioner v1 (kept for transparency, not used)

`dup_aware_v1/` holds the first five duplicate-aware fits (2026-11-11). Partitioner v1 placed
whole duplicate groups in a random cumulative order. NF-ToN-IoT-v2 has giant groups (one benign
vector x 422,766 rows = 17.7 % of the subsample; one attack vector x 249,048 rows), so v1 produced
partitions with distorted class mixes. For example, the meta sample was 100 % attack in seeds 0
and 2, and 7.3 % attack in seed 1 (network share 64 %). Those fits therefore measure partition skew,
not duplicate leakage.

Replaced by v2: groups placed largest-first into the partition with the largest remaining row
deficit, per class. Each vector still sits in exactly one partition, and class mixes match the
targets. The random-mode fits did not use this code and are unaffected.
