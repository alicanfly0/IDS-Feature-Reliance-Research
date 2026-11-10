"""Milestone 3A pre-registration: the frozen groups stay consistent with the registry (no data needed)."""
import json

import yaml

from src.audit.registry import load_registry
from src.config import ROOT

FROZEN = ROOT / "configs/protocol/ablation_groups_3a.yaml"
PRIMARY = ["A_flag_defects", "B_appendix_closed", "C_duplication", "D_metadata_hypothesis", "U_documented_union"]
CONSTANT_ON_TRAIN = {"Bwd PSH Flags", "Fwd URG Flags", "Bwd URG Flags", "CWE Flag Count", "Fwd Avg Bytes/Bulk",
                     "Fwd Avg Packets/Bulk", "Fwd Avg Bulk Rate", "Bwd Avg Bytes/Bulk", "Bwd Avg Packets/Bulk",
                     "Bwd Avg Bulk Rate"}


def _frozen():
    return yaml.safe_load(FROZEN.read_text(encoding="utf-8"))


def _closure(cols, clusters):
    out = set(cols)
    for cl in clusters:
        if out & set(cl):
            out |= set(cl)
    return out


def _registered(reg):
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


def test_groups_match_registry_v2_and_train_only_availability():
    g, by = _frozen(), _registered(load_registry())
    clusters = g["proxy_clusters_multi"]
    groups = {k: set(v["columns"]) for k, v in g["groups"].items()}
    assert groups["A_flag_defects"] == by["flag"] - CONSTANT_ON_TRAIN
    assert groups["B_appendix_literal"] == by["appendix"]
    assert groups["B_appendix_closed"] == _closure(by["appendix"], clusters)
    assert groups["C_duplication"] == by["duplication"]
    assert groups["D_metadata_hypothesis"] == by["hypothesis"]
    assert groups["U_documented_union"] == groups["A_flag_defects"] | groups["B_appendix_closed"] | groups["C_duplication"]
    assert set(g["unavailable_after_train_only_preprocessing"]) == by["flag"] & CONSTANT_ON_TRAIN
    assert set(g["overlaps"]["A_flag_defects & B_appendix_closed"]) == groups["A_flag_defects"] & groups["B_appendix_closed"]
    assert all(v["size"] == len(v["columns"]) for v in g["groups"].values())


def test_controls_are_size_matched_disjoint_and_proxy_closed():
    g = _frozen()
    clusters = g["proxy_clusters_multi"]
    registered = set().union(*(set(v["columns"]) for v in g["groups"].values()))
    pool = set(g["control_pool"]["columns"])
    assert not pool & _closure(registered, clusters)
    for name in PRIMARY:
        size = g["groups"][name]["size"]
        controls = g["controls"][name]["random"] + [g["controls"][name]["difficulty_matched"]]
        assert len(g["controls"][name]["random"]) == 5
        for ctl in controls:
            assert len(ctl) == len(set(ctl)) == size
            assert set(ctl) <= pool
            assert _closure(ctl, clusters) == set(ctl)          # never half of a proxy pair


def test_inputs_and_split_are_the_baseline_ones():
    g = _frozen()
    pre = json.loads((ROOT / "results/baselines/ae_xgb_d008_trackB-seed0-cpu-565a8b9e/preprocessor.json").read_text())
    assert g["generated_from"]["inputs"] == pre["input_dim"] == 68
    assert g["generated_from"]["partition"] == "train only"
    assert g["generated_from"]["split_fingerprint"].startswith("50bd994880abbe15")
    inputs = set(pre["numeric_cols"])
    for v in g["groups"].values():
        assert set(v["columns"]) <= inputs
    assert set(g["control_pool"]["columns"]) <= inputs


R1 = ROOT / "configs/protocol/ablation_groups_3a_r1.yaml"
POP = ROOT / "results/protocol/milestone3a"


def test_r1_revision_only_extends_random_draws():
    """Review resolution: r1 keeps r0 groups, clusters, matched controls and draws 0-4 unchanged."""
    r0, r1 = _frozen(), yaml.safe_load(R1.read_text(encoding="utf-8"))
    assert r1["groups"] == r0["groups"] and r1["proxy_clusters_multi"] == r0["proxy_clusters_multi"]
    assert r1["control_pool"] == r0["control_pool"] and r1["separability_train"] == r0["separability_train"]
    pool, clusters = set(r1["control_pool"]["columns"]), r1["proxy_clusters_multi"]
    for name in PRIMARY:
        a, b = r0["controls"][name], r1["controls"][name]
        assert b["random"][:5] == a["random"] and b["difficulty_matched"] == a["difficulty_matched"]
        assert len(b["random"]) == 10 and len({tuple(r) for r in b["random"]}) == 10
        for ctl in b["random"]:
            assert len(ctl) == r1["groups"][name]["size"] and set(ctl) <= pool
            assert _closure(ctl, clusters) == set(ctl)


def test_population_records_model_visible_equals_raw():
    """Twin exclusions on float32 model-visible inputs equal the raw-view exclusions in every view."""
    for tag, views in (("r0", 38), ("r1", 63)):
        path = POP / f"eval_population_3a_{tag}.json"
        if not path.exists():
            continue
        rec = json.loads(path.read_text())
        assert rec["n_views"] == views and rec["split_fingerprint"].startswith("50bd994880abbe15")
        assert all(v["extra_val"] == 0 and v["extra_test"] == 0 for v in rec["views"].values())
        raw, mod = rec["family_common_raw_views"], rec["family_common_model_visible"]
        for k in ("val_excluded", "test_excluded", "val_kept", "test_kept"):
            assert raw[k] == mod[k]
        assert len(mod["test_excluded_source_rows"]) == mod["test_excluded"]
        assert mod["val_excluded_ddos"] == mod["test_excluded_ddos"] == 0
    r0 = json.loads((POP / "eval_population_3a_r0.json").read_text())["family_common_model_visible"]
    assert (r0["val_kept"], r0["test_kept"], r0["val_excluded"], r0["test_excluded"]) == (33134, 33038, 700, 839)
