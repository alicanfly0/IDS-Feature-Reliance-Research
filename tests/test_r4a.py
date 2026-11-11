"""R4a-ii (D-024): corrected-data loader, frozen groups, population record and matrix."""
import json

import numpy as np
import pandas as pd
import pytest
import yaml

from src.config import ROOT
from src.data import engelen
from src.experiments import matrix_3b as mx

GROUPS = ROOT / "configs/protocol/r4a_groups_v1.yaml"
POP = ROOT / "results/protocol/r4a/eval_population_r4a_v1.json"
ORIG = ROOT / "data/raw/cicids2017_original/MachineLearningCSV.zip"


def _raw(ddos_first="07/07/2017 08:56:31 PM", ddos_last="07/07/2017 09:16:10 PM"):
    ts = ["07/07/2017 08:31:00 PM", ddos_first, ddos_last, "07/07/2017 10:10:00 PM", "07/07/2017 08:40:00 PM"]
    labels = ["BENIGN", "DDoS", "DDoS", "BENIGN", "PortScan"]
    cmap = yaml.safe_load((ROOT / engelen.MAP_FILE).read_text(encoding="utf-8"))["mapping"]
    cols = {e: np.arange(5, dtype=float) for e in set(cmap.values())}
    return pd.DataFrame({**cols, "Timestamp": ts, "Label": labels}), cmap


def test_window_alignment_is_validated_and_columns_mapped():
    raw, cmap = _raw()
    out, info = engelen.window_frame(raw, cmap)
    assert info["alignment_validated"] and list(out["Label"]) == ["BENIGN", "DDoS", "DDoS"]   # 22:10 outside, PortScan out
    assert len(out.columns) == 79 and (out["Fwd Header Length.1"] == out["Fwd Header Length"]).all()
    assert (out["Destination Port"] == raw.loc[out.index, "Dst Port"]).all()
    bad, _ = _raw(ddos_first="07/07/2017 08:57:31 PM")                 # attack onset not at 15:56 + 5:00
    with pytest.raises(RuntimeError, match="alignment check failed"):
        engelen.window_frame(bad, cmap)


def test_frozen_r4a_groups_are_closed_disjoint_and_size_matched():
    g = yaml.safe_load(GROUPS.read_text(encoding="utf-8"))
    assert list(g["groups"]) == ["A_flag_defects", "B_appendix_closed", "U_documented_union"]
    clusters = g["proxy_clusters_multi"]
    inputs = set(g["model_inputs"])

    def closure(cols):
        out = set(cols)
        for cl in clusters:
            if out & set(cl):
                out |= set(cl)
        return out
    registered = set().union(*(set(v["columns"]) for v in g["groups"].values()))
    for name, spec in g["groups"].items():
        assert set(spec["columns"]) <= inputs and closure(spec["columns"]) == set(spec["columns"])
        draws = g["controls"][name]["random"]
        assert len(draws) == 10 and len({tuple(d) for d in draws}) == 10
        for d in draws:
            assert len(d) == spec["size"] and set(d) <= inputs and not set(d) & closure(registered)
            assert closure(d) == set(d)
    u = set(g["groups"]["U_documented_union"]["columns"])
    assert set(g["groups"]["A_flag_defects"]["columns"]) | set(g["groups"]["B_appendix_closed"]["columns"]) <= u


def test_population_record_covers_every_r4a_view_on_model_visible_inputs():
    rec = json.loads(POP.read_text())
    g = yaml.safe_load(GROUPS.read_text(encoding="utf-8"))
    assert rec["n_views"] == 34 and rec["split_fingerprint"].startswith("acd52bd8295ffe29")
    expected = {"full"} | set(g["groups"]) | {f"{n}/random{j}" for n in g["groups"] for j in range(10)}
    assert set(rec["views"]) == expected
    pop = rec["family_common_model_visible"]
    assert (pop["val_kept"], pop["test_kept"]) == (22008, 22049)
    assert pop["val_excluded_ddos"] == pop["test_excluded_ddos"] == 0
    excluded_t = set(pop["test_excluded_source_rows"])
    assert max(v["model_test"] for v in rec["views"].values()) <= len(excluded_t)
    assert rec["views"]["full"]["extra_test"] == 29     # float32-only twins exist on the corrected data (measured)


def test_r4a_matrix_design_and_r1_unchanged():
    m = mx.load_matrix(design="r4a")
    kinds = pd.Series([e["kind"] for e in m["entries"]]).value_counts().to_dict()
    assert m["n_entries"] == 70 and kinds == {"full": 10, "group": 30, "control": 30}
    assert all(e["control_draw"] == e["model_seed"] for e in m["entries"] if e["kind"] == "control")
    assert m["population_file"].endswith("eval_population_r4a_v1.json") and m["design"] == "r4a"
    assert mx.load_matrix()["n_entries"] == 110 and "design" not in mx.load_matrix()      # r1 untouched


@pytest.mark.skipif(not ORIG.is_file(), reason="CICIDS2017 archive not available")
def test_group_module_reproduces_frozen_r1_on_original_data():
    from src.audit import groups as G
    from src.audit.registry import load_registry
    from src.config import load_config
    from src.data import ddos
    cfg = load_config(ROOT / "configs/experiments/ae_xgb_d008_trackB.yaml")
    prep = ddos.prepare(ddos.load(ddos.verified_csv()[0]), cfg["data"]["label_map"])
    inputs = json.loads((ROOT / mx.BASELINE_PREPROCESSOR).read_text())["numeric_cols"]
    tr = prep.split.train
    out = G.build(prep.frame.iloc[tr], prep.y[tr], inputs, load_registry(), list(mx.PRIMARY), 10, 3000)
    r1 = yaml.safe_load((ROOT / mx.GROUPS_FILE).read_text(encoding="utf-8"))
    assert out["proxy_clusters_multi"] == r1["proxy_clusters_multi"]
    assert all(out["controls"][g]["random"] == r1["controls"][g]["random"] for g in out["controls"])
