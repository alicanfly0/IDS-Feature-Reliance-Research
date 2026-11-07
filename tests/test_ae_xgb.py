"""AE-XGBoost pipeline on small synthetic fixtures (no real data, CPU only)."""
import json

import numpy as np
import pandas as pd
import pytest
import torch

from src.config import ROOT
from src.data import ddos
from src.evaluation.metrics import binary_metrics
from src.experiments import ae_xgb
from src.models import augment as aug
from src.models import autoencoder as ae
from src.models import xgb as xgbm

AE_CFG = {"hidden": [16], "latent": 4, "activation": "relu", "latent_activation": "relu",
          "output_activation": "linear", "lr": 0.01, "batch_size": 32, "max_epochs": 4, "patience": 10, "min_delta": 0.0}


def _xy(n=400, d=10, seed=0):
    rng = np.random.default_rng(seed)
    y = (rng.random(n) < 0.6).astype(np.int8)
    x = rng.random((n, d)).astype(np.float32) * 0.5 + y[:, None] * 0.4
    return x, y


def _flows(n=900, seed=1) -> pd.DataFrame:
    """CIC-like frame: duplicates, sentinels, invalid rows and one conflicting-label group."""
    rng = np.random.default_rng(seed)
    ddos_ = rng.random(n) < 0.57
    df = pd.DataFrame({
        "Destination Port": np.where(ddos_, 80, rng.choice([22, 443, 53], n)),
        "Flow Duration": rng.integers(0, 10_000, n).astype(float),
        "Flow Bytes/s": rng.random(n) * 1e4 + ddos_ * 5e3,
        "Init_Win_bytes_forward": np.where(rng.random(n) < 0.2, -1, rng.integers(0, 65535, n)),
        "Init_Win_bytes_backward": np.where(rng.random(n) < 0.3, -1, rng.integers(0, 65535, n)),
        "Fwd URG Flags": np.zeros(n),
        "Label": np.where(ddos_, "DDoS", "BENIGN"),
    })
    df = pd.concat([df, df.iloc[:60]], ignore_index=True)         # exact duplicates
    df.loc[len(df)] = df.loc[0].copy()                              # same vector ...
    df.loc[len(df) - 1, "Label"] = "BENIGN" if df.loc[0, "Label"] == "DDoS" else "DDoS"  # ... other label
    df.loc[5, "Flow Bytes/s"] = np.nan
    df.loc[6, "Flow Bytes/s"] = np.inf
    df.loc[7, "Flow Duration"] = -3.0
    return df


# ------------------------------------------------------------------ data preparation

def test_prepare_counts_rules_conflicts_and_leakage():
    df = _flows()
    prep = ddos.prepare(df, {"BENIGN": 0, "DDoS": 1})
    r = prep.report
    assert r["raw_rows"] == len(df) and r["invalid_rows"] == 3
    assert r["rule_rows"] == {"missing": 1, "infinite": 1, "negative:Flow Duration": 1}
    assert r["conflicting_label_groups"] == 1 and r["conflicting_label_rows_excluded"] >= 2
    assert r["partition_overlap"] == {"train_val": 0, "train_test": 0, "val_test": 0}
    assert r["sentinel_minus1_Init_Win_bytes_forward"]["kept"] > 0     # sentinel is not a rule
    assert r["kept_rows"] == len(df) - 3 - r["conflicting_label_rows_excluded"]
    assert sorted(set(prep.y)) == [0, 1] and prep.y.sum() == (prep.frame["Label"] == "DDoS").sum()
    assert prep.frame.index.is_unique                                   # source rows preserved
    again = ddos.prepare(df, {"BENIGN": 0, "DDoS": 1})
    assert again.split.fingerprint() == prep.split.fingerprint()       # reproducible


def test_prepare_rejects_unknown_labels():
    df = _flows()
    df.loc[10, "Label"] = "PortScan"
    with pytest.raises(ValueError, match="PortScan"):
        ddos.prepare(df, {"BENIGN": 0, "DDoS": 1})


# ------------------------------------------------------------------ autoencoder

def test_autoencoder_shapes_and_finiteness():
    model = ae.build(10, {**AE_CFG, "hidden": [80], "latent": 40})
    out = model(torch.rand(7, 10))
    assert out.shape == (7, 10) and torch.isfinite(out).all()
    z = ae.encode(model, np.random.rand(5, 10).astype(np.float32), "cpu")
    assert z.shape == (5, 40) and np.isfinite(z).all()


def test_checkpoint_resume_matches_uninterrupted_training(tmp_path):
    x, _ = _xy()
    xt, xv = x[:300], x[300:]
    torch.manual_seed(0)
    straight = ae.build(10, AE_CFG)
    ae.train(straight, xt, xv, AE_CFG, "cpu", seed=3, ckpt_dir=tmp_path / "a", log=lambda m: None)

    class Crash(Exception):
        pass

    def crash_after_epoch_1(msg):
        if msg.startswith("epoch   1"):
            raise Crash

    torch.manual_seed(0)
    interrupted = ae.build(10, AE_CFG)
    with pytest.raises(Crash):
        ae.train(interrupted, xt, xv, AE_CFG, "cpu", seed=3, ckpt_dir=tmp_path / "b", log=crash_after_epoch_1)
    resumed = ae.build(10, AE_CFG)            # fresh process: weights come from the checkpoint
    state = ae.train(resumed, xt, xv, AE_CFG, "cpu", seed=3, ckpt_dir=tmp_path / "b", log=lambda m: None)

    assert state["epoch"] == AE_CFG["max_epochs"] and "max_epochs" in state["stopped"]
    for a, b in zip(straight.state_dict().values(), resumed.state_dict().values()):
        assert torch.equal(a, b)
    hist_a = torch.load(tmp_path / "a" / "ae_last.pt", weights_only=False)["state"]["history"]
    assert [h["val_mse"] for h in hist_a] == [h["val_mse"] for h in state["history"]]
    # A finished run is not retrained.
    again = ae.train(ae.build(10, AE_CFG), xt, xv, AE_CFG, "cpu", seed=3, ckpt_dir=tmp_path / "b", log=lambda m: None)
    assert again["epoch"] == AE_CFG["max_epochs"]


def test_early_stopping_restores_best_weights(tmp_path):
    x, _ = _xy()
    cfg = {**AE_CFG, "max_epochs": 50, "patience": 2, "min_delta": 1.0}   # nothing counts as improvement after epoch 0
    model = ae.build(10, cfg)
    state = ae.train(model, x[:300], x[300:], cfg, "cpu", seed=0, ckpt_dir=tmp_path, log=lambda m: None)
    assert state["best_epoch"] == 0 and state["epoch"] == 3 and "early stopping" in state["stopped"]
    best = torch.load(tmp_path / "ae_best.pt", weights_only=True)
    assert all(torch.equal(best[k], v) for k, v in model.state_dict().items())


# ------------------------------------------------------------------ augmentation

def test_augmentation_rule_and_generation(tmp_path):
    assert aug.plan(np.array([1] * 60 + [0] * 40))["applicable"] is False      # attack is the majority
    p = aug.plan(np.array([1] * 30 + [0] * 70))
    assert p["applicable"] and p["n_new"] == 40
    x, _ = _xy()
    model = ae.build(10, AE_CFG)
    ae.train(model, x[:300], x[300:], AE_CFG, "cpu", seed=0, ckpt_dir=tmp_path, log=lambda m: None)
    z_new, info = aug.generate(model, x[:50], 40, 0.1, 0.95, "cpu", seed=1)
    assert z_new.shape[1] == AE_CFG["latent"] and len(z_new) == info["kept"] <= 40 and np.isfinite(z_new).all()
    z_again, _ = aug.generate(model, x[:50], 40, 0.1, 0.95, "cpu", seed=1)
    assert np.array_equal(z_new, z_again)


# ------------------------------------------------------------------ XGBoost and metrics

def test_xgboost_fit_predict_save_load(tmp_path):
    x, y = _xy(600, 6)
    params = {"n_estimators": 200, "learning_rate": 0.11, "max_depth": 6, "reg_alpha": 0, "reg_lambda": 1,
              "subsample": 0.8, "colsample_bytree": 0.8, "early_stopping_rounds": 5}
    clf = xgbm.fit(x[:400], y[:400], x[400:500], y[400:500], params, "cpu", seed=0)
    assert clf.best_iteration is not None and clf.best_iteration < 200
    prob = xgbm.predict_positive(clf, x[500:])
    assert prob.shape == (100,) and ((prob >= 0) & (prob <= 1)).all()
    xgbm.save(clf, tmp_path / "m.json")
    assert np.allclose(xgbm.predict_positive(xgbm.load(tmp_path / "m.json"), x[500:]), prob)
    assert binary_metrics(y[500:], prob)["auroc"] > 0.9
    assert xgbm.check_within_paper_ranges({**params, "learning_rate": 0.5})


def test_binary_metrics_positive_class_and_counts():
    y = np.array([0, 0, 1, 1, 1])
    prob = np.array([0.1, 0.6, 0.9, 0.4, 0.8])
    m = binary_metrics(y, prob)
    assert m["confusion_matrix"] == {"tn": 1, "fp": 1, "fn": 1, "tp": 2}
    assert m["precision"] == pytest.approx(2 / 3) and m["recall"] == pytest.approx(2 / 3)
    assert m["class_counts"] == {"negative_0": 2, "positive_1": 3}
    assert m["auroc"] == pytest.approx(5 / 6)
    with pytest.raises(ValueError):
        binary_metrics(y, np.array([0.1, np.nan, 0.2, 0.3, 0.4]))


def test_cuda_request_fails_without_gpu(monkeypatch):
    from src import env
    monkeypatch.setattr(env, "_torch", lambda: None)
    with pytest.raises(RuntimeError, match="CUDA requested"):
        ae_xgb.resolve_device("cuda")


# ------------------------------------------------------------------ runner

def _tiny_cfg():
    cfg = ae_xgb.load_experiment(ROOT / "configs" / "experiments" / "ae_xgb_d008_smoke.yaml")
    cfg["experiment"]["name"] = "synthetic_test"
    cfg["run"]["sample"] = None
    cfg["ae"].update(max_epochs=2, batch_size=64)
    cfg["xgb"].update(n_estimators=10, early_stopping_rounds=3)
    return cfg


def _loader():
    return _flows(), {"archive": "synthetic", "csv_sha256": "synthetic"}


def test_runner_end_to_end_resume_and_no_overwrite(tmp_path, capsys):
    cfg = _tiny_cfg()
    run_dir = ae_xgb.run(cfg, "cpu", tmp_path, loader=_loader)
    for name in ("DONE", "run_record.json", "metrics.json", "predictions_val.csv.gz", "predictions_test.csv.gz",
                 "preprocessor.json", "data_report.json", "latent.npz", "xgb_model.json", "checkpoints/ae_best.pt"):
        assert (run_dir / name).is_file(), name
    metrics = json.loads((run_dir / "metrics.json").read_text())
    record = json.loads((run_dir / "run_record.json").read_text())
    assert set(metrics) >= {"train", "val", "test"} and metrics["test"]["n"] == len(
        pd.read_csv(run_dir / "predictions_test.csv.gz"))
    assert record["augmentation"]["applicable"] in (True, False) and record["input_dim"] == 5  # constant column dropped
    assert json.loads((run_dir / "preprocessor.json").read_text())["processed_partition_overlap"] == {
        "train_val": 0, "train_test": 0, "val_test": 0}
    assert (tmp_path / "splits" / "synthetic_test-split.json").is_file()

    # Completed: a second call recomputes nothing.
    stamp = (run_dir / "metrics.json").stat().st_mtime_ns
    ae_xgb.run(cfg, "cpu", tmp_path, loader=_loader)
    assert (run_dir / "metrics.json").stat().st_mtime_ns == stamp
    assert "already complete" in capsys.readouterr().out

    # Disconnected after the AE: the AE is not retrained, XGBoost is.
    for name in ("DONE", "xgb_model.json", "metrics.json", "run_record.json"):
        (run_dir / name).unlink()
    ae_xgb.run(cfg, "cpu", tmp_path, loader=_loader)
    assert "latent codes loaded from cache" in (run_dir / "log.txt").read_text()
    assert json.loads((run_dir / "metrics.json").read_text())["test"] == metrics["test"]   # deterministic on CPU

    # Resuming under different code is refused unless explicitly allowed.
    (run_dir / "DONE").unlink()
    ident = json.loads((run_dir / "identity.json").read_text())
    ident["git_commit"] = "0" * 40
    (run_dir / "identity.json").write_text(json.dumps(ident))
    with pytest.raises(RuntimeError, match="commit changed"):
        ae_xgb.run(cfg, "cpu", tmp_path, loader=_loader)


def test_config_change_gives_a_new_run_and_split_is_reused(tmp_path):
    cfg = _tiny_cfg()
    first = ae_xgb.run(cfg, "cpu", tmp_path, loader=_loader)
    cfg["xgb"]["learning_rate"] = 0.06
    second = ae_xgb.run(cfg, "cpu", tmp_path, loader=_loader)
    assert first != second and (first / "DONE").is_file() and (second / "DONE").is_file()
    rec1, rec2 = (json.loads((d / "run_record.json").read_text()) for d in (first, second))
    assert rec1["split_fingerprint"] == rec2["split_fingerprint"]          # same evaluation population
    assert "split verified" in (second / "log.txt").read_text()
