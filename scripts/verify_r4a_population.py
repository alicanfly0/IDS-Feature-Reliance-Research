"""R4a-ii family-common evaluation population over all 34 R4a views (D-005). Read-only, no model.

    .\run.cmd scripts/verify_r4a_population.py            # print summary
    .\run.cmd scripts/verify_r4a_population.py --write    # results/protocol/r4a/eval_population_r4a_v1.json (no overwrite)
"""
import json
import sys
from pathlib import Path

import yaml

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))
from src.config import load_config  # noqa: E402
from src.data import ddos, engelen  # noqa: E402
from src.experiments.population import compute_family_common, lf_sha256  # noqa: E402

CONFIG = root / "configs/experiments/ae_xgb_r4a_trackB.yaml"
GROUPS = root / "configs/protocol/r4a_groups_v1.yaml"
OUT = root / "results/protocol/r4a/eval_population_r4a_v1.json"

cfg = load_config(CONFIG)
df, prov = engelen.load(root)
prep = ddos.prepare(df, cfg["data"]["label_map"], tuple(cfg["experiment"]["split"]["fractions"]),
                    cfg["experiment"]["split"]["seed"], tuple(cfg["data"]["nonnegative_cols"]))
assert prep.split.fingerprint() == cfg["experiment"]["split"]["expected_fingerprint"]
g = yaml.safe_load(GROUPS.read_text(encoding="utf-8"))
views = {"full": []}
for name, spec in g["groups"].items():
    views[name] = spec["columns"]
    views.update({f"{name}/random{j}": r for j, r in enumerate(g["controls"][name]["random"])})
rec = compute_family_common(cfg, prep, views)
rec.update({"milestone": "R4a-ii family-common population (D-005, D-024)", "frozen_groups_file": str(GROUPS.relative_to(root)).replace("\\", "/"),
            "frozen_groups_sha256_lf": lf_sha256(GROUPS), "data_provenance": prov})
for k, v in rec["views"].items():
    print(f"{k:34s} inputs={v['model_inputs']:2d} model val/test {v['model_val']:4d}/{v['model_test']:4d} extra {v['extra_val']}/{v['extra_test']}")
p = rec["family_common_model_visible"]
print(f"family-common: val {p['val_kept']} (excl {p['val_excluded']}, DDoS {p['val_excluded_ddos']}); "
      f"test {p['test_kept']} (excl {p['test_excluded']}, DDoS {p['test_excluded_ddos']}); test DDoS {p['test_kept_ddos']} / BENIGN {p['test_kept_benign']}")
if "--write" in sys.argv[1:]:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("x", encoding="utf-8") as f:
        json.dump(rec, f, indent=1)
        f.write("\n")
    print("wrote", OUT.relative_to(root))
