"""Independent check of corrected ARR values using only NumPy/YAML and saved arrays.

Run from the project root: .\run.cmd scripts/verify_m2b_arr.py
Does not import any src.audit implementation or write output.
"""
import json
from pathlib import Path

import numpy as np
import yaml

root = Path(__file__).resolve().parents[1]
registry = yaml.safe_load((root / "configs/artifact_registry.yaml").read_text(encoding="utf-8"))
results = json.loads((root / "results/corrections/milestone2b/corrected_arr_v2.json").read_text())
members = {"direct": set(), "shortcut": set(), "hypothesis": set()}
level_key = {"direct_extraction_error": "direct", "shortcut_indicator": "shortcut",
             "unverified_hypothesis": "hypothesis"}
rename = lambda c: "Fwd Header Length" if c == "Fwd Header Length.1" else c
for feature in registry["features"]:
    for mechanism in feature.get("mechanisms", [feature]):
        members[level_key[mechanism["evidence_level"]]].update(map(rename, feature["columns"]))
members["hypothesis"] -= members["direct"] | members["shortcut"]
members["all"] = set.union(*members.values())
checked = 0
max_difference = 0.
for name, variant in results["variants"].items():
    folder = root / "results/shap/ae_xgb_d008_trackB-seed0-cpu-565a8b9e" / name
    columns = json.loads((folder / "settings.json").read_text())["columns"]
    with np.load(folder / "shap_values.npz", allow_pickle=False) as archive:
        values = archive["values"].astype(np.float64)
    grouped = list(dict.fromkeys(map(rename, columns)))
    for method in ("sum_abs", "signed"):
        scores = []
        for group in grouped:
            sub = values[:, [i for i, col in enumerate(columns) if rename(col) == group]]
            scores.append(float(np.abs(sub).sum(axis=1).mean()) if method == "sum_abs"
                          else float(np.abs(sub.sum(axis=1)).mean()))
        scores = np.array(scores)
        order = sorted(range(len(grouped)), key=lambda i: (-scores[i], grouped[i]))
        for k in (2, 5, 10, 20):
            ix = order[:k]
            expected_top = variant["methods"][method]["arr"][str(k)]["top_k"]
            assert [grouped[i] for i in ix] == expected_top, (name, method, k)
            for tier, group_members in members.items():
                selection = np.array([grouped[i] in group_members for i in ix])
                computed = float(scores[ix][selection].sum() / scores[ix].sum())
                saved = variant["methods"][method]["arr"][str(k)][tier]
                difference = abs(computed - saved)
                assert difference < 1e-12, (name, method, k, tier)
                max_difference = max(max_difference, difference)
                checked += 1
print(f"Independent NumPy check: {checked} ARR values agree; max absolute discrepancy {max_difference:.3g}.")
