"""Milestone 3B-0 execution infrastructure: matrix, population, aggregation, Monday scorer, statistics.
No model is trained; real-data tests skip without the local CICIDS2017 archive."""
import gzip
import json
import shutil
import types

import numpy as np
import pandas as pd
import pytest
import yaml

from src.config import ROOT, load_config
from src.data.split import Split
from src.evaluation import aggregate_3b as agg
from src.evaluation import score_benign as sb
from src.evaluation import stats_3b as st
from src.experiments import matrix_3b as mx
from src.experiments.population import apply_population, lf_sha256, load_population, rows_sha256

DATA = (ROOT / "data/raw/cicids2017_original/MachineLearningCSV.zip").is_file()


# ------------------------------------------------------------------ statistics

def test_orientation_lower_is_better():
    assert st.removal_effect(ablated=0.003, full=0.001) > 0          # removal made it worse
    d = st.contrasts([0.002, 0.004], [0.001, 0.001])
    assert (d > 0).all()                                               # group hurt more than control
    with pytest.raises(ValueError):
        st.contrasts([0.1, 0.2], [0.1])


def test_sign_flip_exact_values_and_ties():
    r = st.sign_flip_test([1.0, 2.0, 3.0])
    assert r["p"] == pytest.approx(2 / 8) and r["min_attainable_p"] == pytest.approx(2 / 8)
    r = st.sign_flip_test(np.arange(1, 11, dtype=float))
    assert r["p"] == pytest.approx(2 / 1024) and r["n_nonzero"] == 10
    r = st.sign_flip_test([0, 0, 0, 1, 2, 3, 4, 5, 6, 7.0])           # three ties at zero
    assert r["n_nonzero"] == 7 and r["min_attainable_p"] == pytest.approx(2 / 128)
    assert st.sign_flip_test([0.0] * 10)["p"] == 1.0


def test_holm_step_down():
    out = st.holm({"a": 0.001, "b": 0.03, "c": 0.04}, alpha=0.05)
    assert out["a"]["reject"] and not out["b"]["reject"] and not out["c"]["reject"]   # 0.03 > 0.05/2; then stop
    assert out["a"]["p_holm"] == pytest.approx(0.003)
    assert out["b"]["p_holm"] == pytest.approx(0.06) and out["c"]["p_holm"] == pytest.approx(0.06)
    assert all(v["reject"] for v in st.holm({"a": 0.001, "b": 0.02, "c": 0.04}).values())


def test_readings_and_testability():
    big = np.linspace(0.01, 0.02, 10)
    r = st.reading(big, sesoi=0.001, holm_reject=True)
    assert r["reading"] == "practically relevant difference" and r["direction"].startswith("group removal hurts more")
    tiny = np.array([1e-5, -1e-5] * 5)
    assert st.reading(tiny, sesoi=0.001, holm_reject=False)["reading"] == "practical equivalence at the SESOI"
    ties = np.array([0] * 4 + [0.001] * 6)
    assert st.reading(ties, sesoi=0.001, holm_reject=False)["exact_test_can_reach_holm_threshold"] is False
    wide = np.array([0.05, -0.05] * 5)
    assert st.reading(wide, sesoi=0.001, holm_reject=False)["reading"] == "inconclusive"


def test_clopper_pearson_and_cluster_bootstrap():
    lo, hi = st.clopper_pearson(0, 10)
    assert lo == 0 and hi == pytest.approx(1 - 0.025 ** (1 / 10))
    a = np.r_[np.zeros(95), np.ones(5)]
    b = np.zeros(100)
    clusters = np.repeat(np.arange(50), 2)
    r1 = st.cluster_bootstrap_diff(a, b, clusters, n_boot=200, seed=1)
    r2 = st.cluster_bootstrap_diff(a, b, clusters, n_boot=200, seed=1)
    assert r1 == r2 and r1["estimate"] == pytest.approx(0.05) and r1["n_clusters"] == 50
    assert 1 <= r1["distinct_replicates"] <= 200


# ------------------------------------------------------------------ matrix and configs

def test_matrix_design_d():
    m = mx.build_matrix()
    kinds = pd.Series([e["kind"] for e in m["entries"]]).value_counts().to_dict()
    assert m["n_entries"] == 110 and kinds == {"full": 10, "group": 50, "control": 50}
    for e in m["entries"]:
        if e["kind"] == "control":
            assert e["control_draw"] == e["model_seed"]
    assert {e["model_seed"] for e in m["entries"]} == set(range(10))


def test_committed_configs_match_protocol():
    m = mx.load_matrix()                                   # refuses if protocol files changed
    from src.experiments import ae_xgb
    for e in m["entries"][::11]:
        cfg = ae_xgb.load_experiment(ROOT / e["config"])
        assert cfg["experiment"]["extra_drop_cols"] == e["drop"]
        assert cfg["run"]["model_seed"] == e["model_seed"] and not cfg["run"]["exclude_eval_twins"]
        assert cfg["run"]["eval_population"]["sha256"] == lf_sha256(ROOT / mx.POPULATION_FILE)
        base = ae_xgb.load_experiment(ROOT / mx.BASE_CONFIG)
        for sec in ("ae", "xgb", "augment", "data"):
            assert cfg[sec] == base[sec]                    # nothing but the view and seed changes


def _copy_root(tmp_path):
    for rel in (mx.GROUPS_FILE, mx.POPULATION_FILE, mx.BASE_CONFIG, mx.BASELINE_PREPROCESSOR):
        (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / rel, tmp_path / rel)
    return tmp_path


def test_matrix_refuses_unknown_columns_groups_and_changed_files(tmp_path, monkeypatch):
    root = _copy_root(tmp_path)
    g = yaml.safe_load((root / mx.GROUPS_FILE).read_text(encoding="utf-8"))
    g["controls"]["C_duplication"]["random"][3] = ["Not A Column"] * 4
    (root / mx.GROUPS_FILE).write_text(yaml.safe_dump(g), encoding="utf-8")
    with pytest.raises(RuntimeError, match="different groups file"):        # hash no longer matches the record
        mx.build_matrix(root)
    pop = json.loads((root / mx.POPULATION_FILE).read_text())
    pop["frozen_groups_sha256_lf"] = lf_sha256(root / mx.GROUPS_FILE)
    (root / mx.POPULATION_FILE).write_text(json.dumps(pop))
    with pytest.raises(ValueError, match="not in the 68 model inputs"):
        mx.build_matrix(root)
    monkeypatch.setitem(mx.PRIMARY, "E_unknown", "E")
    with pytest.raises(KeyError):
        mx.build_matrix(_copy_root(tmp_path / "fresh"))


def test_generate_is_idempotent_and_never_overwrites(tmp_path):
    root = _copy_root(tmp_path)
    path = mx.generate(root)
    assert path.read_text() == mx.generate(root).read_text()                  # identical rerun is fine
    cfg = root / mx.OUT_DIR / "r1_full_s0.yaml"
    cfg.write_text(cfg.read_text() + "# edited\n", encoding="utf-8")
    with pytest.raises(FileExistsError):
        mx.generate(root)


def test_run_requires_recorded_approval(capsys):
    assert mx.main(["run", "--batch", "0", "--storage", "unused"]) == 2
    assert "refusing to train" in capsys.readouterr().err


# ------------------------------------------------------------------ aggregation

def _fake_run(storage, entry, rows, y, prob):
    d = storage / "runs" / f"{entry['experiment_name']}-seed{entry['model_seed']}-cpu-deadbeef"
    d.mkdir(parents=True)
    (d / "DONE").write_text("{}")
    pred = pd.DataFrame({"source_row": rows, "y_true": y, "prob_ddos": prob, "y_pred": (prob >= 0.5).astype(int)})
    with gzip.open(d / "predictions_test.csv.gz", "wt") as f:
        pred.to_csv(f, index=False)


def test_aggregate_enforces_identical_rows(tmp_path):
    rows, y = np.array([3, 7, 9, 12]), np.array([0, 1, 1, 0])
    full = {"id": "r1_full_s0", "kind": "full", "experiment_name": "ae3b_r1_full", "model_seed": 0}
    grp = {"id": "r1_A_s0", "kind": "group", "experiment_name": "ae3b_r1_A", "model_seed": 0}
    matrix = {"n_entries": 2, "entries": [full, grp]}
    pop = {"family_common_model_visible": {"test_kept_source_rows_sha256": rows_sha256(rows)}}
    _fake_run(tmp_path, full, rows, y, np.array([0.1, 0.9, 0.8, 0.2]))
    _fake_run(tmp_path, grp, rows, y, np.array([0.6, 0.9, 0.3, 0.2]))      # one FP, one FN more
    out = agg.aggregate(tmp_path, matrix, pop, check_config=False)
    assert out["runs"]["r1_full_s0"]["errors"] == 0 and out["runs"]["r1_A_s0"]["errors"] == 2
    p = out["paired_vs_full"]["r1_A_s0"]
    assert p["only_ablated_wrong"] == 2 and p["effect_error_rate"] == pytest.approx(0.5)
    assert agg.aggregate(tmp_path, matrix, pop, check_config=False) == out              # deterministic
    shutil.rmtree(next((tmp_path / "runs").glob("ae3b_r1_A-*")))
    _fake_run(tmp_path, grp, rows[::-1], y[::-1], np.array([0.6, 0.9, 0.3, 0.2]))
    with pytest.raises(RuntimeError, match="differ"):
        agg.aggregate(tmp_path, matrix, pop, check_config=False)
    pop_bad = {"family_common_model_visible": {"test_kept_source_rows_sha256": rows_sha256(rows[:3])}}
    with pytest.raises(RuntimeError, match="family-common"):
        agg.aggregate(tmp_path, matrix, pop_bad, check_config=False)


# ------------------------------------------------------------------ Monday scorer

def test_training_twin_mask_uses_model_visible_view():
    cfg = load_config(ROOT / mx.BASE_CONFIG)
    train = pd.DataFrame({"a": [1.0, 2.0, 3.0], "b": [10.0, 20.0, 30.0], "Label": ["BENIGN"] * 3})
    prep = types.SimpleNamespace(frame=train, split=Split(np.arange(3), np.array([], int), np.array([], int), "t", 0))
    monday = pd.DataFrame({"a": [1.0, 2.0, 5.0], "b": [10.0, 99.0, 30.0], "Label": ["BENIGN"] * 3})
    mask, per_view = sb.training_twin_mask(cfg, prep, {"full": [], "no_b": ["b"]}, monday)
    assert per_view == {"full": 1, "no_b": 2} and mask.tolist() == [True, True, False]
    assert sb.fpr_summary(np.array([0, 1, 0, 0]))["fpr"] == 0.25


# ------------------------------------------------------------------ real data: population path

@pytest.mark.skipif(not DATA, reason="CICIDS2017 archive not available")
def test_population_applies_identically_and_refuses_tampering(tmp_path):
    from src.data import ddos
    record_path = ROOT / mx.POPULATION_FILE
    record = load_population(record_path, lf_sha256(record_path))
    cfg = load_config(ROOT / mx.BASE_CONFIG)
    prep = ddos.prepare(ddos.load(ddos.verified_csv(ROOT)[0]), cfg["data"]["label_map"])
    groups = yaml.safe_load((ROOT / mx.GROUPS_FILE).read_text(encoding="utf-8"))
    kept = set()
    for drop in ([], groups["groups"]["D_metadata_hypothesis"]["columns"], groups["controls"]["U_documented_union"]["random"][9]):
        view = [c for c in prep.feature_cols if c not in drop]
        split, rep = apply_population(prep, record, view)
        assert (rep["val_kept"], rep["test_kept"]) == (33134, 33038)
        kept.add(rows_sha256(prep.frame.index.to_numpy()[split.test]))
    assert len(kept) == 1                                            # identical test rows for every view
    with pytest.raises(RuntimeError, match="hash"):
        load_population(record_path, "0" * 64)
    bad = json.loads(json.dumps(record))
    bad["family_common_model_visible"]["test_excluded_source_rows"] = bad["family_common_model_visible"]["test_excluded_source_rows"][1:]
    with pytest.raises(RuntimeError):
        apply_population(prep, bad, [c for c in prep.feature_cols if c not in groups["groups"]["D_metadata_hypothesis"]["columns"]])
