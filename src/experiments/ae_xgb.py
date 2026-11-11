"""AE-XGBoost baseline on the D-008 scope, leakage-resistant track (D-007 track B).

    python -m src.experiments.ae_xgb --config configs/experiments/ae_xgb_d008_trackB.yaml --device cuda \
        --storage /content/drive/MyDrive/cnet-runs
    python -m src.experiments.ae_xgb --config configs/experiments/ae_xgb_d008_smoke.yaml --device cpu
    python -m src.experiments.ae_xgb --config ... --benchmark      # timing + projected full-run cost

Stages (each saved atomically under <storage>/runs/<run_id>/, so a disconnected session
resumes where it stopped and a finished run is never recomputed or overwritten):
  split -> preprocess -> autoencoder (per-epoch checkpoints) -> latent codes
  -> optional training-only augmentation -> XGBoost (validation early stopping)
  -> evaluation on validation and test -> run_record.json -> DONE
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import time
from pathlib import Path

import numpy as np
import pandas as pd
import torch

from src import env
from src.config import ROOT, check_no_leaky_outputs, load_config, make_preprocessor
from src.data import ddos
from src.data.split import Split, content_groups, exclude_eval_twins, load_split, partition_overlap, save_split
from src.evaluation.metrics import binary_metrics
from src.experiments.population import apply_population, load_population
from src.models import augment as aug
from src.models import autoencoder as ae
from src.models import xgb as xgbm

PARTS = ("train", "val", "test")


def _write_json(path: Path, obj) -> None:
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(obj, indent=2, default=str), encoding="utf-8")
    os.replace(tmp, path)


def _read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def config_hash(cfg: dict) -> str:
    body = {k: v for k, v in cfg.items() if k != "config_files"}
    return hashlib.sha256(json.dumps(body, sort_keys=True, default=str).encode()).hexdigest()


class Logger:
    def __init__(self, path: Path | None = None):
        self.path = path

    def __call__(self, msg: str) -> None:
        line = f"[{time.strftime('%H:%M:%S')}] {msg}"
        print(line, flush=True)
        if self.path:
            with open(self.path, "a", encoding="utf-8") as f:
                f.write(line + "\n")


def resolve_device(requested: str) -> str:
    device = env.select_device(requested)   # "cuda" raises if no GPU: never silently fall back
    if device == "cuda" and not xgbm.cuda_build():
        raise RuntimeError("GPU requested but the installed XGBoost has no CUDA support")
    return device


# ---------------------------------------------------------------------------------- data

def prepare_data(cfg: dict, storage: Path, log, root: Path = ROOT, loader=None):
    """Verified data -> D-011 rules -> track-B split. The split is saved once per dataset+policy
    and every later run must reproduce it exactly (same evaluation population)."""
    d, s = cfg["data"], cfg["experiment"]["split"]
    if loader is None:
        csv, provenance = ddos.verified_csv(root)
        df = ddos.load(csv)
    else:
        df, provenance = loader()
    prep = ddos.prepare(df, d["label_map"], tuple(s["fractions"]), s["seed"], tuple(d["nonnegative_cols"]))
    source = {"dataset": cfg["experiment"]["dataset"], **provenance, "rules": d["nonnegative_cols"],
              "n_rows": len(prep.frame), "strategy": s["strategy"], "fractions": s["fractions"], "seed": s["seed"]}
    split_file = storage / "splits" / f"{cfg['experiment']['name']}-split.json"
    if split_file.is_file():
        saved = load_split(split_file, expected_source=source, n_rows=len(prep.frame))
        if saved.fingerprint() != prep.split.fingerprint():
            raise RuntimeError(f"recomputed split differs from the saved one ({split_file}); refusing to change the evaluation population")
        log(f"split verified against {split_file.name}")
    else:
        split_file.parent.mkdir(parents=True, exist_ok=True)
        save_split(prep.split, split_file, source=source)
        log(f"split saved to splits/{split_file.name}")   # no absolute paths in logs (audit F5)
    expected = s.get("expected_fingerprint")
    if expected and loader is None and prep.split.fingerprint() != expected:
        raise RuntimeError(f"split fingerprint {prep.split.fingerprint()} != expected {expected}")
    prep.report["split_fingerprint"] = prep.split.fingerprint()
    population = cfg["run"].get("eval_population")
    if population and cfg["run"].get("exclude_eval_twins"):
        raise ValueError("use either run.eval_population (family-common) or run.exclude_eval_twins, not both")
    if population:
        # Milestone 3B: identical validation/test rows for every model, from a validated record.
        drop = cfg["experiment"].get("extra_drop_cols", [])
        view = [c for c in prep.feature_cols if c not in drop]
        record = load_population(root / population["record"], population["sha256"])
        prep.split, prep.report["family_common_population"] = apply_population(prep, record, view)
        log(f"family-common population: val {prep.report['family_common_population']['val_kept']}, "
            f"test {prep.report['family_common_population']['test_kept']}")
    if cfg["run"].get("exclude_eval_twins"):
        # Feature-removal runs: same split and training rows, but validation/test rows whose
        # vector duplicates an earlier partition IN THIS MODEL'S INPUT VIEW are not evaluated.
        drop = cfg["experiment"].get("extra_drop_cols", [])
        view = [c for c in prep.feature_cols if c not in drop]
        reduced, info = exclude_eval_twins(content_groups(prep.frame, view), prep.split)
        rows = prep.frame.index.to_numpy()
        prep.report["eval_twin_exclusion"] = {
            "feature_view": len(view), "dropped_features": drop,
            "val_excluded": info["val_excluded"], "test_excluded": info["test_excluded"],
            "val_excluded_source_rows": rows[info["val_excluded_positions"]].tolist(),
            "test_excluded_source_rows": rows[info["test_excluded_positions"]].tolist(),
        }
        prep.split = reduced
        log(f"evaluation twins excluded in the {len(view)}-feature view: val {info['val_excluded']}, test {info['test_excluded']}")
    if cfg["run"].get("sample"):
        prep = ddos.subsample(prep, cfg["run"]["sample"], cfg["run"]["model_seed"])
        log(f"SMOKE subsample: {prep.report['subsample']}")
    return prep, source, split_file


def preprocess(cfg: dict, prep, log):
    pre = make_preprocessor(cfg)
    parts = prep.split.parts()
    x = {"train": pre.fit_transform(prep.frame.iloc[parts["train"]])}
    for p in ("val", "test"):
        x[p] = pre.transform(prep.frame.iloc[parts[p]])
    check_no_leaky_outputs(pre.output_columns, cfg)
    arrays = {p: x[p].to_numpy(dtype=np.float32) for p in PARTS}
    # Leakage re-check on what the model actually sees (after constant removal and scaling).
    processed = pd.DataFrame(np.concatenate([arrays[p] for p in PARTS]))
    sizes = [len(arrays[p]) for p in PARTS]
    offsets = np.cumsum([0] + sizes)
    pos = Split(*(np.arange(offsets[i], offsets[i + 1]) for i in range(3)), "positional", None)
    overlap = partition_overlap(content_groups(processed, list(processed.columns)), pos)
    if any(overlap.values()):
        raise AssertionError(f"preprocessed vectors shared across partitions: {overlap}")
    state = {**pre.state(), "medians": pre.medians_, "mins": pre.mins_, "maxs": pre.maxs_,
             "input_dim": len(pre.output_columns), "processed_partition_overlap": overlap}
    log(f"preprocessing: {len(pre.constant_cols_)} constant-on-train columns dropped -> input dim {state['input_dim']}")
    return arrays, state


# ---------------------------------------------------------------------------------- run

def run(cfg: dict, device: str, storage: Path, allow_code_change: bool = False, loader=None, root: Path = ROOT) -> Path:
    model_seed = cfg["run"]["model_seed"]
    chash = config_hash(cfg)
    run_id = f"{cfg['experiment']['name']}-seed{model_seed}-{device}-{chash[:8]}"
    run_dir = storage / "runs" / run_id
    if (run_dir / "DONE").is_file():
        print(f"{run_id} is already complete; nothing recomputed. Results: {run_dir}")
        return run_dir
    run_dir.mkdir(parents=True, exist_ok=True)
    log = Logger(run_dir / "log.txt")
    snap = env.snapshot(seed=model_seed, dataset_id=cfg["experiment"]["dataset"])
    snap["available_device"] = snap["device"]
    snap["device"] = device   # the device this run TRAINS on (not merely the best one available)
    identity = {"run_id": run_id, "config_hash": chash, "device": device, "git_commit": snap["git"]["commit"],
                "dataset_sha256": snap["dataset"]["sha256"],
                # Milestone 3B-1: training-relevant environment (Python minor, platform, device, GPU, CUDA,
                # numpy/pandas/scipy/scikit-learn/torch/xgboost). A run is never resumed in another one.
                "environment_fingerprint": env.fingerprint(snap), "environment": env.result_relevant(snap)}
    id_file = run_dir / "identity.json"
    if id_file.is_file():
        old = _read_json(id_file)
        for key in ("config_hash", "device", "dataset_sha256"):
            if old[key] != identity[key]:
                raise RuntimeError(f"cannot resume {run_id}: {key} changed")
        if "environment_fingerprint" in old and old["environment_fingerprint"] != identity["environment_fingerprint"]:
            raise RuntimeError(f"cannot resume {run_id}: training-relevant environment changed "
                               f"{old.get('environment')} -> {identity['environment']}")
        if old["git_commit"] != identity["git_commit"] and not allow_code_change:
            raise RuntimeError(f"cannot resume {run_id}: code commit changed {old['git_commit']} -> "
                               f"{identity['git_commit']} (pass --allow-code-change to accept and record it)")
        identity["resumed_from_commit"] = old["git_commit"]
        log(f"resuming {run_id}")
    else:
        _write_json(id_file, identity)
        log(f"new run {run_id}")
    _write_json(run_dir / "effective_config.json", cfg)
    _write_json(run_dir / f"environment-{time.strftime('%Y%m%dT%H%M%S')}.json", snap)
    timings = {}
    env.set_seeds(model_seed)

    t = time.perf_counter()
    prep, source, split_file = prepare_data(cfg, storage, log, root=root, loader=loader)
    _write_json(run_dir / "data_report.json", prep.report)
    arrays, pre_state = preprocess(cfg, prep, log)
    _write_json(run_dir / "preprocessor.json", pre_state)
    timings["data_and_preprocess_s"] = round(time.perf_counter() - t, 2)
    y = {p: prep.y[i] for p, i in prep.split.parts().items()}
    rows = {p: prep.frame.index.to_numpy()[i] for p, i in prep.split.parts().items()}

    # Autoencoder (resumable) and latent codes (cached so an XGBoost crash never retrains the AE).
    model = ae.build(arrays["train"].shape[1], cfg["ae"])
    latent_file = run_dir / "latent.npz"
    if latent_file.is_file():
        with np.load(latent_file) as f:
            z = {p: f[p] for p in PARTS}
        model.load_state_dict(torch.load(run_dir / "checkpoints" / "ae_best.pt", map_location=device, weights_only=True))
        ae_state = _read_json(run_dir / "ae_done.json")
        log("latent codes loaded from cache")
    else:
        t = time.perf_counter()
        ae_state = ae.train(model, arrays["train"], arrays["val"], cfg["ae"], device, model_seed,
                            run_dir / "checkpoints", log=log)
        timings["autoencoder_s"] = round(time.perf_counter() - t, 2)
        _write_json(run_dir / "ae_done.json", ae_state)
        z = {p: ae.encode(model, arrays[p], device) for p in PARTS}
        tmp = run_dir / "latent.tmp.npz"
        np.savez_compressed(tmp, **z)
        os.replace(tmp, latent_file)

    # Augmentation: training partition only, and only where the paper's rule applies.
    z_train, y_train = z["train"], y["train"]
    aug_info = {"enabled": cfg["augment"]["enabled"], **aug.plan(y_train)}
    if cfg["augment"]["enabled"] and aug_info["applicable"]:
        x_minority = arrays["train"][y_train == 1]
        z_new, info = aug.generate(model, x_minority, aug_info["n_new"], cfg["augment"]["sigma_scale"],
                                   cfg["augment"]["keep_quantile"], device, model_seed)
        z_train = np.concatenate([z_train, z_new])
        y_train = np.concatenate([y_train, np.ones(len(z_new), dtype=y_train.dtype)])
        aug_info.update(info)
    log(f"augmentation: {aug_info}")

    # XGBoost with validation early stopping.
    xgb_file = run_dir / "xgb_model.json"
    if xgb_file.is_file():
        clf = xgbm.load(xgb_file)
        log("XGBoost model loaded from checkpoint")
    else:
        t = time.perf_counter()
        clf = xgbm.fit(z_train, y_train, z["val"], y["val"], cfg["xgb"], device, model_seed)
        timings["xgboost_s"] = round(time.perf_counter() - t, 2)
        xgbm.save(clf, xgb_file)
        log(f"XGBoost best iteration {clf.best_iteration}")

    # Evaluation: validation and test kept separate; threshold fixed in the config.
    thr = cfg["run"]["threshold"]
    metrics, preds = {}, {}
    for p in PARTS:
        prob = xgbm.predict_positive(clf, z[p])
        metrics[p] = binary_metrics(y[p], prob, thr)
        preds[p] = pd.DataFrame({"source_row": rows[p], "y_true": y[p], "prob_ddos": prob,
                                 "y_pred": (prob >= thr).astype(int)})
    for p in ("val", "test"):
        tmp = run_dir / f"predictions_{p}.tmp.csv.gz"
        with gzip.open(tmp, "wt", encoding="utf-8", newline="") as f:
            preds[p].to_csv(f, index=False)
        os.replace(tmp, run_dir / f"predictions_{p}.csv.gz")
    metrics["note"] = "train metrics are for overfitting diagnosis only; validation selected the model; test was not used for any choice"
    _write_json(run_dir / "metrics.json", metrics)
    log("validation: " + json.dumps({k: metrics["val"][k] for k in ("f1", "macro_f1", "auroc", "mcc")}))
    log("test:       " + json.dumps({k: metrics["test"][k] for k in ("f1", "macro_f1", "auroc", "mcc")}))

    record = {
        "identity": identity, "split_file": split_file.name, "split_source": source,
        "split_fingerprint": prep.report["split_fingerprint"],     # the pinned split (before any exclusion)
        "evaluation_fingerprint": prep.split.fingerprint(),        # population actually trained/evaluated
        "data_report_file": "data_report.json",
        "preprocessor_file": "preprocessor.json", "input_dim": pre_state["input_dim"],
        "autoencoder": {"best_epoch": ae_state["best_epoch"], "best_val_mse": ae_state["best_val"],
                        "epochs_run": ae_state["epoch"], "stopped": ae_state["stopped"]},
        "augmentation": aug_info,
        "xgboost": {"best_iteration": int(clf.best_iteration) if clf.best_iteration is not None else None,
                    "params": cfg["xgb"], "outside_paper_ranges": xgbm.check_within_paper_ranges(cfg["xgb"])},
        "metrics_file": "metrics.json", "timings": timings, "smoke": bool(cfg["run"].get("sample")),
    }
    _write_json(run_dir / "run_record.json", record)
    _write_json(run_dir / "DONE", {"completed": time.strftime("%Y-%m-%dT%H:%M:%S"), "run_id": run_id})
    log(f"DONE -> runs/{run_id}")
    return run_dir


# ---------------------------------------------------------------------------------- benchmark

def benchmark(cfg: dict, device: str, storage: Path, ae_batches: int = 60, xgb_rounds: int = 50) -> dict:
    """Time a few AE batches and XGBoost rounds on the real training partition, then project."""
    log = Logger()
    env.set_seeds(cfg["run"]["model_seed"])
    t = time.perf_counter()
    prep, _, _ = prepare_data(cfg, storage, log)
    arrays, _ = preprocess(cfg, prep, log)
    data_s = time.perf_counter() - t
    model = ae.build(arrays["train"].shape[1], cfg["ae"]).to(device)
    xt = torch.from_numpy(arrays["train"]).to(device)
    opt = torch.optim.Adam(model.parameters(), lr=cfg["ae"]["lr"])
    bs, loss_fn = cfg["ae"]["batch_size"], torch.nn.MSELoss()
    for warm in (True, False):
        if device == "cuda":
            torch.cuda.synchronize()
        t = time.perf_counter()
        for b in range(5 if warm else ae_batches):
            xb = xt[b * bs:(b + 1) * bs]
            opt.zero_grad()
            loss_fn(model(xb), xb).backward()
            opt.step()
        if device == "cuda":
            torch.cuda.synchronize()
    per_batch = (time.perf_counter() - t) / ae_batches
    t = time.perf_counter()
    ae.reconstruction_mse(model, torch.from_numpy(arrays["val"]).to(device))
    val_s = time.perf_counter() - t
    batches_per_epoch = -(-len(arrays["train"]) // bs)
    epoch_s = per_batch * batches_per_epoch + val_s
    z_train = ae.encode(model, arrays["train"], device)
    z_val = ae.encode(model, arrays["val"], device)
    params = {**cfg["xgb"], "n_estimators": xgb_rounds, "early_stopping_rounds": None}
    t = time.perf_counter()
    xgbm.fit(z_train, prep.y[prep.split.train], z_val, prep.y[prep.split.val], params, device, 0)
    per_round = (time.perf_counter() - t) / xgb_rounds
    max_epochs, max_rounds = cfg["ae"]["max_epochs"], cfg["xgb"]["n_estimators"]
    result = {
        "device": device, "snapshot": env.snapshot(), "train_rows": len(arrays["train"]), "input_dim": arrays["train"].shape[1],
        "measured": {"data_and_preprocess_s": round(data_s, 2), "ae_seconds_per_batch": per_batch,
                     "ae_batches_per_epoch": batches_per_epoch, "ae_seconds_per_epoch": round(epoch_s, 2),
                     "xgb_seconds_per_round": per_round},
        "projection_upper_bound_minutes": {
            "autoencoder_max_epochs": round(epoch_s * max_epochs / 60, 1),
            "xgboost_max_rounds": round(per_round * max_rounds / 60, 1),
        },
        "projection_assumptions": f"AE runs all {max_epochs} epochs and XGBoost all {max_rounds} rounds "
                                  "(early stopping usually ends both sooner); excludes Drive I/O and session start-up",
    }
    out = storage / "benchmarks" / f"benchmark-{device}-{time.strftime('%Y%m%dT%H%M%S')}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    _write_json(out, result)
    print(json.dumps({k: result[k] for k in ("device", "train_rows", "input_dim", "measured",
                                              "projection_upper_bound_minutes")}, indent=2))
    print(f"saved {out}")
    return result


REQUIRED = {"data": ("label_map", "nonnegative_cols"),
            "ae": ("hidden", "latent", "activation", "latent_activation", "output_activation", "lr",
                   "batch_size", "max_epochs", "patience", "min_delta"),
            "augment": ("enabled", "sigma_scale", "keep_quantile"),
            "xgb": ("n_estimators", "learning_rate", "max_depth", "early_stopping_rounds"),
            "run": ("model_seed", "device", "threshold")}


def load_experiment(path) -> dict:
    cfg = load_config(path)
    missing = [f"{sec}.{k}" for sec, keys in REQUIRED.items() for k in keys if k not in cfg.get(sec, {})]
    if missing:
        raise ValueError(f"experiment config missing {missing}")
    outside = xgbm.check_within_paper_ranges(cfg["xgb"])
    if outside:
        raise ValueError(f"XGBoost settings outside the paper's Table 5 ranges: {outside}")
    return cfg


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--device", choices=("auto", "cpu", "cuda"), help="overrides run.device")
    parser.add_argument("--storage", type=Path, help="persistent output root (default: $CNET_STORAGE or results/)")
    parser.add_argument("--benchmark", action="store_true", help="time a few steps and project the full run; no training")
    parser.add_argument("--allow-code-change", action="store_true", help="resume although the Git commit changed (recorded)")
    args = parser.parse_args(argv)
    cfg = load_experiment(args.config)
    device = resolve_device(args.device or cfg["run"]["device"])
    storage = args.storage or Path(os.environ.get("CNET_STORAGE", ROOT / cfg["paths"]["results"]))
    if args.benchmark:
        benchmark(cfg, device, storage)
    else:
        run(cfg, device, storage, allow_code_change=args.allow_code_change)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
