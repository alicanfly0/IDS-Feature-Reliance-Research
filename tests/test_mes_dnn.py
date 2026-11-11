"""D-010 two-network MES-DNN adaptation: partitions, model structure, frozen subsample record."""
import json

import numpy as np
import pandas as pd
import pytest

torch = pytest.importorskip("torch")

from src.config import ROOT  # noqa: E402
from src.data import netflow  # noqa: E402
from src.experiments import mes_dnn as M  # noqa: E402


def _toy(n=4000, seed=0, dup=True):
    rng = np.random.default_rng(seed)
    X = rng.integers(0, 8 if dup else 10**6, size=(n, 3)).astype(float)
    y = (X[:, 0] > 4).astype(np.int64)
    gid = M.group_ids(pd.DataFrame(X))
    return X, y, gid


def test_partitions_are_disjoint_and_sized_like_the_paper():
    X, y, gid = _toy(dup=False)
    p = M.partition("random", 3, y, gid)
    rec = M.partition_record(p, y, gid)
    assert sum(rec["rows"].values()) == len(y)
    for k, f in M.FRACTIONS.items():
        assert abs(rec["rows"][k] / len(y) - f) < 0.005
    assert np.array_equal(p, M.partition("random", 3, y, gid)) and not np.array_equal(p, M.partition("random", 4, y, gid))


def test_dup_aware_puts_every_vector_in_one_partition():
    X, y, gid = _toy()
    rnd = M.partition_record(M.partition("random", 0, y, gid), y, gid)
    p = M.partition("dup_aware", 0, y, gid)
    rec = M.partition_record(p, y, gid)
    assert pd.Series(p).groupby(gid).nunique().max() == 1
    assert rec["test_rows_with_vector_seen_in_base_meta_val"] == 0 and rec["test_rows_novel"] == rec["rows"]["test"]
    assert rnd["test_rows_with_vector_seen_in_base_meta_val"] > 0.9 * rnd["rows"]["test"]


def test_meta_model_freezes_bases_and_stacks_their_outputs():
    Base, Meta = M._models()
    bases = [Base(np.zeros(39), np.ones(39)) for _ in range(2)]
    assert [m.out_features for m in bases[0].body if isinstance(m, torch.nn.Linear)] == [9, 7, 5, 3, 1]
    meta = Meta(bases)
    trainable = [n for n, p in meta.named_parameters() if p.requires_grad]
    assert trainable == ["head.0.weight", "head.0.bias", "head.2.weight", "head.2.bias"]
    assert meta.head[0].in_features == 2 and meta.head[0].out_features == 10
    assert meta(torch.rand(4, 39)).shape == (4,)


def test_run_one_on_synthetic_networks(monkeypatch):
    monkeypatch.setitem(M.HP, "epochs", 1)
    nets = {}
    for i, name in enumerate(["N1_unsw", "N2_ton"]):
        X, y, gid = _toy(3000, seed=i)
        X = np.hstack([X, np.zeros((len(X), 36))])
        nets[name] = {"X": X, "y": y, "gid": gid}
    info, art = M.run_one(nets, "dup_aware", 0, log=lambda *_: None)
    assert set(info["test"]) == {f"{n}/{m}" for n in nets for m in ("ensemble", "base_N1_unsw", "base_N2_ton")}
    assert info["meta"]["rows"] == sum(info["partitions"][n]["rows"]["meta"] for n in nets)
    t = info["test"]["N1_unsw/ensemble"]
    assert t["all"]["n"] == t["novel_vectors"]["n"] == info["partitions"]["N1_unsw"]["rows"]["test"]


@pytest.mark.skipif(not netflow.RECORD.is_file(), reason="subsample record not generated")
def test_frozen_ton_subsample_record():
    r = json.loads(netflow.RECORD.read_text(encoding="utf-8"))
    assert r["source_rows"] == 16_940_496 and r["subsample_size"] == 2_390_275
    assert r["csv_sha1_verified"] == netflow.TON_SHA1
    assert sum(r["label_counts"].values()) == r["subsample_size"]
    assert len(netflow.inputs()) == 39
