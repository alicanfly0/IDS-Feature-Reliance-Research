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
