import json
import random

import numpy as np
import pytest

from src import env


def test_snapshot_has_provenance_fields():
    snap = env.snapshot(seed=7, dataset_id="nf_unsw_nb15_v2")
    for key in ("python", "os", "cpu", "cpu_count", "ram_bytes", "in_colab", "device", "gpu", "packages", "git"):
        assert key in snap
    assert snap["seed"] == 7 and snap["device"] in ("cpu", "cuda")
    assert snap["dataset"]["sha256"]["NF-UNSW-NB15-v2.zip"].startswith("0e42c11d")
    assert snap["packages"]["numpy"] == np.__version__
    json.dumps(snap)  # serializable for the run record


def test_device_selection_without_gpu(monkeypatch):
    monkeypatch.setattr(env, "_torch", lambda: None)  # behave like a machine without torch
    assert env.select_device("auto") == "cpu"
    assert env.select_device("cpu") == "cpu"
    with pytest.raises(RuntimeError, match="CUDA requested"):
        env.select_device("cuda")
    with pytest.raises(ValueError):
        env.select_device("gpu")


def test_set_seeds_is_reproducible():
    env.set_seeds(123)
    first = (random.random(), np.random.rand())
    env.set_seeds(123)
    assert (random.random(), np.random.rand()) == first


def test_cli_writes_json(tmp_path, capsys):
    out = tmp_path / "environment.json"
    assert env.main(["--json", str(out)]) == 0
    assert json.loads(out.read_text(encoding="utf-8"))["python"]
    capsys.readouterr()


def test_archive_mode_has_no_git_history_and_skips_only_history_tests(tmp_path):
    """A git-archive bundle (no .git) must be detected; the checkout here is a real repository."""
    from src.config import ROOT
    from src.env import git_history_available
    assert git_history_available(tmp_path) is False                 # bundle-like folder
    (tmp_path / ".git").mkdir()                                     # an empty .git is not a repository
    assert git_history_available(tmp_path) is False
    assert git_history_available(ROOT) == (ROOT / ".git").exists()
    import test_milestone2b as m
    marks = {name: [mk.name for mk in getattr(getattr(m, name), "pytestmark", [])]
             for name in ("test_original_registry_is_exact_git_snapshot", "test_original_registry_matches_recorded_v1_hash")}
    assert marks["test_original_registry_is_exact_git_snapshot"] == ["skipif"]
    assert marks["test_original_registry_matches_recorded_v1_hash"] == []        # archive-safe check never skips
