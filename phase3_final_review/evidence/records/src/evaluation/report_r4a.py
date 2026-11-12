"""R4a analysis (D-024). Reads committed records only.

Inputs (from the Colab run, docs/COLAB_R4A_RUN.md):
  results/r4a/aggregate_r4a.json   aggregate_3b --design r4a (70 fits, R4a-ii)
  results/r4a/r4a_i_scores.json    score_r4a_i (110 r1 models on the corrected test rows, R4a-i)
  results/milestone3b/stats_r1.json  (the original-data contrasts, for the observational comparison)

R4a-ii primary family: groups A, B, U x in-domain error rate (3 tests, Holm), same estimand,
exact sign-flip test, intervals and SESOI (0.001) as r1. Group C/D are not part of R4a (D-024).
Cross-dataset comparison (original vs corrected, per group): DESCRIPTIVE / OBSERVATIONAL only.
The groups differ in composition between the two datasets (proxy closure recomputed on each),
and the datasets differ in segmentation, label windows, populations and definitions, so a
difference of effects is not attributable to the extractor defects alone.
R4a-i: descriptive transfer of the original models to corrected rows (definitions differ for
>= 16 inputs); never read as artifact reliance.

  python -m src.evaluation.report_r4a
"""
from __future__ import annotations

import json

import numpy as np

from src.data.manifest import ROOT
from src.evaluation import stats_3b as S
from src.experiments.matrix_3b import load_matrix

DIR = ROOT / "results/r4a"
R1 = ROOT / "results/milestone3b/stats_r1.json"
SESOI = 0.001
LABEL = {"A_flag_defects": "A: TCP flag-count defects", "B_appendix_closed": "B: TCP appendix",
         "U_documented_union": "U: union"}


def load():
    matrix = load_matrix(design="r4a")
    agg = json.loads((DIR / "aggregate_r4a.json").read_text(encoding="utf-8"))
    n = len(matrix["entries"])
    if agg["n_completed"] != n or agg["n_matrix"] != n:
        raise RuntimeError(f"incomplete R4a aggregate: {agg['n_completed']}/{agg['n_matrix']} of {n}")
    sizes = {r["n"] for r in agg["runs"].values()}
    if len(sizes) != 1:
        raise RuntimeError(f"R4a runs scored on different populations: {sizes}")
    return matrix, agg


def welch(a, b, level: float = 0.95) -> dict:
    """Mean difference a - b with a Welch t interval. Descriptive only."""
    from scipy import stats
    a, b = np.asarray(a, float), np.asarray(b, float)
    va, vb = a.var(ddof=1) / len(a), b.var(ddof=1) / len(b)
    se = np.sqrt(va + vb)
    diff = float(a.mean() - b.mean())
    if se == 0:
        return {"difference": diff, "interval": [diff, diff], "df": None, "level": level}
    df = (va + vb) ** 2 / (va ** 2 / (len(a) - 1) + vb ** 2 / (len(b) - 1))
    q = stats.t.ppf(0.5 + level / 2, df)
    return {"difference": diff, "interval": [float(diff - q * se), float(diff + q * se)], "df": float(df),
            "level": level}


def analyse_ii(matrix, agg) -> dict:
    ent = matrix["entries"]
    runs = agg["runs"]
    full = {e["model_seed"]: e["id"] for e in ent if e["kind"] == "full"}
    seeds = sorted(full)
    groups = sorted({e["group"] for e in ent if e["group"]})
    out = {"protocol": "R4a-ii (D-024), design D within the Engelen corrected Friday data",
           "code_commit": agg["environment"]["git_commit"], "environment_fingerprint": agg["environment"]["fingerprint"],
           "test_rows": runs[full[0]]["n"], "sesoi": SESOI, "family": [f"{g}/error_rate" for g in groups],
           "full_model": {}, "groups": {}}
    for m in ("errors", "error_rate", "mcc", "log_loss", "fp", "fn"):
        v = [runs[full[s]][m] for s in seeds]
        out["full_model"][m] = {"per_seed": v, "mean": float(np.mean(v)), "min": float(np.min(v)), "max": float(np.max(v))}
    pvals, cache = {}, {}
    for g in groups:
        gid = {e["model_seed"]: e["id"] for e in ent if e["kind"] == "group" and e["group"] == g}
        cid = {e["model_seed"]: e["id"] for e in ent if e["kind"] == "control" and e["group"] == g}
        size = len(next(e for e in ent if e["kind"] == "group" and e["group"] == g)["drop"])
        rec = {"label": LABEL.get(g, g), "removed_inputs": size, "endpoints": {}}
        for m in ("error_rate", "mcc", "log_loss"):
            dg = np.array([S.removal_effect(runs[gid[s]][m], runs[full[s]][m]) for s in seeds])
            dc = np.array([S.removal_effect(runs[cid[s]][m], runs[full[s]][m]) for s in seeds])
            d = S.contrasts(dg, dc)
            r = {"delta_group": dg.tolist(), "delta_control": dc.tolist(), "d": d.tolist(),
                 "mean_delta_group": float(dg.mean()), "mean_delta_control": float(dc.mean()),
                 "sign_flip": S.sign_flip_test(d), "primary": m == "error_rate"}
            if m == "error_rate":
                pvals[f"{g}/{m}"] = r["sign_flip"]["p"]
                cache[f"{g}/{m}"] = d
                for k in ("errors", "fp", "fn"):
                    r[f"{k}_group"] = [runs[gid[s]][k] for s in seeds]
                    r[f"{k}_control"] = [runs[cid[s]][k] for s in seeds]
            else:
                r["note"] = "secondary/descriptive (MCC is higher-is-better: Delta < 0 means removal worsened it)"
            rec["endpoints"][m] = r
        out["groups"][g] = rec
    h = S.holm(pvals)
    out["holm"] = h
    for key, d in cache.items():
        g, m = key.split("/")
        r = out["groups"][g]["endpoints"][m]
        r["reading"] = S.reading(d, SESOI, family_size=len(cache), holm_reject=h[key]["reject"])
        r["p_holm"] = h[key]["p_holm"]
    return out


def compare_with_r1(ii: dict) -> dict:
    r1 = json.loads(R1.read_text(encoding="utf-8"))
    out = {"status": "observational / descriptive (D-024): group composition, segmentation, label windows, "
                     "populations and definitions differ between the datasets", "groups": {}}
    for g, rec in ii["groups"].items():
        if g not in r1["groups"]:
            continue
        d_orig = np.array(r1["groups"][g]["endpoints"]["error_rate"]["d"])
        d_corr = np.array(rec["endpoints"]["error_rate"]["d"])
        out["groups"][g] = {"removed_inputs_original": r1["groups"][g]["removed_inputs"],
                            "removed_inputs_corrected": rec["removed_inputs"],
                            "mean_d_original": float(d_orig.mean()), "mean_d_corrected": float(d_corr.mean()),
                            "corrected_minus_original": welch(d_corr, d_orig)}
    f1, f2 = r1["full_model"]["error_rate"], ii["full_model"]["error_rate"]
    out["full_model_error_rate"] = {"original": {k: f1[k] for k in ("mean", "min", "max")},
                                    "corrected": {k: f2[k] for k in ("mean", "min", "max")},
                                    "original_rows": r1["test_rows"], "corrected_rows": ii["test_rows"]}
    return out


def analyse_i(path) -> dict:
    sc = json.loads(path.read_text(encoding="utf-8"))
    matrix = load_matrix()
    kind = {e["id"]: (e["kind"], e["group"]) for e in matrix["entries"]}
    if sc["n_scored"] != len(matrix["entries"]):
        raise RuntimeError(f"R4a-i scored {sc['n_scored']} of {len(matrix['entries'])} r1 models")
    rows = {}
    for rid, r in sc["runs"].items():
        k, g = kind[rid]
        key = "full" if k == "full" else f"{k}:{g}"
        rows.setdefault(key, []).append(r)
    summ = {}
    for key, rs in sorted(rows.items()):
        summ[key] = {"n_models": len(rs)}
        for m in ("ddos_recall", "benign_fpr", "error_rate", "mcc"):
            v = np.array([r[m] for r in rs], float)
            summ[key][m] = {"mean": float(np.nanmean(v)), "min": float(np.nanmin(v)), "max": float(np.nanmax(v))}
    return {"status": sc["status"], "population": sc["population"], "n": sc["n"], "n_ddos": sc["n_ddos"],
            "by_view": summ}


def tables(ii: dict, cmp: dict) -> tuple[str, str]:
    short = {"practically relevant difference": "relevant diff.", "practical equivalence at the SESOI": "equivalent",
             "inconclusive": "inconclusive", "difference (below SESOI or interval overlaps it)": "diff. $<$ SESOI"}
    md = ["| Group | Inputs removed | mean Δ group | mean Δ control | mean d | interval | p (exact) | p (Holm) | Reading | mean d original |",
          "|---|---|---|---|---|---|---|---|---|---|"]
    tex = [r"\begin{tabular}{@{}lrrrlr@{}}", r"\toprule",
           r"Group & $\bar\Delta_G$ & $\bar\Delta_R$ & $\bar d$ [CI] & $p_{\mathrm{Holm}}$ & $\bar d$ (orig.) \\",
           r"\midrule"]
    for g, rec in ii["groups"].items():
        r = rec["endpoints"]["error_rate"]
        rd = r["reading"]
        lo, hi = rd["interval_difference"]
        orig = cmp["groups"].get(g, {}).get("mean_d_original", float("nan"))
        md.append(f"| {rec['label']} | {rec['removed_inputs']} | {r['mean_delta_group']:+.6f} | {r['mean_delta_control']:+.6f} | "
                  f"{rd['mean_contrast']:+.6f} | [{lo:+.6f}, {hi:+.6f}] | {r['sign_flip']['p']:.4f} | {r['p_holm']:.4f} | "
                  f"{rd['reading']} | {orig:+.6f} |")
        tex.append(f"{rec['label'].split(':')[0]} ({rec['removed_inputs']}) & {r['mean_delta_group'] * 1e3:+.3f} & "
                   f"{r['mean_delta_control'] * 1e3:+.3f} & {rd['mean_contrast'] * 1e3:+.3f} [{lo * 1e3:+.3f}, {hi * 1e3:+.3f}] "
                   f"({short[rd['reading']]}) & {r['p_holm']:.3f} & {orig * 1e3:+.3f} \\\\")
    tex += [r"\bottomrule", r"\end{tabular}"]
    return "\n".join(md) + "\n", "\n".join(tex) + "\n"


def main() -> int:
    matrix, agg = load()
    ii = analyse_ii(matrix, agg)
    cmp = compare_with_r1(ii)
    res = {"r4a_ii": ii, "original_vs_corrected": cmp}
    i_path = DIR / "r4a_i_scores.json"
    if i_path.exists():
        res["r4a_i"] = analyse_i(i_path)
    (DIR / "stats_r4a.json").write_text(json.dumps(res, indent=1) + "\n", encoding="utf-8")
    md, tex = tables(ii, cmp)
    (DIR / "tables_r4a.md").write_text(md, encoding="utf-8")
    (ROOT / "paper/tables").mkdir(parents=True, exist_ok=True)
    (ROOT / "paper/tables/r4a.tex").write_text(tex, encoding="utf-8")
    print(md)
    f = ii["full_model"]
    print(f"R4a-ii full model: errors {f['errors']['per_seed']} on {ii['test_rows']} rows; "
          f"fp {f['fp']['per_seed']}; fn {f['fn']['per_seed']}")
    for g, c in cmp["groups"].items():
        w = c["corrected_minus_original"]
        print(f"{g}: mean d original {c['mean_d_original']:+.6f}, corrected {c['mean_d_corrected']:+.6f}, "
              f"difference {w['difference']:+.6f} [{w['interval'][0]:+.6f}, {w['interval'][1]:+.6f}] (descriptive)")
    if "r4a_i" in res:
        for k, v in res["r4a_i"]["by_view"].items():
            print(f"R4a-i {k}: DDoS recall {v['ddos_recall']['mean']:.4f} [{v['ddos_recall']['min']:.4f}, "
                  f"{v['ddos_recall']['max']:.4f}], benign FPR {v['benign_fpr']['mean']:.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
