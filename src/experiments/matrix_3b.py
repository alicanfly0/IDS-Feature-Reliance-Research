"""Milestone 3B experiment matrix (protocol r1, PROPOSED) and run-config generation.

    python -m src.experiments.matrix_3b generate                  # write configs + matrix.json (idempotent)
    python -m src.experiments.matrix_3b plan [--storage DIR]      # dry run: batches, status, estimates
    python -m src.experiments.matrix_3b run --batch K --storage DIR --device cuda --confirm-approved
                                                                  # trains ONE batch; the flag is an operator
                                                                  # confirmation only, NOT proof of approval

Mandatory design D (docs/MILESTONE_3A_REVIEW_RESOLUTION.md §3): full model and the five primary
groups at model seeds 0-9, and random control draw j trained with seed j (j = 0..9): 110 fits.
Every config uses the validated family-common population (run.eval_population), so all models
see identical training, validation and test rows. Nothing here changes a frozen protocol file.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

from src.config import ROOT
from src.experiments.population import lf_sha256

GROUPS_FILE = "configs/protocol/ablation_groups_3a_r1.yaml"
POPULATION_FILE = "results/protocol/milestone3a/eval_population_3a_r1.json"
BASE_CONFIG = "configs/experiments/ae_xgb_d008_trackB.yaml"
BASELINE_PREPROCESSOR = "results/baselines/ae_xgb_d008_trackB-seed0-cpu-565a8b9e/preprocessor.json"
OUT_DIR = "configs/experiments/generated/r1"
PRIMARY = {"A_flag_defects": "A", "B_appendix_closed": "B", "C_duplication": "C",
           "D_metadata_hypothesis": "D", "U_documented_union": "U"}
SEEDS = range(10)

# Designs. r1 = the main AE-XGBoost experiment (frozen, 110 fits). r4a = R4a-ii on the Engelen corrected
# window (D-024, approved 2026-11-11): full + groups A, B, U at seeds 0-9 and 10 seed-paired controls each.
DESIGNS = {
    "r1": {"groups_file": GROUPS_FILE, "population_file": POPULATION_FILE, "base_config": BASE_CONFIG,
           "inputs_from": ("preprocessor", BASELINE_PREPROCESSOR), "out_dir": OUT_DIR, "primary": PRIMARY,
           "n_fits": 110, "protocol": "Milestone 3B, design D (r1), PROPOSED; generated configs only"},
    "r4a": {"groups_file": "configs/protocol/r4a_groups_v1.yaml",
            "population_file": "results/protocol/r4a/eval_population_r4a_v1.json",
            "base_config": "configs/experiments/ae_xgb_r4a_trackB.yaml",
            "inputs_from": ("groups", "model_inputs"), "out_dir": "configs/experiments/generated/r4a",
            "primary": {"A_flag_defects": "A", "B_appendix_closed": "B", "U_documented_union": "U"},
            "n_fits": 70, "protocol": "R4a-ii (D-024, approved), Engelen corrected window; generated configs only"},
}
BATCH = 10
MIN_PER_FIT, MAX_PER_FIT = 1.45, 2.36       # measured laptop-CPU minutes (baseline, D-018 ablation)
MB_PER_RUN = 30


def build_matrix(root: Path = ROOT, design: str = "r1") -> dict:
    d = DESIGNS[design]
    primary = d["primary"] if design != "r1" else PRIMARY        # r1 keeps the module-level mapping (tests patch it)
    groups = yaml.safe_load((root / d["groups_file"]).read_text(encoding="utf-8"))
    population = json.loads((root / d["population_file"]).read_text(encoding="utf-8"))
    groups_sha = lf_sha256(root / d["groups_file"])
    if population["frozen_groups_sha256_lf"] != groups_sha:
        raise RuntimeError("population record was made for a different groups file")
    kind_from, ref = d["inputs_from"]
    inputs = set(json.loads((root / ref).read_text(encoding="utf-8"))["numeric_cols"] if kind_from == "preprocessor"
                 else groups[ref])
    unknown = set(primary) - set(groups["groups"])
    if unknown:
        raise KeyError(f"primary groups missing from {d['groups_file']}: {sorted(unknown)}")
    entries = []

    def add(kind, group, draw, seed, drop):
        bad = set(drop) - inputs
        if bad:
            raise ValueError(f"{kind}/{group}: columns not in the {len(inputs)} model inputs: {sorted(bad)}")
        if len(set(drop)) != len(drop):
            raise ValueError(f"{kind}/{group}: duplicate columns")
        tag = "full" if kind == "full" else primary[group] + ("" if kind == "group" else f"ctl{draw}")
        entries.append({"id": f"{design}_{tag}_s{seed}", "tier": "mandatory", "kind": kind, "group": group,
                        "control_draw": draw, "model_seed": seed, "drop": sorted(drop),
                        "experiment_name": f"ae3b_{design}_{tag}"})

    for s in SEEDS:
        add("full", None, None, s, [])
    for name in primary:
        for s in SEEDS:
            add("group", name, None, s, groups["groups"][name]["columns"])
        draws = groups["controls"][name]["random"]
        if len(draws) != len(SEEDS):
            raise ValueError(f"{name}: expected {len(SEEDS)} random draws, found {len(draws)}")
        for j in SEEDS:                                   # draw j <-> seed j
            if len(draws[j]) != groups["groups"][name]["size"]:
                raise ValueError(f"{name} draw {j}: size mismatch")
            add("control", name, j, j, draws[j])
    ids = [e["id"] for e in entries]
    assert len(ids) == len(set(ids)) == d["n_fits"], len(ids)
    for i, e in enumerate(entries):
        e["batch"] = i // BATCH
    out = {"protocol": d["protocol"],
            "groups_file": d["groups_file"], "groups_sha256_lf": groups_sha,
            "population_file": d["population_file"], "population_sha256_lf": lf_sha256(root / d["population_file"]),
            "base_config": d["base_config"], "split_fingerprint": population["split_fingerprint"],
            "n_entries": len(entries), "entries": entries}
    if design != "r1":
        out["design"] = design
    return out


def config_for(entry: dict, matrix: dict) -> dict:
    return {"experiment": {"name": entry["experiment_name"], "extra_drop_cols": entry["drop"]},
            "run": {"model_seed": entry["model_seed"], "exclude_eval_twins": False,
                    "eval_population": {"record": matrix["population_file"], "sha256": matrix["population_sha256_lf"]}}}


def _header(entry, matrix) -> str:
    over = "".join(f"#   {line}\n" for line in yaml.safe_dump(config_for(entry, matrix), sort_keys=False).splitlines())
    return (f"# GENERATED by src/experiments/matrix_3b.py from {matrix['groups_file']} (do not edit).\n"
            f"# Entry {entry['id']} ({entry['kind']}"
            f"{', ' + entry['group'] if entry['group'] else ''}"
            f"{', control draw ' + str(entry['control_draw']) if entry['control_draw'] is not None else ''}): "
            f"{matrix['base_config']} with only these keys changed:\n{over}")


def materialize(entry: dict, matrix: dict, root: Path = ROOT) -> Path:
    """The full experiment YAML = base config overlaid with the entry (no other change)."""
    base = yaml.safe_load((root / matrix["base_config"]).read_text(encoding="utf-8"))
    over = config_for(entry, matrix)
    base["experiment"].update(over["experiment"])
    base["run"].update(over["run"])
    return base


def generate(root: Path = ROOT, design: str = "r1") -> Path:
    matrix = build_matrix(root, design)
    out_dir = OUT_DIR if design == "r1" else DESIGNS[design]["out_dir"]
    out = root / out_dir
    out.mkdir(parents=True, exist_ok=True)
    for e in matrix["entries"]:
        path = out / f"{e['id']}.yaml"
        text = _header(e, matrix) + yaml.safe_dump(materialize(e, matrix, root), sort_keys=False)
        if path.exists() and path.read_text(encoding="utf-8").replace("\r\n", "\n") != text:
            raise FileExistsError(f"{path.name} exists with different content; refusing to overwrite")
        if not path.exists():
            path.write_text(text, encoding="utf-8")
        e["config"] = f"{out_dir}/{path.name}"
    mpath = out / "matrix.json"
    text = json.dumps(matrix, indent=1) + "\n"
    if mpath.exists() and mpath.read_text(encoding="utf-8").replace("\r\n", "\n") != text:
        raise FileExistsError("matrix.json exists with different content; refusing to overwrite")
    if not mpath.exists():
        mpath.write_text(text, encoding="utf-8")
    return mpath


def load_matrix(root: Path = ROOT, design: str = "r1") -> dict:
    """Load the committed matrix and refuse it if the protocol inputs changed since generation."""
    out_dir = OUT_DIR if design == "r1" else DESIGNS[design]["out_dir"]
    matrix = json.loads((root / out_dir / "matrix.json").read_text(encoding="utf-8"))
    fresh = build_matrix(root, design)
    if fresh["groups_sha256_lf"] != matrix["groups_sha256_lf"] or fresh["population_sha256_lf"] != matrix["population_sha256_lf"]:
        raise RuntimeError("groups or population file changed since the matrix was generated")
    if [ {k: v for k, v in e.items() if k != "config"} for e in matrix["entries"]] != fresh["entries"]:
        raise RuntimeError("matrix entries differ from the protocol file")
    return matrix


def status(matrix: dict, storage: Path | None) -> dict:
    done = set()
    if storage and (storage / "runs").is_dir():
        for d in (storage / "runs").iterdir():
            if (d / "DONE").is_file():
                done.add(d.name.split("-seed")[0] + "|" + d.name.split("-seed")[1].split("-")[0])
    return {e["id"]: f"{e['experiment_name']}|{e['model_seed']}" in done for e in matrix["entries"]}


def plan(matrix: dict, storage: Path | None) -> str:
    st = status(matrix, storage)
    n, batches = matrix["n_entries"], sorted({e["batch"] for e in matrix["entries"]})
    title = ("Milestone 3B dry run (design D, r1 PROPOSED)" if matrix.get("design", "r1") == "r1"
             else f"{matrix['design']} dry run ({matrix['protocol']})")
    lines = [f"{title}: {n} fits in {len(batches)} batches of {BATCH}",
             f"split {matrix['split_fingerprint'][:16]}..., population {matrix['population_sha256_lf'][:12]}..., "
             f"groups {matrix['groups_sha256_lf'][:12]}...",
             f"laptop-CPU estimate {n * MIN_PER_FIT / 60:.1f}-{n * MAX_PER_FIT / 60:.1f} h (measured 1.45-2.36 min/fit); "
             f"Colab speed NOT measured; storage ~{n * MB_PER_RUN / 1024:.1f} GB at ~{MB_PER_RUN} MB/run"]
    for b in batches:
        es = [e for e in matrix["entries"] if e["batch"] == b]
        done = sum(st[e["id"]] for e in es)
        lines.append(f"  batch {b:2d}: {done}/{len(es)} done  " + ", ".join(e["id"] for e in es))
    return "\n".join(lines)


def run_batch(matrix: dict, batch: int, storage: Path, device: str, root: Path = ROOT) -> list[Path]:
    from src.experiments import ae_xgb   # imports torch only when training is actually requested
    out = []
    for e in [e for e in matrix["entries"] if e["batch"] == batch]:
        cfg = ae_xgb.load_experiment(root / e["config"])
        out.append(ae_xgb.run(cfg, ae_xgb.resolve_device(device), storage))
    return out


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("command", choices=("generate", "plan", "run"))
    p.add_argument("--design", default="r1", choices=sorted(DESIGNS))
    p.add_argument("--storage", type=Path)
    p.add_argument("--batch", type=int)
    p.add_argument("--device", default="auto", choices=("auto", "cpu", "cuda"))
    p.add_argument("--confirm-approved", action="store_true",
                   help="required for 'run': the OPERATOR's explicit confirmation that D-007/D-012/D-020 r1/D-021/D-023 "
                        "approvals are recorded. It is not checked against the decision log and is not proof of approval.")
    a = p.parse_args(argv)
    if a.command == "generate":
        print(f"wrote {generate(design=a.design).relative_to(ROOT)}")
        return 0
    matrix = load_matrix(design=a.design)
    if a.command == "plan":
        print(plan(matrix, a.storage))
        return 0
    if not a.confirm_approved:
        print("refusing to train: pass --confirm-approved only after the approvals are recorded in docs/decision_log.md",
              file=sys.stderr)
        return 2
    if a.batch is None or a.storage is None:
        p.error("run needs --batch and --storage")
    run_batch(matrix, a.batch, a.storage, a.device)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
