"""Pre-register Milestone 3A ablation groups and matched controls (TRAIN partition only).

Deterministic: proxy clusters from exact equality or |r| >= 0.999 on train; random controls
drawn from non-registered clusters with RandomState(3000 + 100*g + j); difficulty-matched
controls by train-only univariate separability |AUROC - 0.5|. No validation/test rows, no model
output, no SHAP value is read.

    .\run.cmd scripts/freeze_ablation_groups_3a.py            # print YAML
    .\run.cmd scripts/freeze_ablation_groups_3a.py --check    # compare with the frozen file

The frozen output is configs/protocol/ablation_groups_3a.yaml (Milestone 3A). Never regenerate
it after 3A training starts; --check only confirms it is reproducible from the data.
"""
import json
import sys
from pathlib import Path

import numpy as np
import yaml
from sklearn.metrics import roc_auc_score

root = Path(__file__).resolve().parents[1]
FROZEN = root / "configs/protocol/ablation_groups_3a.yaml"
sys.path.insert(0, str(root))
from src.data import ddos  # noqa: E402

PROXY_R = 0.999
N_RANDOM = 5
csv, _ = ddos.verified_csv(root)
prep = ddos.prepare(ddos.load(csv), {"BENIGN": 0, "DDoS": 1})
pre = json.loads((root / "results/runs/ae_xgb_d008_trackB-seed0-cpu-565a8b9e/preprocessor.json").read_text())
inputs = pre["numeric_cols"]
tr = prep.split.train
X = prep.frame.iloc[tr][inputs].replace([np.inf, -np.inf], np.nan).astype(float)
X = X.fillna(X.median())
y = prep.y[tr]

# proxy clusters (union-find)
parent = {c: c for c in inputs}
def find(c):
    while parent[c] != c:
        c = parent[c]
    return c
corr = X.corr().abs().fillna(0)
for i, a in enumerate(inputs):
    for b in inputs[i + 1:]:
        if np.array_equal(X[a].to_numpy(), X[b].to_numpy()) or corr.loc[a, b] >= PROXY_R:
            parent[find(b)] = find(a)
clusters = {}
for c in inputs:
    clusters.setdefault(find(c), []).append(c)
cluster_of = {c: tuple(sorted(clusters[find(c)])) for c in inputs}

sep = {c: abs(roc_auc_score(y, X[c].to_numpy()) - 0.5) for c in inputs}

reg = yaml.safe_load((root / "configs/artifact_registry.yaml").read_text(encoding="utf-8"))
level = {"direct_extraction_error": "direct", "shortcut_indicator": "shortcut", "unverified_hypothesis": "hypothesis"}
by_source = {"flag": set(), "appendix": set(), "duplication": set(), "hypothesis": set()}
for f in reg["features"]:
    for m in f.get("mechanisms", [f]):
        refs = {s["ref"] for s in m.get("sources", [])}
        cols = set(f["columns"])
        if level[m["evidence_level"]] == "direct" and "engelen_extended" in refs:
            by_source["flag"] |= cols
        elif level[m["evidence_level"]] == "shortcut" and "engelen2021" in refs:
            by_source["appendix"] |= cols
        elif level[m["evidence_level"]] == "direct" and "lanvin2023" in refs:
            by_source["duplication"] |= cols
        elif level[m["evidence_level"]] == "hypothesis":
            by_source["hypothesis"] |= cols
avail = set(inputs)
def closure(cols):
    out = set()
    for c in cols & avail:
        out |= set(cluster_of[c])
    return out

groups = {
    "A_flag_defects": sorted(by_source["flag"] & avail),
    "B_appendix_literal": sorted(by_source["appendix"] & avail),
    "B_appendix_closed": sorted(closure(by_source["appendix"])),
    "C_duplication": sorted(closure(by_source["duplication"])),
    "D_metadata_hypothesis": sorted(closure(by_source["hypothesis"])),
}
groups["U_documented_union"] = sorted(set(groups["A_flag_defects"]) | set(groups["B_appendix_closed"]) | set(groups["C_duplication"]))
for g in ("A_flag_defects", "C_duplication", "D_metadata_hypothesis"):
    assert set(groups[g]) == closure(set(groups[g])), f"{g} not proxy-closed"
registered_closed = closure(by_source["flag"] | by_source["appendix"] | by_source["duplication"] | by_source["hypothesis"])
pool_clusters = sorted({cluster_of[c] for c in avail - registered_closed})
pool_cols = sorted({c for cl in pool_clusters for c in cl})

def random_control(n, seed):
    rng = np.random.RandomState(seed)
    order = rng.permutation(len(pool_clusters))
    chosen, total = [], 0
    for i in order:
        cl = pool_clusters[i]
        if total + len(cl) <= n:
            chosen += list(cl)
            total += len(cl)
        if total == n:
            return sorted(chosen)
    raise ValueError(f"cannot match size {n}")

def matched_control(group):
    used, chosen = set(), []
    gcl = sorted({cluster_of[c] for c in group}, key=lambda cl: -max(sep[c] for c in cl))
    for cl in gcl:
        target = max(sep[c] for c in cl)
        cands = [p for p in pool_clusters if p not in used and len(p) == len(cl)]
        if not cands:
            cands = [p for p in pool_clusters if p not in used and len(p) <= len(cl)]
        best = min(cands, key=lambda p: (abs(max(sep[c] for c in p) - target), p))
        used.add(best)
        chosen += list(best)
    while len(chosen) < len(group):                       # top up singletons if needed
        rest = [p for p in pool_clusters if p not in used and len(p) == 1]
        best = rest[0]
        used.add(best)
        chosen += list(best)
    return sorted(chosen)

primary = ["A_flag_defects", "B_appendix_closed", "C_duplication", "D_metadata_hypothesis", "U_documented_union"]
out = {
    "protocol": "Milestone 3A pre-registered ablation groups (frozen before any 3A training)",
    "generated_from": {"split_fingerprint": prep.split.fingerprint() if callable(getattr(prep.split, "fingerprint", None)) else None,
                       "partition": "train only", "n_train_rows": int(len(tr)), "inputs": len(inputs),
                       "registry_version": reg.get("registry_version"),
                       "proxy_rule": f"exact equality or |pearson r| >= {PROXY_R} on train (after train-median imputation)",
                       "random_seed_rule": "RandomState(3000 + 100*group_index + draw_index), group_index in primary order",
                       "separability": "|ROC AUC(train label, raw train column) - 0.5|"},
    "proxy_clusters_multi": [list(cl) for cl in sorted({cluster_of[c] for c in inputs}) if len(cl) > 1],
    "groups": {g: {"columns": groups[g], "size": len(groups[g])} for g in groups},
    "overlaps": {"A_flag_defects & B_appendix_closed": sorted(set(groups["A_flag_defects"]) & set(groups["B_appendix_closed"]))},
    "unavailable_after_train_only_preprocessing": sorted((by_source["flag"] | by_source["appendix"] | by_source["duplication"] | by_source["hypothesis"]) - avail),
    "control_pool": {"columns": pool_cols, "n_columns": len(pool_cols), "n_clusters": len(pool_clusters)},
    "controls": {},
    "separability_train": {c: round(float(sep[c]), 4) for c in inputs},
}
for gi, g in enumerate(primary):
    n = len(groups[g])
    out["controls"][g] = {
        "random": [random_control(n, 3000 + 100 * gi + j) for j in range(N_RANDOM)],
        "difficulty_matched": matched_control(groups[g]),
        "group_mean_separability": round(float(np.mean([sep[c] for c in groups[g]])), 4),
    }
    out["controls"][g]["difficulty_matched_mean_separability"] = round(float(np.mean([sep[c] for c in out["controls"][g]["difficulty_matched"]])), 4)
    out["controls"][g]["random_mean_separability"] = [round(float(np.mean([sep[c] for c in r])), 4) for r in out["controls"][g]["random"]]
    for ctl in out["controls"][g]["random"] + [out["controls"][g]["difficulty_matched"]]:
        assert len(ctl) == n and not set(ctl) & registered_closed and set(ctl) == closure(set(ctl)), (g, ctl)
text = yaml.safe_dump(out, sort_keys=False, width=110, allow_unicode=True)
if "--check" in sys.argv[1:]:
    frozen = yaml.safe_load(FROZEN.read_text(encoding="utf-8"))
    if frozen != yaml.safe_load(text):
        raise SystemExit("frozen groups do NOT reproduce from the data")
    print("frozen groups reproduce exactly from the training partition")
else:
    print(text, end="")
