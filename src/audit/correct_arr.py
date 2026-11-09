"""Milestone 2B: versioned postprocessing of six SAVED arrays; no model or SHAP imports.

python -m src.audit.correct_arr
Refuses to overwrite existing corrected outputs. --verify checks saved results and protected hashes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

from src.audit.arr import arr_table, importance_from_arrays, top_k
from src.audit.registry import feature_sets, load_registry
from src.config import ROOT

PILOT = ROOT / "results/shap/ae_xgb_d008_trackB-seed0-cpu-565a8b9e"
OUTPUT = ROOT / "results/corrections/milestone2b"
MERGES = {"Fwd Header Length.1": "Fwd Header Length"}
TIERS = ("direct", "shortcut", "hypothesis", "all")
KS = (2, 5, 10, 20)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def protected_integrity():
    expected = json.loads((OUTPUT / "original_artifact_sha256.json").read_text())
    changed = [p for p, h in expected.items() if not (ROOT / p).is_file() or digest(ROOT / p) != h]
    if changed:
        raise ValueError(f"original artifacts changed: {changed}")
    return len(expected)


def independent_arr(values, columns, tiers, aggregation, k):
    """Separate row/column calculation (does not call arr.py)."""
    matrix = np.asarray(values, dtype=np.float64)
    scores = {}
    for col in columns:
        name = MERGES.get(col, col)
        if name in scores:
            continue
        indices = [i for i, c in enumerate(columns) if MERGES.get(c, c) == name]
        scores[name] = (sum(float(np.mean(np.abs(matrix[:, i]))) for i in indices)
                        if aggregation == "sum_abs" else
                        float(np.mean(np.abs(np.sum(matrix[:, indices], axis=1)))))
    ordered = sorted(scores, key=lambda c: (-scores[c], c))[:k]
    denominator = sum(scores[c] for c in ordered)
    return {tier: sum(scores[c] for c in ordered if c in members) / denominator
            if denominator else float("nan") for tier, members in tiers.items()}


def calculate():
    reg = load_registry()
    old_path = ROOT / "configs/history/artifact_registry_v1.yaml"
    old = load_registry(old_path)
    variants = sorted(PILOT.glob("variant-*"))
    if len(variants) != 6:
        raise ValueError("exactly six existing variants required")
    results = {}
    for folder in variants:
        settings = json.loads((folder / "settings.json").read_text())
        summary = json.loads((folder / "summary.json").read_text())
        cols = settings["columns"]
        settings_key = hashlib.sha256(json.dumps(settings, sort_keys=True, default=str).encode()).hexdigest()[:12]
        if not folder.name.endswith(settings_key):
            raise ValueError("settings do not match original variant identity")
        with np.load(folder / "shap_values.npz", allow_pickle=False) as data:
            values = data["values"].astype(np.float64)
            if values.shape != (settings["n_explain"], len(cols)) or not np.isfinite(values).all():
                raise ValueError("array dimensions/finiteness inconsistent")
            if data["source_rows"].tolist() != settings["explained_source_rows"]:
                raise ValueError("source row alignment inconsistent")
            if any(data[k].shape != (len(values),) or not np.isfinite(data[k]).all() for k in ("base", "fx")):
                raise ValueError("base/output dimensions or finiteness inconsistent")
            error = float(np.max(np.abs(values.sum(axis=1) + data["base"] - data["fx"])))
        if error > 1e-4:
            raise ValueError("stored additivity tolerance exceeded")
        sets = feature_sets(reg, cols)
        if sets["missing"]:
            raise ValueError("registered feature missing from raw schema")
        tiers = {t: {MERGES.get(c, c) for c in sets[t]} for t in TIERS}
        old_sets = feature_sets(old, cols)
        old_tiers = {t: {MERGES.get(c, c) for c in old_sets[t]} for t in TIERS}
        methods = {}
        for method in ("sum_abs", "signed"):
            importance = importance_from_arrays(values, cols, MERGES, method)
            table = arr_table(importance, tiers)
            old_table = arr_table(importance, old_tiers)
            for k in KS:
                reference = independent_arr(values, cols, tiers, method, k)
                if any(abs(reference[t] - table[k][t]) > 1e-12 for t in TIERS):
                    raise ValueError("independent ARR computation disagrees")
            methods[method] = {
                "importance": importance, "ranking": top_k(importance, len(importance)),
                "arr": table, "registry_v1_arr_same_aggregation": old_table,
                "delta_from_registry_v1": {k: {t: table[k][t] - old_table[k][t] for t in TIERS} for k in KS},
                "added_membership_in_top_k": {k: {t: [c for c in table[k]["top_k"]
                    if c in tiers[t] - old_tiers[t]] for t in TIERS} for k in KS}}
        a, b = methods["sum_abs"], methods["signed"]
        old_diff = max(abs(a["importance"][c] - summary["importance_merged"][c]) for c in a["importance"])
        if old_diff > 1e-5:
            raise ValueError("saved arrays disagree with historical importances")
        results[folder.name] = {
            "settings": settings, "array_sha256": digest(folder / "shap_values.npz"),
            "settings_sha256": digest(folder / "settings.json"),
            "stored_array_additivity_error": error, "historical_importance_max_discrepancy": old_diff,
            "methods": methods,
            "duplicate_comparison": {
                "sum_abs": a["importance"]["Fwd Header Length"], "signed": b["importance"]["Fwd Header Length"],
                "rank_sum_abs": a["ranking"].index("Fwd Header Length") + 1,
                "rank_signed": b["ranking"].index("Fwd Header Length") + 1,
                "top_k_identical": {k: a["arr"][k]["top_k"] == b["arr"][k]["top_k"] for k in KS},
                "max_arr_difference": max(abs(a["arr"][k][t] - b["arr"][k][t]) for k in KS for t in TIERS)}}
    return {"registry_version": reg["registry_version"], "registry_sha256": digest(ROOT / "configs/artifact_registry.yaml"),
            "previous_registry_sha256": digest(old_path),
            "primary_aggregation": "sum_abs (historical continuity); signed reported as sensitivity",
            "membership": {t: sorted(v) for t, v in tiers.items()},
            "overlap_direct_shortcut": sorted(tiers["direct"] & tiers["shortcut"]),
            "variants": results}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args(argv)
    count = protected_integrity()
    result = calculate()
    target = OUTPUT / "corrected_arr_v2.json"
    serial = json.dumps(result, indent=2, allow_nan=False) + "\n"
    if args.verify:
        if json.loads(target.read_text()) != json.loads(serial):
            raise ValueError("corrected results do not reproduce")
    else:
        with target.open("x", encoding="utf-8") as stream:
            stream.write(serial)
    print(f"Six arrays independently checked; {count} original artifacts unchanged; corrected ARR v2 verified.")


if __name__ == "__main__":
    main()
