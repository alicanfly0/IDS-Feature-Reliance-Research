"""Deterministic aggregation of completed Milestone 3B runs on the family-common test rows.

    python -m src.evaluation.aggregate_3b --storage DIR [--out results/milestone3b/aggregate.json]

Refuses to aggregate if any completed run was trained from a config other than its committed
matrix entry, or if the runs' test rows differ in any way (order, set, labels).
"""
from __future__ import annotations

import argparse
import gzip
import json
from pathlib import Path

import numpy as np
import pandas as pd

from src.config import ROOT
from src.evaluation.stats_3b import removal_effect
from src.experiments.compare_ablation import mcnemar_exact
from src.experiments.population import rows_sha256

EPS = 1e-15


def endpoint_metrics(y, prob, threshold=0.5) -> dict:
    y, prob = np.asarray(y, int), np.asarray(prob, float)
    pred = (prob >= threshold).astype(int)
    tp, tn = int(((pred == 1) & (y == 1)).sum()), int(((pred == 0) & (y == 0)).sum())
    fp, fn = int(((pred == 1) & (y == 0)).sum()), int(((pred == 0) & (y == 1)).sum())
    denom = np.sqrt(float(tp + fp) * (tp + fn) * (tn + fp) * (tn + fn))
    p = np.clip(prob, EPS, 1 - EPS)
    return {"n": int(len(y)), "errors": fp + fn, "error_rate": (fp + fn) / len(y), "fp": fp, "fn": fn,
            "mcc": float((tp * tn - fp * fn) / denom) if denom else 0.0,
            "log_loss": float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))}


def find_run(storage: Path, entry: dict) -> Path | None:
    hits = sorted((storage / "runs").glob(f"{entry['experiment_name']}-seed{entry['model_seed']}-*"))
    hits = [h for h in hits if (h / "DONE").is_file()]
    if len(hits) > 1:
        raise RuntimeError(f"{entry['id']}: several completed runs {[h.name for h in hits]}")
    return hits[0] if hits else None


def _check_config(run_dir: Path, entry: dict, root: Path):
    from src.experiments import ae_xgb
    expected = ae_xgb.load_experiment(root / entry["config"])
    used = json.loads((run_dir / "effective_config.json").read_text(encoding="utf-8"))
    if ae_xgb.config_hash(expected) != ae_xgb.config_hash(used):
        raise RuntimeError(f"{entry['id']}: run {run_dir.name} was not trained from its committed config")


def _test_predictions(run_dir: Path) -> pd.DataFrame:
    with gzip.open(run_dir / "predictions_test.csv.gz", "rt", encoding="utf-8") as f:
        return pd.read_csv(f)


METADATA_FIELDS = ("utc_time", "os", "cpu", "cpu_count", "ram_bytes", "machine")


def environment_record(run_dir: Path) -> dict:
    """Training-relevant provenance of one run, verified against its own records (fails closed)."""
    from src import env
    run_dir = Path(run_dir)
    ident_path = run_dir / "identity.json"
    envs = sorted(run_dir.glob("environment-*.json"))
    if not ident_path.is_file() or not envs:
        raise RuntimeError(f"{run_dir.name}: missing identity or environment records")
    ident = json.loads(ident_path.read_text(encoding="utf-8"))
    for key in ("environment_fingerprint", "environment", "git_commit", "dataset_sha256", "device"):
        if key not in ident:
            raise RuntimeError(f"{run_dir.name}: identity lacks '{key}' (missing provenance)")
    if ident["environment_fingerprint"] != _fp(ident["environment"]):
        raise RuntimeError(f"{run_dir.name}: identity environment does not match its fingerprint (tampered)")
    if ident.get("resumed_from_commit") not in (None, ident["git_commit"]):
        raise RuntimeError(f"{run_dir.name}: resumed under a different code commit")
    meta = {}
    for f in envs:
        snap = json.loads(f.read_text(encoding="utf-8"))
        if env.fingerprint(snap) != ident["environment_fingerprint"]:
            raise RuntimeError(f"{run_dir.name}: {f.name} differs from the run's training environment "
                               f"({env.result_relevant(snap)} vs {ident['environment']})")
        if (snap.get("git") or {}).get("commit") != ident["git_commit"]:
            raise RuntimeError(f"{run_dir.name}: {f.name} commit differs from identity")
        if (snap.get("dataset") or {}).get("sha256") != ident["dataset_sha256"]:
            raise RuntimeError(f"{run_dir.name}: {f.name} dataset hashes differ from identity")
        meta[f.name] = {k: snap.get(k) for k in METADATA_FIELDS}
        meta[f.name]["nvidia_smi"] = (snap.get("gpu") or {}).get("nvidia_smi")
    if ident["environment"]["device"] != ident["device"]:
        raise RuntimeError(f"{run_dir.name}: trained on {ident['device']} but the environment reports "
                           f"{ident['environment']['device']}")
    return {"fingerprint": ident["environment_fingerprint"], "environment": ident["environment"],
            "git_commit": ident["git_commit"], "dataset_sha256": ident["dataset_sha256"],
            "device": ident["device"], "metadata": meta}


def _fp(relevant: dict) -> str:
    import hashlib
    return hashlib.sha256(json.dumps(relevant, sort_keys=True).encode()).hexdigest()


def check_compatible(records: dict[str, dict]) -> dict:
    """All runs must share one training environment, code commit, dataset and device."""
    if not records:
        return {"n_runs": 0}
    problems = []
    for key in ("fingerprint", "git_commit", "dataset_sha256", "device"):
        groups: dict[str, list[str]] = {}
        for rid, r in sorted(records.items()):
            groups.setdefault(json.dumps(r[key], sort_keys=True), []).append(rid)
        if len(groups) <= 1:
            continue
        if key == "fingerprint":                     # show the differing environments, not just hashes
            shown = [f"{records[ids[0]]['environment']} ({len(ids)} runs, e.g. {ids[0]})" for ids in groups.values()]
            problems.append("training environment differs: " + " vs ".join(shown))
        else:
            problems.append(f"{key} differs: " + " vs ".join(f"{v} ({len(ids)} runs)" for v, ids in groups.items()))
    if problems:
        raise RuntimeError("incompatible runs, refusing to compare: " + " | ".join(problems))
    first = next(iter(sorted(records.items())))[1]
    drivers = sorted({json.dumps(m.get("nvidia_smi")) for r in records.values() for m in r["metadata"].values()})
    return {"n_runs": len(records), "environment": first["environment"], "fingerprint": first["fingerprint"],
            "git_commit": first["git_commit"], "device": first["device"],
            "metadata_variation": {"nvidia_smi_values": [json.loads(d) for d in drivers],
                                   "note": "metadata (timestamps, RAM, CPU, driver build) is reported, not required to match"}}


def aggregate(storage: Path, matrix: dict, population: dict, root: Path = ROOT, check_config: bool = True,
              check_environment: bool = True) -> dict:
    pop = population["family_common_model_visible"]
    runs, reference = {}, None
    for e in matrix["entries"]:
        run_dir = find_run(storage, e)
        if run_dir is None:
            continue
        if check_config:
            _check_config(run_dir, e, root)
        pred = _test_predictions(run_dir)
        if reference is None:
            reference = pred[["source_row", "y_true"]].copy()
            if rows_sha256(reference["source_row"]) != pop["test_kept_source_rows_sha256"]:
                raise RuntimeError(f"{e['id']}: test rows are not the family-common population")
        elif not pred[["source_row", "y_true"]].equals(reference):
            raise RuntimeError(f"{e['id']}: test rows or labels differ from the other runs")
        runs[e["id"]] = {"entry": e, "run": run_dir.name, "pred": pred, "dir": run_dir}
    # Milestone 3B-1: refuse to compare runs from different training environments, BEFORE any metric.
    environment = (check_compatible({rid: environment_record(r["dir"]) for rid, r in runs.items()})
                   if check_environment else {"checked": False})
    out = {"population_test_sha256": pop["test_kept_source_rows_sha256"], "n_completed": len(runs),
           "n_matrix": matrix["n_entries"], "environment": environment, "runs": {}, "paired_vs_full": {}}
    for rid in sorted(runs):
        r = runs[rid]
        out["runs"][rid] = {"run": r["run"], **endpoint_metrics(r["pred"]["y_true"], r["pred"]["prob_ddos"])}
    for rid in sorted(runs):
        e = runs[rid]["entry"]
        full_id = f"r1_full_s{e['model_seed']}"
        if e["kind"] == "full" or full_id not in runs:
            continue
        a, f = runs[rid]["pred"], runs[full_id]["pred"]
        wrong_a, wrong_f = a["y_pred"] != a["y_true"], f["y_pred"] != f["y_true"]
        b, c = int((wrong_a & ~wrong_f).sum()), int((~wrong_a & wrong_f).sum())
        out["paired_vs_full"][rid] = {
            "full": full_id, "only_ablated_wrong": b, "only_full_wrong": c, "mcnemar_exact_p": mcnemar_exact(b, c),
            **{f"effect_{m}": removal_effect(out["runs"][rid][m], out["runs"][full_id][m])
               for m in ("error_rate", "log_loss")}}
    return out


def main(argv=None) -> int:
    from src.experiments.matrix_3b import load_matrix
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--storage", type=Path, required=True)
    p.add_argument("--out", type=Path)
    a = p.parse_args(argv)
    matrix = load_matrix()
    population = json.loads((ROOT / matrix["population_file"]).read_text(encoding="utf-8"))
    result = aggregate(a.storage, matrix, population)
    text = json.dumps(result, indent=1, sort_keys=True)
    if a.out:
        a.out.parent.mkdir(parents=True, exist_ok=True)
        a.out.write_text(text + "\n", encoding="utf-8")
    print(f"{result['n_completed']}/{result['n_matrix']} runs aggregated on identical test rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
