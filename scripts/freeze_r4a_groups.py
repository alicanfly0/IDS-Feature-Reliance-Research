"""Freeze the R4a-ii groups and controls on the CORRECTED training partition (D-005, D-024).

    .\\run.cmd scripts/freeze_r4a_groups.py            # print YAML
    .\\run.cmd scripts/freeze_r4a_groups.py --check    # compare with configs/protocol/r4a_groups_v1.yaml

Train-only: proxy clusters, closure, separability and inputs come from the corrected training
partition after the runner's train-only preprocessing. Primary groups A, B (closed), U; 10 random
controls each with RandomState(7000 + 100*group_index + draw). Same algorithm as protocol r1
(src/audit/groups.py, proven to reproduce r1 on the original data).
"""
import sys
from pathlib import Path

import yaml

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))
from src.audit import groups as G  # noqa: E402
from src.audit.registry import load_registry  # noqa: E402
from src.config import load_config, make_preprocessor  # noqa: E402
from src.data import ddos, engelen  # noqa: E402

CONFIG = root / "configs/experiments/ae_xgb_r4a_trackB.yaml"
FROZEN = root / "configs/protocol/r4a_groups_v1.yaml"
PRIMARY = ["A_flag_defects", "B_appendix_closed", "U_documented_union"]
SEED_BASE = 7000

cfg = load_config(CONFIG)
df, prov = engelen.load(root)
prep = ddos.prepare(df, cfg["data"]["label_map"], tuple(cfg["experiment"]["split"]["fractions"]),
                    cfg["experiment"]["split"]["seed"], tuple(cfg["data"]["nonnegative_cols"]))
assert prep.split.fingerprint() == cfg["experiment"]["split"]["expected_fingerprint"], prep.split.fingerprint()
train = prep.frame.iloc[prep.split.train]
pre = make_preprocessor(cfg)
pre.fit(train)
inputs = list(pre.numeric_cols_)
out = {"protocol": "R4a-ii (D-024) groups and controls, frozen from the corrected TRAIN partition before any R4a training",
       "generated_from": {"dataset": "Engelen WTMC2021 Friday, aligned original DDoS window (D-005)",
                          "split_fingerprint": prep.split.fingerprint(), "partition": "train only",
                          "n_train_rows": int(len(train)), "inputs": len(inputs),
                          "constant_on_train": list(pre.constant_cols_),
                          "proxy_rule": f"exact equality or |pearson r| >= {G.PROXY_R} on train (after train-median imputation)",
                          "random_seed_rule": f"RandomState({SEED_BASE} + 100*group_index + draw_index), group order {PRIMARY}",
                          "separability": "|ROC AUC(train label, raw train column) - 0.5|"},
       "model_inputs": inputs,
       **G.build(train, prep.y[prep.split.train], inputs, load_registry(), PRIMARY, 10, SEED_BASE)}
out["groups"] = {g: out["groups"][g] for g in PRIMARY}          # only the R4a groups are part of the design
text = yaml.safe_dump(out, sort_keys=False, width=110, allow_unicode=True)
if "--check" in sys.argv[1:]:
    if yaml.safe_load(FROZEN.read_text(encoding="utf-8")) != yaml.safe_load(text):
        raise SystemExit("R4a frozen groups do NOT reproduce from the data")
    print("R4a frozen groups reproduce exactly from the corrected training partition")
else:
    print(text, end="")
