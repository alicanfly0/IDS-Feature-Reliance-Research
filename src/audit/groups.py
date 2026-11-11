"""Train-only ablation groups and random controls (the Milestone 3A algorithm, reusable).

Same rules as scripts/freeze_ablation_groups_3a.py (r0/r1, frozen): proxy clusters from exact
equality or |pearson r| >= 0.999 on the TRAINING partition after train-median imputation; groups
closed under those clusters; random controls drawn as whole non-registered clusters in the order of
RandomState(seed_base + 100*group_index + draw) until the group's column count is matched exactly.
tests/test_r4a.py proves this module reproduces the frozen r1 groups and draws on the original data.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

PROXY_R = 0.999


def registry_sets(reg: dict) -> dict[str, set]:
    by = {"flag": set(), "appendix": set(), "duplication": set(), "hypothesis": set()}
    for f in reg["features"]:
        for m in f.get("mechanisms", [f]):
            refs = {s["ref"] for s in m.get("sources", [])}
            lvl = m["evidence_level"]
            if lvl == "direct_extraction_error" and "engelen_extended" in refs:
                by["flag"] |= set(f["columns"])
            elif lvl == "shortcut_indicator" and "engelen2021" in refs:
                by["appendix"] |= set(f["columns"])
            elif lvl == "direct_extraction_error" and "lanvin2023" in refs:
                by["duplication"] |= set(f["columns"])
            elif lvl == "unverified_hypothesis":
                by["hypothesis"] |= set(f["columns"])
    return by


def proxy_clusters(train: pd.DataFrame, inputs: list[str]) -> dict[str, tuple]:
    x = train[inputs].replace([np.inf, -np.inf], np.nan).astype(float)
    x = x.fillna(x.median())
    parent = {c: c for c in inputs}

    def find(c):
        while parent[c] != c:
            c = parent[c]
        return c
    corr = x.corr().abs().fillna(0)
    for i, a in enumerate(inputs):
        for b in inputs[i + 1:]:
            if np.array_equal(x[a].to_numpy(), x[b].to_numpy()) or corr.loc[a, b] >= PROXY_R:
                parent[find(b)] = find(a)
    clusters = {}
    for c in inputs:
        clusters.setdefault(find(c), []).append(c)
    return {c: tuple(sorted(clusters[find(c)])) for c in inputs}


def separability(train: pd.DataFrame, y, inputs: list[str]) -> dict[str, float]:
    x = train[inputs].replace([np.inf, -np.inf], np.nan).astype(float)
    x = x.fillna(x.median())
    return {c: abs(roc_auc_score(y, x[c].to_numpy()) - 0.5) for c in inputs}


def build(train: pd.DataFrame, y, inputs: list[str], reg: dict, primary: list[str], n_random: int,
          seed_base: int) -> dict:
    cluster_of = proxy_clusters(train, inputs)
    avail = set(inputs)
    by = registry_sets(reg)

    def closure(cols):
        out = set()
        for c in set(cols) & avail:
            out |= set(cluster_of[c])
        return out
    groups = {"A_flag_defects": sorted(by["flag"] & avail), "B_appendix_closed": sorted(closure(by["appendix"])),
              "C_duplication": sorted(closure(by["duplication"])),
              "D_metadata_hypothesis": sorted(closure(by["hypothesis"]))}
    groups["U_documented_union"] = sorted(set(groups["A_flag_defects"]) | set(groups["B_appendix_closed"])
                                          | set(groups["C_duplication"]))
    registered_closed = closure(by["flag"] | by["appendix"] | by["duplication"] | by["hypothesis"])
    pool_clusters = sorted({cluster_of[c] for c in avail - registered_closed})

    def random_control(n, seed):
        order = np.random.RandomState(seed).permutation(len(pool_clusters))
        chosen, total = [], 0
        for i in order:
            cl = pool_clusters[i]
            if total + len(cl) <= n:
                chosen += list(cl)
                total += len(cl)
            if total == n:
                return sorted(chosen)
        raise ValueError(f"cannot match size {n}")
    sep = separability(train, y, inputs)
    controls = {}
    for gi, g in enumerate(primary):
        n = len(groups[g])
        draws = [random_control(n, seed_base + 100 * gi + j) for j in range(n_random)]
        for d in draws:
            assert len(d) == n and not set(d) & registered_closed and set(d) == closure(set(d))
        controls[g] = {"random": draws, "group_mean_separability": round(float(np.mean([sep[c] for c in groups[g]])), 4),
                       "random_mean_separability": [round(float(np.mean([sep[c] for c in d])), 4) for d in draws]}
    return {"groups": {g: {"columns": c, "size": len(c)} for g, c in groups.items()},
            "proxy_clusters_multi": [list(cl) for cl in sorted({cluster_of[c] for c in inputs}) if len(cl) > 1],
            "control_pool": {"columns": sorted({c for cl in pool_clusters for c in cl}), "n_clusters": len(pool_clusters)},
            "unavailable_after_train_only_preprocessing": sorted((by["flag"] | by["appendix"] | by["duplication"]
                                                                  | by["hypothesis"]) - avail),
            "controls": controls, "separability_train": {c: round(float(sep[c]), 4) for c in inputs}}
