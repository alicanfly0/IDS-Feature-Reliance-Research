"""Milestone 3B-1: frozen Colab environment, cross-run compatibility and resume refusal (synthetic)."""
import copy
import json

import pytest

from src import colab_env, env
from src.config import ROOT
from src.evaluation import aggregate_3b as agg

SESSION1 = ROOT / "results/colab results/session1/preflight/environment.json"


def _session1_snapshot():
    """The real Colab session-1 snapshot, plus numba as printed in the same session (not in its JSON)."""
    if SESSION1.is_file():
        snap = json.loads(SESSION1.read_text(encoding="utf-8"))
    else:   # same values, for checkouts without the uncommitted session folder
        snap = {"python": "3.13.16", "in_colab": True, "device": "cuda",
                "gpu": {"torch_cuda_available": True, "devices": [{"name": "Tesla T4", "memory_bytes": 15637086208}],
                        "torch_cuda_version": "13.0", "nvidia_smi": ["Tesla T4, 15360 MiB, 580.82.07"]},
                "packages": {"numpy": "2.4.6", "pandas": "2.2.3", "scikit-learn": "1.6.1", "PyYAML": "6.0.3",
                             "pytest": "8.4.2", "torch": "2.14.1+cu130", "xgboost": "3.4.1", "lightgbm": "4.6.0",
                             "shap": "0.54.1"},
                "git": {"commit": "ac0715a73ad9af7e591aac100c116b594dd21158", "dirty": False, "source": "bundle"},
                "dataset": {"id": "cicids2017_original", "sha256": {"MachineLearningCSV.zip": "c3f2"}}}
    snap["packages"]["numba"] = "0.64.0"
    return snap


# ------------------------------------------------------------------ environment spec and checker

def test_spec_is_frozen_from_session1_and_never_pins_torch():
    spec = colab_env.load_spec()
    snap = _session1_snapshot()
    assert spec["python_major_minor"] == ".".join(snap["python"].split(".")[:2])
    assert spec["torch"]["version"] == snap["packages"]["torch"] and spec["gpu_name"] == "Tesla T4"
    for name, version in spec["pinned_packages"].items():
        assert snap["packages"][name] == str(version), name               # every pin was actually observed
    assert "scipy" not in spec["pinned_packages"] and "scipy" in spec["not_observed_in_session1"]
    bad = copy.deepcopy(spec)
    bad["pinned_packages"]["torch"] = "2.0"
    path = ROOT / "results" / "_tmp_bad_spec.yaml"
    try:
        import yaml
        path.write_text(yaml.safe_dump(bad))
        with pytest.raises(ValueError, match="never be a pip-pinned"):
            colab_env.load_spec(path)
    finally:
        path.unlink(missing_ok=True)


def test_compare_separates_fatal_from_pinnable():
    spec = colab_env.load_spec()
    ok = colab_env.compare(_session1_snapshot(), spec)
    assert ok["compatible"] and not ok["fatal"] and not ok["pinnable"]
    for mutate, kind in (
        (lambda s: s.__setitem__("python", "3.12.11"), "fatal"),
        (lambda s: s["packages"].__setitem__("torch", "2.15.0+cu130"), "fatal"),
        (lambda s: s["gpu"].__setitem__("torch_cuda_version", "12.4"), "fatal"),
        (lambda s: s["gpu"]["devices"][0].__setitem__("name", "NVIDIA L4"), "fatal"),
        (lambda s: s.__setitem__("device", "cpu"), "fatal"),
        (lambda s: s.__setitem__("in_colab", False), "fatal"),
        (lambda s: s["packages"].__setitem__("numpy", "2.4.7"), "pinnable"),
        (lambda s: s["packages"].pop("numba"), "pinnable"),
    ):
        snap = _session1_snapshot()
        mutate(snap)
        r = colab_env.compare(snap, spec)
        assert not r["compatible"] and bool(r["fatal"]) == (kind == "fatal") and bool(r["pinnable"]) == (kind == "pinnable")


def test_installer_pins_then_requires_restart_and_never_touches_torch(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(colab_env.subprocess, "run", lambda cmd, **k: calls.append(cmd) or type("R", (), {"returncode": 0})())
    snap = _session1_snapshot()
    snap["packages"]["xgboost"] = "3.5.0"
    monkeypatch.setattr(env, "snapshot", lambda *a, **k: snap)
    assert colab_env.main(["install", "--json", str(tmp_path / "r.json")]) == 4          # restart required
    assert calls and "xgboost==3.4.1" in calls[0] and not any("torch" in c for c in calls[0])
    assert colab_env.main(["check"]) == 3                                                  # check never installs
    fatal = _session1_snapshot()
    fatal["packages"]["torch"] = "2.15.0+cu130"
    fatal["packages"]["xgboost"] = "3.5.0"
    monkeypatch.setattr(env, "snapshot", lambda *a, **k: fatal)
    calls.clear()
    assert colab_env.main(["install"]) == 3 and not calls                                  # fatal: no pip at all
    monkeypatch.setattr(env, "snapshot", lambda *a, **k: _session1_snapshot())
    assert colab_env.main(["check"]) == 0


# ------------------------------------------------------------------ cross-run compatibility

def _run_dir(tmp_path, name, snap=None, device="cuda"):
    snap = snap or _session1_snapshot()
    d = tmp_path / name
    d.mkdir()
    ident = {"run_id": name, "config_hash": "x", "device": device, "git_commit": snap["git"]["commit"],
             "dataset_sha256": snap["dataset"]["sha256"], "environment_fingerprint": env.fingerprint(snap),
             "environment": env.result_relevant(snap)}
    (d / "identity.json").write_text(json.dumps(ident))
    (d / "environment-20261111T000000.json").write_text(json.dumps({**snap, "utc_time": "t0", "ram_bytes": 1}))
    return d


def test_compatible_runs_pass_and_metadata_is_only_reported(tmp_path):
    a = _run_dir(tmp_path, "a")
    snap = _session1_snapshot()
    snap["gpu"]["nvidia_smi"] = ["Tesla T4, 15360 MiB, 581.00.01"]               # driver build: metadata
    b = _run_dir(tmp_path, "b", snap)
    (b / "environment-20261112T000000.json").write_text(json.dumps({**snap, "utc_time": "later", "ram_bytes": 2}))
    out = agg.check_compatible({"a": agg.environment_record(a), "b": agg.environment_record(b)})
    assert out["n_runs"] == 2 and out["environment"]["gpu_names"] == ["Tesla T4"]
    assert len(out["metadata_variation"]["nvidia_smi_values"]) == 2


@pytest.mark.parametrize("mutate,msg", [
    (lambda s: s["packages"].__setitem__("xgboost", "3.5.0"), "training environment differs"),
    (lambda s: s["packages"].__setitem__("scipy", "1.16.0"), "training environment differs"),
    (lambda s: s["gpu"]["devices"][0].__setitem__("name", "NVIDIA L4"), "training environment differs"),
    (lambda s: s["git"].__setitem__("commit", "f" * 40), "git_commit differs"),
])
def test_incompatible_runs_are_rejected_before_comparison(tmp_path, mutate, msg):
    a = _run_dir(tmp_path, "a")
    snap = _session1_snapshot()
    mutate(snap)
    b = _run_dir(tmp_path, "b", snap)
    with pytest.raises(RuntimeError, match=msg):
        agg.check_compatible({"a": agg.environment_record(a), "b": agg.environment_record(b)})


def test_mixed_devices_missing_and_tampered_provenance_are_rejected(tmp_path):
    cpu = _session1_snapshot()
    cpu["device"] = "cpu"
    a, b = _run_dir(tmp_path, "a"), _run_dir(tmp_path, "b", cpu, device="cpu")
    with pytest.raises(RuntimeError, match="differs"):
        agg.check_compatible({"a": agg.environment_record(a), "b": agg.environment_record(b)})
    c = _run_dir(tmp_path, "c", device="cpu")                                    # trained on cpu, env says cuda
    with pytest.raises(RuntimeError, match="trained on cpu"):
        agg.environment_record(c)
    d = _run_dir(tmp_path, "d")
    next(d.glob("environment-*.json")).unlink()
    with pytest.raises(RuntimeError, match="missing"):
        agg.environment_record(d)
    e = _run_dir(tmp_path, "e")
    ident = json.loads((e / "identity.json").read_text())
    del ident["environment_fingerprint"]
    (e / "identity.json").write_text(json.dumps(ident))
    with pytest.raises(RuntimeError, match="missing provenance"):
        agg.environment_record(e)
    f = _run_dir(tmp_path, "f")
    ident = json.loads((f / "identity.json").read_text())
    ident["environment"]["packages"]["torch"] = "9.9"                            # tampered identity
    (f / "identity.json").write_text(json.dumps(ident))
    with pytest.raises(RuntimeError, match="tampered"):
        agg.environment_record(f)
    g = _run_dir(tmp_path, "g")
    snap = json.loads(next(g.glob("environment-*.json")).read_text())
    snap["packages"]["numpy"] = "1.26.4"                                         # tampered environment file
    (g / "environment-20261113T000000.json").write_text(json.dumps(snap))
    with pytest.raises(RuntimeError, match="differs from the run's training environment"):
        agg.environment_record(g)
    h = _run_dir(tmp_path, "h")
    ident = json.loads((h / "identity.json").read_text())
    ident["resumed_from_commit"] = "0" * 40
    (h / "identity.json").write_text(json.dumps(ident))
    with pytest.raises(RuntimeError, match="different code commit"):
        agg.environment_record(h)


def test_historical_laptop_runs_are_not_comparable_with_colab_runs(tmp_path):
    mk = _run_dir
    laptop = env.snapshot()                                     # this machine (laptop or CI), not Colab
    laptop.update(git=_session1_snapshot()["git"], dataset=_session1_snapshot()["dataset"])
    a = mk(tmp_path, "colab")
    b = mk(tmp_path, "laptop", laptop, device=laptop["device"])
    if env.fingerprint(laptop) == env.fingerprint(_session1_snapshot()):
        pytest.skip("test machine reproduces the Colab environment exactly")
    with pytest.raises(RuntimeError, match="training environment differs"):
        agg.check_compatible({"colab": agg.environment_record(a), "laptop": agg.environment_record(b)})


# ------------------------------------------------------------------ runner: no resume in another environment

def test_runner_refuses_to_resume_in_a_different_environment(tmp_path, monkeypatch):
    from src.experiments import ae_xgb
    from test_ae_xgb import _loader, _tiny_cfg
    cfg = _tiny_cfg()
    run_dir = ae_xgb.run(cfg, "cpu", tmp_path, loader=_loader)
    ident = json.loads((run_dir / "identity.json").read_text())
    assert ident["environment_fingerprint"] == env.fingerprint(env.snapshot()) and "environment" in ident
    assert agg.environment_record(run_dir)["fingerprint"] == ident["environment_fingerprint"]
    (run_dir / "DONE").unlink()                                                   # simulate an interrupted run
    real = env.snapshot
    monkeypatch.setattr(env, "snapshot", lambda *a, **k: {**real(*a, **k), "packages": {
        **real(*a, **k)["packages"], "xgboost": "0.0.0"}})
    with pytest.raises(RuntimeError, match="training-relevant environment changed"):
        ae_xgb.run(cfg, "cpu", tmp_path, loader=_loader)


@pytest.mark.skipif(not (ROOT / "data/raw/cicids2017_original/MachineLearningCSV.zip").is_file(),
                    reason="CICIDS2017 archive not available")
def test_split_and_population_verify_reproduces_records():
    from src.experiments.population import verify
    out = verify()
    assert out["split_matches"] and out["val_kept_matches"] and out["test_kept_matches"]
    assert (out["val_kept"], out["test_kept"]) == (33134, 33038)
    assert "path" not in json.dumps(out["data_provenance"]).lower()             # names only, no local paths
