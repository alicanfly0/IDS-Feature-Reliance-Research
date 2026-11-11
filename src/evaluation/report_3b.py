"""Milestone 3B pre-registered analysis (protocol r1, design D). Reads committed records only.

Inputs: results/milestone3b/aggregate_r1.json (aggregate_3b on Colab, 110/110 runs, identical
test rows) and results/milestone3b/monday_fpr_r1.json (score_benign on the recorded Monday rows).
Primary family (10 tests, Holm): groups A, B, C, D, U x {in-domain error rate, Monday FPR}.
d_s = Delta_group,s - Delta_control(draw s),s; exact sign-flip p; t intervals at 1 - alpha/10
(difference) and 1 - 2 alpha/10 (TOST); SESOI 0.001 for both endpoints (D-020 r1).

  python -m src.evaluation.report_3b     # writes stats_r1.json, tables_r1.md, paper tables/figure
"""
from __future__ import annotations

import json

import numpy as np

from src.data.manifest import ROOT
from src.evaluation import stats_3b as S
from src.experiments.matrix_3b import load_matrix

DIR = ROOT / "results/milestone3b"
SESOI = {"error_rate": 0.001, "fpr": 0.001}
GROUP_LABEL = {"A_flag_defects": "A: TCP flag-count defects", "B_appendix_closed": "B: TCP appendix",
               "C_duplication": "C: duplicated packets", "D_metadata_hypothesis": "D: metadata hypotheses",
               "U_documented_union": "U: union"}


def load() -> tuple[dict, dict, dict]:
    matrix = load_matrix()
    agg = json.loads((DIR / "aggregate_r1.json").read_text(encoding="utf-8"))
    mon = json.loads((DIR / "monday_fpr_r1.json").read_text(encoding="utf-8"))
    if agg["n_completed"] != 110 or agg["n_matrix"] != 110 or len(mon) != 110:
        raise RuntimeError("incomplete records")
    for e in matrix["entries"]:
        if agg["runs"][e["id"]]["run"] != mon[e["id"]]["run"]:
            raise RuntimeError(f"{e['id']}: aggregate and Monday scored different run directories")
    return matrix, agg, mon


def metric(agg, mon, rid: str, m: str) -> float:
    return mon[rid]["fpr"] if m == "fpr" else agg["runs"][rid][m]


def analyse() -> dict:
    matrix, agg, mon = load()
    ent = matrix["entries"]
    full = {e["model_seed"]: e["id"] for e in ent if e["kind"] == "full"}
    groups = sorted({e["group"] for e in ent if e["group"]})
    seeds = sorted(full)
    out = {"protocol": "r1 design D", "code_commit": agg["environment"]["git_commit"],
           "environment_fingerprint": agg["environment"]["fingerprint"],
           "test_rows": agg["runs"][full[0]]["n"], "monday_rows": mon[full[0]]["n"], "sesoi": SESOI,
           "full_model": {}, "groups": {}}
    for m in ("errors", "error_rate", "mcc", "log_loss", "fpr"):
        v = [metric(agg, mon, full[s], m) if m != "errors" else agg["runs"][full[s]]["errors"] for s in seeds]
        out["full_model"][m] = {"per_seed": v, "mean": float(np.mean(v)), "min": float(np.min(v)), "max": float(np.max(v))}
    out["full_model"]["monday_false_positives"] = [mon[full[s]]["false_positives"] for s in seeds]
    pvals, cache = {}, {}
    for g in groups:
        gid = {e["model_seed"]: e["id"] for e in ent if e["kind"] == "group" and e["group"] == g}
        cid = {e["model_seed"]: e["id"] for e in ent if e["kind"] == "control" and e["group"] == g}
        size = len(next(e for e in ent if e["kind"] == "group" and e["group"] == g)["drop"])
        rec = {"label": GROUP_LABEL.get(g, g), "removed_inputs": size, "endpoints": {}}
        for m in ("error_rate", "fpr", "mcc", "log_loss"):
            dg = np.array([S.removal_effect(metric(agg, mon, gid[s], m), metric(agg, mon, full[s], m)) for s in seeds])
            dc = np.array([S.removal_effect(metric(agg, mon, cid[s], m), metric(agg, mon, full[s], m)) for s in seeds])
            d = S.contrasts(dg, dc)
            r = {"delta_group": dg.tolist(), "delta_control": dc.tolist(), "d": d.tolist(),
                 "mean_delta_group": float(dg.mean()), "mean_delta_control": float(dc.mean()),
                 "sign_flip": S.sign_flip_test(d), "primary": m in SESOI}
            if m in SESOI:
                pvals[f"{g}/{m}"] = r["sign_flip"]["p"]
                cache[f"{g}/{m}"] = d
            else:
                r["note"] = "secondary/descriptive (MCC is higher-is-better: Delta < 0 means removal worsened it)"
            if m == "error_rate":
                r["errors_group"] = [agg["runs"][gid[s]]["errors"] for s in seeds]
                r["errors_control"] = [agg["runs"][cid[s]]["errors"] for s in seeds]
            if m == "fpr":
                r["fp_group"] = [mon[gid[s]]["false_positives"] for s in seeds]
                r["fp_control"] = [mon[cid[s]]["false_positives"] for s in seeds]
            rec["endpoints"][m] = r
        out["groups"][g] = rec
    h = S.holm(pvals)
    out["holm"] = h
    for key, d in cache.items():
        g, m = key.split("/")
        out["groups"][g]["endpoints"][m]["reading"] = S.reading(d, SESOI[m], holm_reject=h[key]["reject"])
        out["groups"][g]["endpoints"][m]["p_holm"] = h[key]["p_holm"]
    return out


def tables(res: dict) -> tuple[str, str]:
    md = ["| Group | Inputs removed | Endpoint | mean Δ group | mean Δ control | mean d | 99% interval | p (exact) | p (Holm) | Reading |",
          "|---|---|---|---|---|---|---|---|---|---|"]
    tex = [r"\begin{tabular}{@{}llrrrrl@{}}", r"\toprule",
           r"Group & Endpoint & $\bar\Delta_G$ & $\bar\Delta_R$ & $\bar d$ [99\% CI] & $p_{\mathrm{Holm}}$ & Reading \\",
           r"\midrule"]
    short = {"practically relevant difference": "relevant diff.", "practical equivalence at the SESOI": "equivalent",
             "inconclusive": "inconclusive", "difference (below SESOI or interval overlaps it)": "diff. $<$ SESOI"}
    for g, rec in res["groups"].items():
        for m, name in (("error_rate", "error rate"), ("fpr", "Monday FPR")):
            r = rec["endpoints"][m]
            rd = r["reading"]
            lo, hi = rd["interval_difference"]
            md.append(f"| {rec['label']} | {rec['removed_inputs']} | {name} | {r['mean_delta_group']:+.6f} | "
                      f"{r['mean_delta_control']:+.6f} | {rd['mean_contrast']:+.6f} | [{lo:+.6f}, {hi:+.6f}] | "
                      f"{r['sign_flip']['p']:.4f} | {r['p_holm']:.4f} | {rd['reading']} |")
            tex.append(f"{rec['label'].split(':')[0]} ({rec['removed_inputs']}) & {name} & "
                       f"{r['mean_delta_group'] * 1e3:+.3f} & {r['mean_delta_control'] * 1e3:+.3f} & "
                       f"{rd['mean_contrast'] * 1e3:+.3f} [{lo * 1e3:+.3f}, {hi * 1e3:+.3f}] & "
                       f"{r['p_holm']:.3f} & {short[rd['reading']]} \\\\")
    tex += [r"\bottomrule", r"\end{tabular}"]
    return "\n".join(md) + "\n", "\n".join(tex) + "\n"


def figure(res: dict, path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 2.8), sharey=True)
    groups = list(res["groups"])
    for ax, (m, title) in zip(axes, (("error_rate", "In-domain error rate"), ("fpr", "Monday benign FPR"))):
        for i, g in enumerate(groups):
            r = res["groups"][g]["endpoints"][m]
            d = np.array(r["d"]) * 1e3
            ax.scatter(d, np.full(len(d), i) + np.linspace(-0.15, 0.15, len(d)), s=9, color="#4a6fa5", alpha=0.7, lw=0)
            lo, hi = np.array(r["reading"]["interval_difference"]) * 1e3
            ax.plot([lo, hi], [i, i], color="black", lw=1.2)
            ax.plot(d.mean(), i, "D", color="black", ms=4)
        s = res["sesoi"][m] * 1e3
        ax.axvspan(-s, s, color="#dddddd", zorder=0)
        ax.axvline(0, color="grey", lw=0.6)
        ax.set_title(title, fontsize=9)
        ax.set_xlabel(r"$d_s$ ($\times 10^{-3}$)", fontsize=8)
        ax.tick_params(labelsize=7)
    axes[0].set_yticks(range(len(groups)), [res["groups"][g]["label"].split(":")[0] for g in groups])
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def main() -> int:
    res = analyse()
    DIR.mkdir(parents=True, exist_ok=True)
    (DIR / "stats_r1.json").write_text(json.dumps(res, indent=1) + "\n", encoding="utf-8")
    md, tex = tables(res)
    (DIR / "tables_r1.md").write_text(md, encoding="utf-8")
    (ROOT / "paper/tables").mkdir(parents=True, exist_ok=True)
    (ROOT / "paper/tables/main_r1.tex").write_text(tex, encoding="utf-8")
    (ROOT / "paper/figures").mkdir(parents=True, exist_ok=True)
    figure(res, ROOT / "paper/figures/contrasts_r1.pdf")
    print(md)
    f = res["full_model"]
    print(f"full model: errors {f['errors']['per_seed']}; Monday FPR mean {f['fpr']['mean']:.6f} "
          f"(range {f['fpr']['min']:.6f}-{f['fpr']['max']:.6f}); FP {f['monday_false_positives']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
