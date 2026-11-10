"""Registry correction, array-only postprocessing, and preservation of original artifacts."""
import copy
import json

import numpy as np
import pytest

from src.audit.arr import importance_from_arrays
from src.audit.correct_arr import ATOL, OUTPUT, PILOT, calculate, compare_results, protected_integrity
from src.audit.registry import feature_sets, load_registry, validate
from src.config import ROOT


def test_v2_flag_family_and_multiple_mechanisms():
    reg = load_registry()
    cols = json.loads(next(PILOT.glob("variant-*/settings.json")).read_text())["columns"]
    tiers = feature_sets(reg, cols)
    flags = {"FIN Flag Count", "SYN Flag Count", "RST Flag Count", "PSH Flag Count", "ACK Flag Count",
             "URG Flag Count", "CWE Flag Count", "ECE Flag Count", "Fwd PSH Flags", "Bwd PSH Flags",
             "Fwd URG Flags", "Bwd URG Flags"}
    assert len(tiers["direct"]) == 16 and flags <= tiers["direct"]
    assert tiers["direct"] & tiers["shortcut"] == {"SYN Flag Count"}
    assert tiers["hypothesis"] == {"Destination Port", "Init_Win_bytes_backward"}
    assert len(tiers["all"]) == 24 and not tiers["missing"]
    syn = next(e for e in reg["features"] if e["id"] == "R07")
    assert syn["evidence_level"] == "shortcut_indicator" and len(syn["mechanisms"]) == 2


def test_original_registry_is_exact_git_snapshot():
    import subprocess
    original = subprocess.run(["git", "show", "2490821:configs/artifact_registry.yaml"],
                              cwd=ROOT, check=True, capture_output=True).stdout
    # Git stores LF; Windows working-tree snapshots may contain CRLF.
    local = (ROOT / "configs/history/artifact_registry_v1.yaml").read_bytes()
    assert original.replace(b"\r\n", b"\n") == local.replace(b"\r\n", b"\n")


def test_web_evidence_requires_section_url_and_published_support():
    reg = load_registry()
    assert not validate(reg)
    bad = copy.deepcopy(reg)
    entry = next(e for e in bad["features"] if e["name"] == "ACK Flag Count")
    entry["sources"][0]["url"] = "https://unrelated.example/"
    assert validate(bad)
    bad = copy.deepcopy(reg)
    syn = next(e for e in bad["features"] if e["id"] == "R07")
    syn["mechanisms"][1]["sources"] = [{"ref": "phase2", "section": "Step 4", "finding": "proposal"}]
    assert any("requires published evidence" in x for x in validate(bad))


def test_signed_aggregation_cancellation_and_validation():
    a = np.array([[3., -2., 1.], [-3., 2., 1.]])
    cols = ["copy", "copy.1", "x"]
    merges = {"copy.1": "copy"}
    assert importance_from_arrays(a, cols, merges, "sum_abs")["copy"] == 5
    assert importance_from_arrays(a, cols, merges, "signed")["copy"] == 1
    for bad in (np.array([[float("nan"), 0, 0]]), np.zeros((2, 2))):
        with pytest.raises(ValueError):
            importance_from_arrays(bad, cols)
    with pytest.raises(ValueError):
        importance_from_arrays(a, cols, aggregation="unknown")


@pytest.mark.skipif(not all(p.is_file() for p in PILOT.glob("variant-*/shap_values.npz")) or
                    len(list(PILOT.glob("variant-*/shap_values.npz"))) != 6, reason="six local arrays unavailable")
def test_corrected_results_reproduce_from_arrays_and_independent_formula():
    expected = json.loads((OUTPUT / "corrected_arr_v2.json").read_text())
    actual = json.loads(json.dumps(calculate()))
    assert compare_results(expected, actual) == []
    for v in actual["variants"].values():
        c = v["duplicate_comparison"]
        assert c["signed"] <= c["sum_abs"] and c["max_arr_difference"] <= ATOL
        assert all(c["top_k_identical"].values())


def _saved():
    return json.loads((OUTPUT / "corrected_arr_v2.json").read_text())


def _first_arr(result):
    variant = next(iter(result["variants"].values()))
    return variant["methods"]["sum_abs"]["arr"]["20"]


def test_comparator_accepts_cross_platform_float_noise():
    saved = _saved()
    noisy = copy.deepcopy(saved)
    for variant in noisy["variants"].values():          # perturb every importance and ARR value
        for method in variant["methods"].values():
            method["importance"] = {k: v * (1 + 2e-16) + 5.55e-17 for k, v in method["importance"].items()}
            for table in method["arr"].values():
                for tier in ("direct", "shortcut", "hypothesis", "all"):
                    table[tier] += 5.55e-17
    assert compare_results(saved, noisy) == []


@pytest.mark.parametrize("delta", [1e-6, 1e-9, -2e-8])
def test_comparator_rejects_genuinely_wrong_arr(delta):
    saved = _saved()
    wrong = copy.deepcopy(saved)
    _first_arr(wrong)["direct"] += delta
    problems = compare_results(saved, wrong)
    assert len(problems) == 1 and ".arr.20.direct" in problems[0]


def test_comparator_keeps_discrete_results_exact():
    saved = _saved()
    for mutate in (
        lambda r: _first_arr(r)["top_k"].reverse(),                                   # ranking order
        lambda r: r["membership"]["direct"].append("Destination Port"),               # membership
        lambda r: r.__setitem__("registry_sha256", "0" * 64),                         # digest
        lambda r: next(iter(r["variants"].values()))["settings"].__setitem__("n_explain", 199),
        lambda r: next(iter(r["variants"].values()))["methods"]["sum_abs"]["arr"].pop("20"),  # K value
        lambda r: next(iter(r["variants"].values()))["duplicate_comparison"]["top_k_identical"]
        .__setitem__("2", False),                                                     # bool, not 0/1
    ):
        changed = copy.deepcopy(saved)
        mutate(changed)
        assert compare_results(saved, changed), mutate


def test_comparator_nonfinite_and_type_handling():
    nan, inf = float("nan"), float("inf")
    assert compare_results({"x": nan}, {"x": nan}) == []
    assert compare_results({"x": nan}, {"x": 0.5})
    assert compare_results({"x": 0.5}, {"x": nan})
    assert compare_results({"x": inf}, {"x": inf}) == []
    assert compare_results({"x": inf}, {"x": -inf})
    assert compare_results({"x": 1.0}, {"x": 1e308})
    assert compare_results({"x": 0.5}, {"x": "0.5"})
    assert compare_results({"x": True}, {"x": 1})
    assert compare_results({"x": 3}, {"x": 3.0}) == []      # same number, int vs float JSON spelling
    assert compare_results({"x": 3}, {"x": 4})


def test_verify_cli_uses_tolerance_but_rejects_tampering(tmp_path, monkeypatch):
    """--verify passes on float noise in the saved file and fails on a real change."""
    import src.audit.correct_arr as ca
    if len(list(PILOT.glob("variant-*/shap_values.npz"))) != 6:
        pytest.skip("six local arrays unavailable")
    saved = _saved()
    out = tmp_path / "out"
    out.mkdir()
    (out / "original_artifact_sha256.json").write_bytes((OUTPUT / "original_artifact_sha256.json").read_bytes())
    monkeypatch.setattr(ca, "OUTPUT", out)
    noisy = copy.deepcopy(saved)
    _first_arr(noisy)["all"] += 5.55e-17
    (out / "corrected_arr_v2.json").write_text(json.dumps(noisy, indent=2))
    ca.main(["--verify"])
    _first_arr(noisy)["all"] += 1e-6
    (out / "corrected_arr_v2.json").write_text(json.dumps(noisy, indent=2))
    with pytest.raises(ValueError, match="do not reproduce"):
        ca.main(["--verify"])


@pytest.mark.skipif(not (ROOT / "results/runs/ae_xgb_d008_trackB-seed0-cpu-565a8b9e/DONE").exists(),
                    reason="local original runs unavailable")
def test_protected_artifacts_unchanged():
    assert protected_integrity() == 96


def test_precision_evidence_is_archived_measurement():
    import zipfile
    p = json.loads((ROOT / "docs/evidence/precision_comparison_2a.json").read_text())
    assert p["float64_vs_saved"]["predictions_identical"]
    assert p["float64_vs_float32"]["max_abs_margin_diff"] > 1.5
    assert p["float64_vs_saved"]["max_abs_prob_diff"] == pytest.approx(0.0008868888248654283)
    archive = ROOT / "MILESTONE_2A_REVIEW.zip"
    if archive.exists():
        with zipfile.ZipFile(archive) as z:
            member = next(n for n in z.namelist() if n.endswith("/float32_vs_float64.json"))
            assert z.read(member) == (ROOT / "docs/evidence/precision_comparison_2a.json").read_bytes()


def test_empty_mechanisms_cannot_silently_remove_evidence():
    reg = load_registry()
    reg["features"][0]["mechanisms"] = []
    assert any("retain the primary" in x for x in validate(reg))
