"""Effective run configuration: configs/base.yaml overlaid with one experiment file.

    cfg = load_config("configs/experiments/smoke_unsw_official.yaml")
    pre = make_preprocessor(cfg)               # drops cfg label + identifier columns
    check_no_leaky_outputs(pre.output_columns, cfg)
    write_run_record(cfg, out_dir, extra={...})

Settings the code does not implement are rejected, so a config can never claim
a policy that is not actually applied.
"""
from __future__ import annotations

import json
from pathlib import Path

import yaml

from src.data.manifest import load_manifest
from src.data.preprocess import TrainOnlyPreprocessor

ROOT = Path(__file__).resolve().parents[1]
BASE_PATH = ROOT / "configs" / "base.yaml"

SUPPORTED_PREPROCESSING = {
    "inf_as_missing": {True},
    "impute": {"median"},
    "scale": {"minmax"},
    "one_hot_unknown": {"ignore"},
    "drop_constant_on_train": {True, False},
    "clip_to_train_range": {True, False},
}
SPLIT_STRATEGIES = {"stratified_random", "group", "temporal", "predefined"}
EXPERIMENT_KEYS = ("name", "dataset", "files", "label", "label_cols", "identifier_cols", "categorical_cols", "split")


def _merge(base: dict, override: dict) -> dict:
    out = dict(base)
    for key, value in override.items():
        out[key] = _merge(out[key], value) if isinstance(value, dict) and isinstance(out.get(key), dict) else value
    return out


def load_config(experiment_path: str | Path | None = None, base_path: str | Path = BASE_PATH) -> dict:
    with open(base_path, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    if experiment_path is not None:
        with open(experiment_path, encoding="utf-8") as f:
            cfg = _merge(cfg, yaml.safe_load(f))
        cfg["config_files"] = [str(Path(base_path).name), str(Path(experiment_path).name)]
    validate_config(cfg)
    return cfg


def validate_config(cfg: dict) -> None:
    for key, value in cfg.get("preprocessing", {}).items():
        allowed = SUPPORTED_PREPROCESSING.get(key)
        if allowed is None:
            raise ValueError(f"unknown preprocessing setting '{key}'")
        if value not in allowed:
            raise ValueError(f"preprocessing.{key}={value!r} is not implemented (supported: {sorted(map(str, allowed))})")
    exp = cfg.get("experiment")
    if exp is None:
        return
    missing = [k for k in EXPERIMENT_KEYS if k not in exp]
    if missing:
        raise ValueError(f"experiment config is missing {missing}")
    if exp["dataset"] not in load_manifest()["datasets"]:
        raise ValueError(f"experiment dataset '{exp['dataset']}' is not in configs/datasets.yaml")
    if exp["split"].get("strategy") not in SPLIT_STRATEGIES:
        raise ValueError(f"split.strategy must be one of {sorted(SPLIT_STRATEGIES)}")
    if exp["label"] not in exp["label_cols"]:
        raise ValueError("experiment.label must be listed in experiment.label_cols")
    overlap = set(exp["categorical_cols"]) & (set(exp["label_cols"]) | set(exp["identifier_cols"]))
    if overlap:
        raise ValueError(f"columns cannot be both features and label/identifier: {sorted(overlap)}")


def excluded_columns(cfg: dict) -> list[str]:
    exp = cfg["experiment"]
    return list(dict.fromkeys([*exp["identifier_cols"], *exp["label_cols"], *exp.get("extra_drop_cols", [])]))


def make_preprocessor(cfg: dict) -> TrainOnlyPreprocessor:
    pre = cfg["preprocessing"]
    return TrainOnlyPreprocessor(
        drop_cols=tuple(excluded_columns(cfg)),
        categorical_cols=tuple(cfg["experiment"]["categorical_cols"]),
        drop_constant=pre["drop_constant_on_train"],
        clip_to_train_range=pre["clip_to_train_range"],
    )


def check_no_leaky_outputs(output_columns: list[str], cfg: dict) -> None:
    """Raise if any label or identifier column, or a one-hot of one, reaches the model input."""
    banned = set(cfg["experiment"]["label_cols"]) | set(cfg["experiment"]["identifier_cols"])
    leaked = [c for c in output_columns if c in banned or c.split("=", 1)[0] in banned]
    if leaked:
        raise AssertionError(f"label/identifier columns in model input: {leaked}")


def write_run_record(cfg: dict, out_dir: str | Path, extra: dict | None = None) -> Path:
    """Save the effective configuration (plus run facts such as split fingerprint) as JSON."""
    out = Path(out_dir) / "run_record.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"config": cfg, **(extra or {})}, indent=2, default=str), encoding="utf-8")
    return out
