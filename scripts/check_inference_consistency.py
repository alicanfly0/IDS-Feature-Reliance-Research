"""Milestone 3B-0.1: bounded inference-consistency check on the ALREADY-INSPECTED baseline test set.

    .\\run.cmd scripts/check_inference_consistency.py            # print
    .\\run.cmd scripts/check_inference_consistency.py --write    # results/protocol/milestone3b/inference_consistency_v1.json

Loads the saved baseline (ae_xgb_d008_trackB-seed0-cpu-565a8b9e); nothing is retrained and no new
population is scored. Compares the saved test predictions with predictions reconstructed by
(a) the runner's own path (train-only preprocessing -> float32 -> ae.encode, batch 8192 -> XGBoost),
(b) CompositeModel float32 at several batch sizes, (c) a shuffled row order, (d) float64.
"""
import gzip
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import torch

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))
from src.audit.composite import CompositeModel  # noqa: E402
from src.config import load_config  # noqa: E402
from src.data import ddos  # noqa: E402
from src.models import autoencoder as ae  # noqa: E402
from src.models import xgb as xgbm  # noqa: E402

RUN = root / "results/runs/ae_xgb_d008_trackB-seed0-cpu-565a8b9e"
OUT = root / "results/protocol/milestone3b/inference_consistency_v1.json"
THR = 0.5


def compare(name, prob, margin, saved_prob, ref_margin):
    pred, saved_pred = prob >= THR, saved_prob >= THR
    return {"method": name, "max_abs_prob_diff_vs_saved": float(np.max(np.abs(prob - saved_prob))),
            "bitwise_equal_prob_vs_saved": bool(np.array_equal(prob.astype(np.float32), saved_prob.astype(np.float32))),
            "max_abs_margin_diff_vs_runner": float(np.max(np.abs(margin - ref_margin))),
            "rows_margin_diff_gt_1e-3": int((np.abs(margin - ref_margin) > 1e-3).sum()),
            "threshold_crossings_vs_saved": int((pred != saved_pred).sum())}


def main():
    torch.set_num_threads(torch.get_num_threads())
    cfg = load_config(root / "configs/experiments/ae_xgb_d008_trackB.yaml")
    prep = ddos.prepare(ddos.load(ddos.verified_csv(root)[0]), cfg["data"]["label_map"])
    with gzip.open(RUN / "predictions_test.csv.gz", "rt", encoding="utf-8") as f:
        saved = pd.read_csv(f)
    test = prep.frame.loc[saved["source_row"].to_numpy()]                 # saved order = runner order
    assert (prep.y[np.searchsorted(prep.frame.index.to_numpy(), saved["source_row"].to_numpy())] == saved["y_true"]).all()
    raw_cols = [c for c in prep.feature_cols]
    raw = test[raw_cols].to_numpy(np.float64)
    saved_prob = saved["prob_ddos"].to_numpy(np.float64)

    # (a) the runner's own inference path, rebuilt from saved artifacts
    cm = CompositeModel(RUN, raw_cols, precision="float32")
    x32 = cm.transform(raw)
    model = ae.build(x32.shape[1], json.loads((RUN / "effective_config.json").read_text())["ae"])
    model.load_state_dict(torch.load(RUN / "checkpoints" / "ae_best.pt", map_location="cpu", weights_only=True))
    z = ae.encode(model, x32, "cpu")                                         # default batch 8192, as in the runner
    clf = xgbm.load(RUN / "xgb_model.json")
    ref_margin = clf.predict(z, output_margin=True).astype(np.float64)
    ref_prob = xgbm.predict_positive(clf, z).astype(np.float64)
    results = [compare("runner path: ae.encode batch 8192 (saved row order)", ref_prob, ref_margin, saved_prob, ref_margin)]

    # (b) CompositeModel float32 at several batch sizes; (c) shuffled order; (d) float64
    for batch in (8192, 65536, 1024):
        m = CompositeModel(RUN, raw_cols, batch=batch, precision="float32")
        mg = m.margin(raw)
        results.append(compare(f"CompositeModel float32 batch {batch}", 1 / (1 + np.exp(-mg)), mg, saved_prob, ref_margin))
    perm = np.random.RandomState(0).permutation(len(raw))
    inv = np.argsort(perm)
    m = CompositeModel(RUN, raw_cols, batch=8192, precision="float32")
    mg = m.margin(raw[perm])[inv]
    results.append(compare("CompositeModel float32 batch 8192, shuffled order", 1 / (1 + np.exp(-mg)), mg, saved_prob, ref_margin))
    m64 = CompositeModel(RUN, raw_cols, precision="float64")
    mg = m64.margin(raw)
    results.append(compare("CompositeModel float64", 1 / (1 + np.exp(-mg)), mg, saved_prob, ref_margin))

    near = int((np.abs(ref_margin) < 0.01).sum())
    out = {"population": "baseline test partition (33,877 rows; already inspected in Milestones 1A-2A)",
           "run": RUN.name, "threshold": THR, "n_rows": int(len(raw)),
           "rows_with_|margin|<0.01": near, "torch_threads": torch.get_num_threads(), "device": "cpu",
           "results": results}
    print(json.dumps(out, indent=1))
    if "--write" in sys.argv[1:]:
        OUT.parent.mkdir(parents=True, exist_ok=True)
        with OUT.open("x", encoding="utf-8") as f:
            json.dump(out, f, indent=1)
            f.write("\n")
        print("wrote", OUT.relative_to(root))


if __name__ == "__main__":
    main()
