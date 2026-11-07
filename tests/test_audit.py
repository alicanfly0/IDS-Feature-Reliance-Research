"""Milestone 2A: artifact registry, ARR@K, composite raw-feature model and SHAP (synthetic run, CPU)."""
import copy
import hashlib
import json

import numpy as np
import pandas as pd
import pytest

from src.audit import shap_explain as se
from src.audit.arr import arr_at_k, arr_table, merge_columns, top_k
from src.audit.composite import CompositeModel
from src.audit.registry import feature_sets, load_registry, validate
from src.config import ROOT
from src.data import ddos
from src.experiments import ae_xgb
from test_ae_xgb import _flows, _tiny_cfg

REG = load_registry()
BASELINE = ROOT / "results" / "baselines" / "ae_xgb_d008_trackB-seed0-cpu-565a8b9e"
PRE = json.loads((BASELINE / "preprocessor.json").read_text(encoding="utf-8"))
D008_COLUMNS = PRE["numeric_cols"] + PRE["dropped_constant_on_train"]


# ------------------------------------------------------------------ registry
def test_registry_evidence_levels_are_the_reviewed_ones():
    level = {e["id"]: e["evidence_level"] for e in REG["features"]}
    assert {i for i, v in level.items() if v == "direct_extraction_error"} == {"R09", "R10", "R11", "R12"}
    assert {i for i, v in level.items() if v == "shortcut_indicator"} == {"R02", "R04", "R05", "R06", "R07", "R08"}
    # Phase II candidates are not promoted without a paged source.
    assert {i for i, v in level.items() if v == "unverified_hypothesis"} == {"R01", "R03"}


def test_registry_sources_resolve_and_carry_pages():
    for entry in REG["features"] + REG["non_feature_issues"]:
        for src in entry["sources"]:
            assert src["ref"] in REG["sources"]
            assert src["section"] and src["finding"]
            if src["ref"] in ("engelen2021", "lanvin2023"):
                assert src["page"], entry["id"]


def test_registry_columns_exist_in_the_d008_schema():
    assert len(D008_COLUMNS) == 78
    sets = feature_sets(REG, D008_COLUMNS)
    assert sets["missing"] == []
    assert sets["direct"] == {"Flow IAT Min", "Flow IAT Mean", "Flow Packets/s", "Bwd Packets/s"}
    assert "Fwd Header Length.1" in sets["shortcut"] and "Destination Port" in sets["hypothesis"]
    assert sets["all"] == sets["direct"] | sets["shortcut"] | sets["hypothesis"]
    assert not (sets["direct"] & sets["shortcut"]) and not (sets["shortcut"] & sets["hypothesis"])


def test_feature_sets_report_missing_columns():
    sets = feature_sets(REG, [c for c in D008_COLUMNS if c != "Flow IAT Min"])
    assert sets["missing"] == ["Flow IAT Min"] and "Flow IAT Min" not in sets["direct"]


def test_validate_rejects_unsupported_claims():
    bad = copy.deepcopy(REG)
    r01 = next(e for e in bad["features"] if e["id"] == "R01")
    r01["evidence_level"] = "shortcut_indicator"
    r01["sources"] = [s for s in r01["sources"] if s["ref"] == "phase2"]      # Phase II alone
    bad["features"][1]["sources"][0].pop("page")
    bad["features"][2]["evidence_level"] = "confirmed"
    bad["features"][3]["columns"] = ["Destination Port"]                      # mapped twice
    problems = " | ".join(validate(bad))
    assert "R01: shortcut_indicator requires a paged source" in problems
    assert "needs a page" in problems and "evidence_level must be one of" in problems
    assert "more than one feature entry" in problems


# ------------------------------------------------------------------ ARR@K
def test_arr_at_k_synthetic_values():
    imp = {"a": 4.0, "b": 3.0, "c": 2.0, "d": 1.0, "e": 0.0}
    assert arr_at_k(imp, {"a"}, 2) == pytest.approx(4 / 7)
    assert arr_at_k(imp, {"c", "d"}, 2) == 0.0
    assert arr_at_k(imp, {"b", "d"}, 5) == pytest.approx(4 / 10)
    assert arr_at_k(imp, {"a", "b", "c", "d", "e"}, 20) == 1.0          # K larger than the feature count
    assert arr_at_k(imp, set(), 3) == 0.0


def test_arr_zero_denominator_ties_and_bad_input():
    assert np.isnan(arr_at_k({"a": 0.0, "b": 0.0}, {"a"}, 2))
    assert top_k({"b": 1.0, "a": 1.0, "c": 2.0}, 2) == ["c", "a"]        # ties broken by name
    with pytest.raises(ValueError):
        arr_at_k({"a": -1.0}, {"a"}, 1)
    with pytest.raises(ValueError):
        arr_at_k({"a": float("nan")}, {"a"}, 1)
    with pytest.raises(ValueError):
        arr_at_k({"a": 1.0}, {"a"}, 0)


def test_merge_duplicate_columns_and_table():
    imp = {"Fwd Header Length": 1.0, "Fwd Header Length.1": 0.5, "x": 1.2}
    merged = merge_columns(imp, se.MERGES)
    assert merged == {"Fwd Header Length": 1.5, "x": 1.2}
    table = arr_table(merged, {"shortcut": {"Fwd Header Length"}}, ks=(1, 2))
    assert table[1]["top_k"] == ["Fwd Header Length"] and table[1]["shortcut"] == 1.0
    assert table[2]["shortcut"] == pytest.approx(1.5 / 2.7) and table[2]["shortcut_in_top_k"] == ["Fwd Header Length"]


# ------------------------------------------------------------------ sampling
def test_stratified_sample_is_deterministic_and_proportional():
    pos = np.arange(1000, 2000)
    y = (np.arange(1000) % 4 == 0).astype(int)                            # 25 % positive
    a, b = se.stratified_sample(pos, y, 100, 3), se.stratified_sample(pos, y, 100, 3)
    assert np.array_equal(a, b) and len(a) == 100 and len(set(a)) == 100
    assert set(a) <= set(pos) and y[a - 1000].sum() == 25
    assert not np.array_equal(a, se.stratified_sample(pos, y, 100, 4))


# ------------------------------------------------------------------ composite model + SHAP on a synthetic run
@pytest.fixture(scope="module")
def synthetic_run(tmp_path_factory):
    storage = tmp_path_factory.mktemp("audit")
    cfg = _tiny_cfg()
    loader = lambda: (_flows(), {"archive": "synthetic", "csv_sha256": "synthetic"})   # noqa: E731
    run_dir = ae_xgb.run(cfg, "cpu", storage, loader=loader)
    d, s = cfg["data"], cfg["experiment"]["split"]
    prep = ddos.prepare(_flows(), d["label_map"], tuple(s["fractions"]), s["seed"], tuple(d["nonnegative_cols"]))
    return run_dir, prep


def _hashes(folder):
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(folder.rglob("*")) if p.is_file()}


def test_composite_reproduces_saved_outputs_without_retraining(synthetic_run):
    run_dir, prep = synthetic_run
    before = _hashes(run_dir)
    cm = CompositeModel(run_dir, prep.feature_cols)
    test = prep.split.parts()["test"]
    raw = prep.frame[prep.feature_cols].to_numpy(dtype=np.float64)
    saved = pd.read_csv(run_dir / "predictions_test.csv.gz").set_index("source_row").loc[prep.frame.index[test]]
    assert np.abs(cm.proba(raw[test]) - saved.prob_ddos.to_numpy()).max() < 1e-6
    lat = np.load(run_dir / "latent.npz")["test"]
    assert np.abs(cm.latent(raw[test]) - lat).max() < 1e-5
    cm64 = CompositeModel(run_dir, prep.feature_cols, precision="float64")
    assert ((cm64.proba(raw[test]) >= 0.5).astype(int) == saved.y_pred.to_numpy()).all()
    assert _hashes(run_dir) == before                                     # loading changes nothing


def test_composite_rejects_wrong_columns_and_incomplete_runs(synthetic_run, tmp_path):
    run_dir, prep = synthetic_run
    with pytest.raises(ValueError):
        CompositeModel(run_dir, prep.feature_cols[:-1])
    with pytest.raises(RuntimeError):
        CompositeModel(tmp_path, prep.feature_cols)
    with pytest.raises(ValueError):
        CompositeModel(run_dir, prep.feature_cols, precision="float16")


def test_composite_uses_column_names_not_positions(synthetic_run):
    run_dir, prep = synthetic_run
    cols = list(prep.feature_cols)
    shuffled = cols[::-1]
    raw = prep.frame[cols].to_numpy(dtype=np.float64)[:50]
    raw_s = prep.frame[shuffled].to_numpy(dtype=np.float64)[:50]
    a = CompositeModel(run_dir, cols, precision="float64").margin(raw)
    b = CompositeModel(run_dir, shuffled, precision="float64").margin(raw_s)
    assert np.array_equal(a, b)


def test_float64_composite_is_batch_invariant(synthetic_run):
    run_dir, prep = synthetic_run
    cm = CompositeModel(run_dir, prep.feature_cols, precision="float64")
    raw = prep.frame[prep.feature_cols].to_numpy(dtype=np.float64)[:64]
    whole = cm.margin(raw)
    single = np.array([cm.margin(raw[i:i + 1])[0] for i in range(len(raw))])
    assert np.array_equal(whole, single)


def test_shap_dimensions_additivity_and_unused_columns(synthetic_run):
    run_dir, prep = synthetic_run
    cm = CompositeModel(run_dir, prep.feature_cols, precision="float64")
    parts, y = prep.split.parts(), prep.y
    raw = prep.frame[prep.feature_cols].to_numpy(dtype=np.float64)
    bg = raw[se.stratified_sample(parts["train"], y[parts["train"]], 20, 0)]
    x = raw[se.stratified_sample(parts["test"], y[parts["test"]], 6, 0)]
    res = se.explain_rows(cm, bg, x, 3 * (2 * len(prep.feature_cols) + 1), 0)
    assert res["values"].shape == (6, len(prep.feature_cols))
    assert res["checks"]["finite"]
    assert res["checks"]["additivity_max_abs_error"] < 1e-6
    assert res["checks"]["base_value_equals_mean_background_margin"] < 1e-9
    unused = prep.feature_cols.index("Fwd URG Flags")                    # constant on train -> dropped by the model
    assert np.all(res["values"][:, unused] == 0)
    again = se.explain_rows(cm, bg, x, 3 * (2 * len(prep.feature_cols) + 1), 0)
    assert np.array_equal(res["values"], again["values"])                 # seeded


def test_variant_is_cached_and_reports_arr(synthetic_run, tmp_path, monkeypatch):
    run_dir, prep = synthetic_run
    cm = CompositeModel(run_dir, prep.feature_cols, precision="float64")
    first = se.run_variant(cm, prep, REG, tmp_path, 0, 0, 20, 8, 2, log=lambda *_: None)
    assert first["checks"]["additivity_max_abs_error"] < 1e-6
    assert list(first["importance_column_level"])[0] in prep.feature_cols
    assert set(first["arr_merged"]) == {"2", "5", "10", "20"}
    assert set(first["arr_merged"]["5"]) >= {"direct", "shortcut", "all", "top_k"}
    settings = json.loads(next(tmp_path.glob("variant-*/settings.json")).read_text())
    assert settings["background_partition"] == "train" and settings["explain_partition"] == "test"
    assert set(settings["background_source_rows"]) <= set(prep.frame.index[prep.split.parts()["train"]])
    assert set(settings["explained_source_rows"]) <= set(prep.frame.index[prep.split.parts()["test"]])
    assert settings["model"]["precision"] == "float64" and settings["columns"] == prep.feature_cols

    def boom(*a, **k):
        raise AssertionError("cached variant was recomputed")
    monkeypatch.setattr(se, "explain_rows", boom)
    assert se.run_variant(cm, prep, REG, tmp_path, 0, 0, 20, 8, 2, log=lambda *_: None) == first
    with pytest.raises(AssertionError, match="recomputed"):              # other settings -> new variant
        se.run_variant(cm, prep, REG, tmp_path, 1, 0, 20, 8, 2, log=lambda *_: None)


# ------------------------------------------------------------------ the real baseline (only where the local run exists)
REAL_RUN = ROOT / "results" / "runs" / "ae_xgb_d008_trackB-seed0-cpu-565a8b9e"


@pytest.mark.skipif(not (REAL_RUN / "DONE").is_file(), reason="local baseline run not present")
def test_real_composite_loads_with_the_d008_schema():
    cm = CompositeModel(REAL_RUN, D008_COLUMNS, precision="float64")
    assert len(cm.model_columns) == 68 and cm.provenance["run"] == REAL_RUN.name
