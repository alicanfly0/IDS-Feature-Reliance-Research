"""D-009 Fang DCNN + self-attention adaptation: model port, preprocessing, metrics, frozen records."""
import json

import numpy as np
import pandas as pd
import pytest

torch = pytest.importorskip("torch")

from src.config import ROOT  # noqa: E402
from src.experiments import dcnn_fang as F  # noqa: E402
from src.models.dcnn import DCNNSA  # noqa: E402

SEL = ROOT / "results/dcnn_fang/selection.json"


def test_architecture_matches_authors_keras_layers():
    m = DCNNSA(22)
    assert (m.conv1.out_channels, m.conv1.kernel_size, m.conv2.out_channels) == (32, (3,), 64)
    assert m.attn.num_heads == 4 and m.attn.head_dim == 16              # Keras key_dim = max(8, 64 // 4)
    assert (m.fc1.in_features, m.fc1.out_features, m.fc2.out_features, m.out.out_features) == (22 * 64, 128, 64, 1)
    assert m.bn1.eps == 1e-3 and m.bn1.momentum == pytest.approx(0.01) and m.norm.eps == 1e-3
    m.eval()
    p = m(torch.rand(5, 22))
    assert p.shape == (5,) and bool(((p > 0) & (p < 1)).all())
    expect = 1e-3 * sum(float((w ** 2).sum()) for w in (m.conv1.weight, m.conv2.weight, m.fc1.weight, m.fc2.weight))
    assert float(m.l2_penalty()) == pytest.approx(expect, rel=1e-5)


def test_preprocessor_is_fitted_on_train_only():
    tr = pd.DataFrame({"id": [1, 2, 3, 4], "a": [0.0, np.nan, 10.0, 1000.0], "proto": ["tcp", "udp", None, "tcp"],
                       "attack_cat": ["Normal"] * 4, "label": [0] * 4})
    te = pd.DataFrame({"id": [9], "a": [5000.0], "proto": ["icmp"], "attack_cat": ["DoS"], "label": [1]})
    pre = F.Preprocessor.fit(tr)
    assert pre.feature_names == ["a", "proto_Unknown", "proto_tcp", "proto_udp"]
    x = pre.transform(te)
    assert x[0, 0] == pytest.approx(1.0) and x[0, 1:].sum() == 0          # clipped to train 99th pct; unseen category ignored
    xt = pre.transform(tr)
    assert xt[:, 0].min() == 0 and xt[:, 0].max() == pytest.approx(1.0) and xt[2, 1] == 1 and xt[1, 3] == 1


def test_metrics_and_exact_row_keys():
    y = np.array([1, 1, 0, 0, 0])
    m = F.metrics(y, np.array([0.9, 0.2, 0.1, 0.7, 0.4]))
    assert (m["tp"], m["fn"], m["fp"], m["tn"], m["errors"]) == (1, 1, 1, 2, 2)
    assert m["fpr"] == pytest.approx(1 / 3) and m["dos_recall"] == 0.5
    a = np.array([[0.1, 0.2], [0.1, 0.2], [0.1, np.nextafter(np.float32(0.2), np.float32(1))]], dtype=np.float32)
    k = F._row_keys(a)
    assert k[0] == k[1] and k[0] != k[2]


def test_training_is_deterministic_per_seed():
    rng = np.random.default_rng(0)
    X = rng.random((300, 6))
    y = (X[:, 0] > 0.6).astype(np.int64)
    hp = {**F.TRAIN, "epochs": 2}
    out = []
    for _ in range(2):
        model, info = F.train_seed(3, X, y, hp=hp, log=lambda *_: None)
        out.append(F.predict(model, X))
    assert np.array_equal(out[0], out[1]) and info["epochs_run"] == 2 and info["fit_rows"] == 240


@pytest.mark.skipif(not SEL.is_file(), reason="selection record not generated")
def test_frozen_selection_record():
    r = json.loads(SEL.read_text(encoding="utf-8"))
    assert r["k"] == 22 and len(r["selected"]) == 22 and r["positive_class"] == "DoS"
    assert r["rows"] == {"train": 68264, "test": 41089, "train_dos": 12264, "test_dos": 4089}
    assert r["rule95_count"] == 30            # the paper's 95% rule picks 30 here; K = 22 is the approved spec
    mv = r["test_populations"]["model_visible"]
    assert mv["kept_rows"] + mv["excluded_rows"] == 41089 and mv["kept_rows"] == 37759
    assert r["lgbm_params"]["random_state"] == 42
