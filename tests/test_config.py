import json

import pytest
import yaml

from src.config import ROOT, check_no_leaky_outputs, load_config, make_preprocessor, write_run_record

EXPERIMENT = {
    "name": "toy", "dataset": "unsw_nb15", "files": {"train": "a.csv"}, "label": "label",
    "label_cols": ["label", "attack_cat"], "identifier_cols": ["id"], "categorical_cols": ["proto"],
    "split": {"strategy": "predefined"},
}


def _write(tmp_path, data):
    path = tmp_path / "exp.yaml"
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    return path


def test_base_config_is_valid_and_drives_the_preprocessor(tmp_path):
    cfg = load_config(_write(tmp_path, {"experiment": EXPERIMENT, "preprocessing": {"clip_to_train_range": True}}))
    assert cfg["seed"] == 42 and cfg["preprocessing"]["impute"] == "median"  # from base.yaml
    pre = make_preprocessor(cfg)
    assert set(pre.drop_cols) == {"id", "label", "attack_cat"}
    assert pre.categorical_cols == ("proto",) and pre.clip_to_train_range is True  # override applied


def test_smoke_experiment_file_is_valid():
    cfg = load_config(ROOT / "configs" / "experiments" / "smoke_unsw_official.yaml")
    assert cfg["experiment"]["split"]["strategy"] == "predefined"


@pytest.mark.parametrize("override,match", [
    ({"preprocessing": {"impute": "mean"}}, "not implemented"),
    ({"preprocessing": {"winsorize": True}}, "unknown preprocessing"),
    ({"experiment": {**EXPERIMENT, "dataset": "kaggle_copy"}}, "not in configs/datasets.yaml"),
    ({"experiment": {**EXPERIMENT, "label": "Label"}}, "label_cols"),
    ({"experiment": {**EXPERIMENT, "categorical_cols": ["attack_cat"]}}, "both features and label"),
    ({"experiment": {**EXPERIMENT, "split": {"strategy": "random_rows"}}}, "split.strategy"),
])
def test_unimplemented_or_inconsistent_settings_are_rejected(tmp_path, override, match):
    data = {"experiment": EXPERIMENT, **override} if "experiment" not in override else override
    with pytest.raises(ValueError, match=match):
        load_config(_write(tmp_path, data))


def test_leaky_outputs_are_caught(tmp_path):
    cfg = load_config(_write(tmp_path, {"experiment": EXPERIMENT}))
    check_no_leaky_outputs(["dur", "proto=tcp"], cfg)
    for leaked in (["dur", "id"], ["attack_cat=DoS"], ["label"]):
        with pytest.raises(AssertionError):
            check_no_leaky_outputs(leaked, cfg)


def test_run_record_contains_effective_config(tmp_path):
    cfg = load_config(_write(tmp_path, {"experiment": EXPERIMENT}))
    path = write_run_record(cfg, tmp_path / "run", extra={"split_fingerprint": "abc"})
    record = json.loads(path.read_text(encoding="utf-8"))
    assert record["config"]["experiment"]["name"] == "toy" and record["split_fingerprint"] == "abc"
