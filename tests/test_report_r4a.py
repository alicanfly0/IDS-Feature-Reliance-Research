"""report_r4a on a synthetic 70-run aggregate (no Colab results needed)."""
import json

import numpy as np
import pytest

from src.evaluation import report_r4a as R
from src.experiments.matrix_3b import load_matrix


def _fake_aggregate(n=22049, shift=None):
    rng = np.random.default_rng(0)
    runs = {}
    for e in load_matrix(design="r4a")["entries"]:
        err = int(rng.integers(5, 15)) + (shift or {}).get((e["kind"], e["group"]), 0)
        fp = err // 2
        runs[e["id"]] = {"run": e["id"] + "-x", "n": n, "errors": err, "error_rate": err / n, "fp": fp,
                         "fn": err - fp, "mcc": 1 - err / n, "log_loss": err / n}
    return {"n_completed": 70, "n_matrix": 70, "runs": runs,
            "environment": {"git_commit": "c", "fingerprint": "f"}}


def test_r4a_ii_family_and_tables(tmp_path, monkeypatch):
    monkeypatch.setattr(R, "DIR", tmp_path)
    agg = _fake_aggregate(shift={("group", "U_documented_union"): 200})
    (tmp_path / "aggregate_r4a.json").write_text(json.dumps(agg))
    matrix, agg2 = R.load()
    ii = R.analyse_ii(matrix, agg2)
    assert sorted(ii["groups"]) == ["A_flag_defects", "B_appendix_closed", "U_documented_union"]
    assert len(ii["holm"]) == 3
    u = ii["groups"]["U_documented_union"]["endpoints"]["error_rate"]
    assert u["reading"]["mean_contrast"] > 0.005 and u["p_holm"] < 0.05
    cmp = R.compare_with_r1(ii)
    assert set(cmp["groups"]) == set(ii["groups"])
    md, tex = R.tables(ii, cmp)
    assert md.count("\n") == 5 and tex.count(r"\\") == 4


def test_incomplete_aggregate_refused(tmp_path, monkeypatch):
    monkeypatch.setattr(R, "DIR", tmp_path)
    agg = _fake_aggregate()
    agg["n_completed"] = 69
    (tmp_path / "aggregate_r4a.json").write_text(json.dumps(agg))
    with pytest.raises(RuntimeError):
        R.load()


def test_welch_matches_scipy():
    from scipy import stats
    a, b = np.array([1.0, 2, 3, 4]), np.array([2.0, 2.5, 5, 7, 1])
    w = R.welch(a, b)
    t = stats.ttest_ind(a, b, equal_var=False)
    ci = t.confidence_interval(0.95)
    assert w["interval"] == pytest.approx([ci.low, ci.high])
