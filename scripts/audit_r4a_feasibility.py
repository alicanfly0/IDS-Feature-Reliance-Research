"""Read-only R4a feasibility audit: original CICIDS2017 Friday DDoS file vs Engelen WTMC2021 Friday.

    .\\run.cmd scripts/audit_r4a_feasibility.py            # print
    .\\run.cmd scripts/audit_r4a_feasibility.py --write    # also write results/protocol/r4a/r4a_feasibility_v1.json

No model is loaded or evaluated. Measures: column mapping coverage, timestamp/clock alignment,
labels inside the original recording window, per-feature distribution shifts (DDoS and BENIGN
separately), and rows of the corrected data identical to an original TRAINING vector in the
model-visible (float32, train-only preprocessing) view of the full model and the five primary groups.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))
from src.config import load_config  # noqa: E402
from src.data import ddos  # noqa: E402
from src.data.load import read_flow_csv  # noqa: E402
from src.evaluation.score_benign import training_twin_mask  # noqa: E402

MAP_FILE = root / "configs/protocol/r4a_column_map_v1.yaml"
OUT = root / "results/protocol/r4a/r4a_feasibility_v1.json"
ENGELEN = root / "data/raw/cicids2017_engelen_wtmc2021/extracted/Friday-WorkingHours.csv"
TL = root / "data/raw/cicids2017_original/extracted/TrafficLabelling/Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv"


def ks(a, b):
    a, b = np.sort(a[np.isfinite(a)]), np.sort(b[np.isfinite(b)])
    if not len(a) or not len(b):
        return None
    grid = np.union1d(a, b)
    return float(np.max(np.abs(np.searchsorted(a, grid, "right") / len(a) - np.searchsorted(b, grid, "right") / len(b))))


def main():
    cmap = yaml.safe_load(MAP_FILE.read_text(encoding="utf-8"))
    mapping = cmap["mapping"]                                   # original name -> Engelen name
    cfg = load_config(root / "configs/experiments/ae_xgb_d008_trackB.yaml")
    prep = ddos.prepare(ddos.load(ddos.verified_csv(root)[0]), cfg["data"]["label_map"])
    orig = prep.frame
    eng, adjust = read_flow_csv(ENGELEN)
    out = {"engelen_file": str(ENGELEN.relative_to(root)).replace("\\", "/"), "engelen_rows": int(len(eng)),
           "engelen_encoding": adjust.get("encoding") if isinstance(adjust, dict) else None}

    # 1. mapping coverage
    missing_src = [o for o, e in mapping.items() if e not in eng.columns]
    unmapped_orig = [c for c in prep.feature_cols if c not in mapping]
    unused_eng = [c for c in eng.columns if c not in set(mapping.values()) | {"Label"}]
    out["mapping"] = {"n_mapped": len(mapping), "missing_in_engelen": missing_src, "original_unmapped": unmapped_orig,
                      "engelen_unused": unused_eng,
                      "renamed": {o: e for o, e in mapping.items() if o != e}}

    # 2. time alignment (original timestamps are minute resolution, 12-hour clock without AM/PM)
    tl, _ = read_flow_csv(TL)
    t_orig = pd.to_datetime(tl["Timestamp"], format="%d/%m/%Y %H:%M", errors="coerce")
    if t_orig.isna().any():
        t_orig = pd.to_datetime(tl["Timestamp"], dayfirst=True, errors="coerce")
    t_orig = t_orig + pd.to_timedelta((t_orig.dt.hour < 8) * 12, unit="h")      # afternoon file: 3:30 -> 15:30
    t_eng = pd.to_datetime(eng["Timestamp"], format="%m/%d/%Y %I:%M:%S %p", errors="coerce")
    lab_o = tl["Label"].astype(str).str.strip()
    lab_e = eng["Label"].astype(str).str.strip()
    # Clock offset estimated from the DDoS attack itself (labels only, no features): onset and end must agree.
    onset = t_eng[lab_e == "DDoS"].min().floor("min") - t_orig[lab_o == "DDoS"].min()
    end = t_eng[lab_e == "DDoS"].max().floor("min") - t_orig[lab_o == "DDoS"].max()
    if onset != end:
        raise RuntimeError(f"no consistent clock offset: onset {onset}, end {end}")
    t_eng_aligned = t_eng - onset
    window = (t_orig.min(), t_orig.max() + pd.Timedelta(minutes=1))
    in_win = (t_eng_aligned >= window[0]) & (t_eng_aligned < window[1])
    out["time"] = {"original_parse_failures": int(t_orig.isna().sum()), "engelen_parse_failures": int(t_eng.isna().sum()),
                   "clock_offset_engelen_minus_original": str(onset),
                   "offset_check": "DDoS onset and end minute differ by the same offset",
                   "original_window": [str(window[0]), str(window[1])],
                   "original_ddos": [str(t_orig[lab_o == "DDoS"].min()), str(t_orig[lab_o == "DDoS"].max())],
                   "engelen_ddos": [str(t_eng[lab_e == "DDoS"].min()), str(t_eng[lab_e == "DDoS"].max())],
                   "engelen_labels_in_original_window": lab_e[in_win].value_counts().to_dict(),
                   "engelen_labels_outside_window": lab_e[~in_win].value_counts().to_dict()}
    per_min_o = t_orig[lab_o == "DDoS"].dt.floor("min").value_counts().sort_index()
    per_min_e = t_eng_aligned[lab_e == "DDoS"].dt.floor("min").value_counts().sort_index()
    out["time"]["ddos_per_minute"] = {"original": {str(k.time()): int(v) for k, v in per_min_o.items()},
                                      "engelen": {str(k.time()): int(v) for k, v in per_min_e.items()}}

    print("TIME:", json.dumps({k: v for k, v in out["time"].items() if k != "ddos_per_minute"}, default=str))

    # 3. candidate R4a population: Engelen DDoS + BENIGN inside the original window, mapped to original names
    cand = eng.loc[in_win & lab_e.isin(["DDoS", "BENIGN"])]
    mapped = pd.DataFrame({o: pd.to_numeric(cand[e], errors="coerce") for o, e in mapping.items()}, index=cand.index)
    mapped["Label"] = lab_e[cand.index].to_numpy()
    nonfinite = ~np.isfinite(mapped.drop(columns="Label").to_numpy(float)).all(axis=1)
    neg_dur = (mapped["Flow Duration"] < 0).to_numpy()
    out["candidate"] = {"rows": int(len(mapped)), "labels": mapped["Label"].value_counts().to_dict(),
                        "d011_nonfinite_rows": int(nonfinite.sum()), "d011_negative_duration_rows": int(neg_dur.sum())}
    mapped = mapped.loc[~(nonfinite | neg_dur)]

    # 4. distribution shifts per feature and class (descriptive)
    shifts = {}
    for c in prep.feature_cols:
        row = {}
        for cls in ("DDoS", "BENIGN"):
            a = orig.loc[orig["Label"] == cls, c].to_numpy(float)
            b = mapped.loc[mapped["Label"] == cls, c].to_numpy(float)
            if not len(a) or not len(b):
                row[cls] = {"ks": None, "n_orig": int(len(a)), "n_engelen": int(len(b))}
                continue
            row[cls] = {"ks": ks(a, b), "orig_median": float(np.nanmedian(a)), "eng_median": float(np.nanmedian(b)),
                        "orig_max": float(np.nanmax(a)), "eng_max": float(np.nanmax(b))}
        shifts[c] = row
    out["shift"] = shifts
    out["destination_port_80_share_ddos"] = {
        "original": float((orig.loc[orig["Label"] == "DDoS", "Destination Port"] == 80).mean()),
        "engelen": float((mapped.loc[mapped["Label"] == "DDoS", "Destination Port"] == 80).mean())}

    # 5. corrected rows identical to an original TRAINING vector (model-visible view)
    g = yaml.safe_load((root / "configs/protocol/ablation_groups_3a_r1.yaml").read_text(encoding="utf-8"))
    views = {"full": [], **{k: g["groups"][k]["columns"] for k in
                            ("A_flag_defects", "B_appendix_closed", "C_duplication", "D_metadata_hypothesis", "U_documented_union")}}
    frame = mapped[prep.feature_cols].copy()
    frame["Label"] = mapped["Label"].to_numpy()
    mask, per_view = training_twin_mask(cfg, prep, views, frame)
    out["training_twins"] = {"views_checked": list(views), "per_view": per_view, "union_rows": int(mask.sum()),
                             "union_by_label": frame.loc[mask, "Label"].value_counts().to_dict(),
                             "note": "execution must recompute the union over all 63 r1 views"}
    out["candidate_after_rules_and_twins"] = frame.loc[~mask, "Label"].value_counts().to_dict()
    print(json.dumps({k: v for k, v in out.items() if k != "shift"}, indent=1, default=str))
    top = sorted(((r["DDoS"]["ks"] or 0, c) for c, r in shifts.items()), reverse=True)[:15]
    print("largest DDoS distribution shifts (KS):", [(c, round(k, 3)) for k, c in top])
    if "--write" in sys.argv[1:]:
        OUT.parent.mkdir(parents=True, exist_ok=True)
        with OUT.open("x", encoding="utf-8") as f:
            json.dump(out, f, indent=1, default=str)
            f.write("\n")
        print("wrote", OUT.relative_to(root))


if __name__ == "__main__":
    main()
