"""Phase III review figures, drawn only from verified records (no training, no SHAP).

    python phase3_final_review/scripts/make_figures.py      -> phase3_final_review/figures/F*.png
Palette: validated categorical slots 1-4 (blue, orange, aqua, yellow); text in ink colours; values are
labelled directly because two slots are below 3:1 contrast on the surface.
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
REV = ROOT / "phase3_final_review"
V = REV / "evidence/verification"
FIG = REV / "figures"
C = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"]
INK, INK2, GRID, SURF = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"
load = lambda p: json.loads(Path(p).read_text(encoding="utf-8"))
plt.rcParams.update({"figure.facecolor": SURF, "axes.facecolor": SURF, "axes.edgecolor": INK2, "axes.labelcolor": INK,
                     "xtick.color": INK2, "ytick.color": INK2, "text.color": INK, "font.size": 8.5, "axes.spines.top": False,
                     "axes.spines.right": False, "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6, "lines.linewidth": 2,
                     "savefig.dpi": 200, "savefig.bbox": "tight"})
GL = {"A_flag_defects": "A flag-count defects", "B_appendix_closed": "B TCP appendix", "C_duplication": "C duplicated packets",
      "D_metadata_hypothesis": "D metadata hypotheses", "U_documented_union": "U union (A∪B∪C)"}


def contrasts(ax, stat, groups, ep, key_iv, scale, sesoi, title):
    for i, g in enumerate(groups):
        r = stat[f"{g}/{ep}"]
        d = np.array(r["d"]) * scale
        ax.scatter(d, np.full(len(d), i) + np.linspace(-0.18, 0.18, len(d)), s=16, color=C[0], alpha=0.75, lw=0, zorder=3)
        lo, hi = np.array(r[key_iv]) * scale
        ax.plot([lo, hi], [i, i], color=INK, lw=1.6, zorder=4)
        ax.plot(d.mean(), i, "D", color=INK, ms=5, zorder=5)
        ax.annotate(f"{d.mean():+.3f}", (hi, i), xytext=(4, 0), textcoords="offset points", va="center", fontsize=7.5, color=INK2)
    ax.axvspan(-sesoi * scale, sesoi * scale, color="#eeeeea", zorder=0)
    ax.axvline(0, color=INK2, lw=0.8)
    ax.set_yticks(range(len(groups)), [GL[g] for g in groups])
    ax.set_title(title, fontsize=9, loc="left")


def main() -> int:
    FIG.mkdir(parents=True, exist_ok=True)
    r1, r4 = load(V / "verify_r1.json"), load(V / "verify_r4a.json")
    g1 = ["A_flag_defects", "B_appendix_closed", "C_duplication", "D_metadata_hypothesis", "U_documented_union"]
    fig, ax = plt.subplots(1, 2, figsize=(8.6, 3.2), sharey=True)
    contrasts(ax[0], r1["statistics"], g1, "error_rate", "interval_99_5_difference", 1e3, 1e-3, "r1 in-domain error rate")
    contrasts(ax[1], r1["statistics"], g1, "fpr", "interval_99_5_difference", 1e3, 1e-3, "r1 Monday benign FPR")
    for a in ax:
        a.set_xlabel("paired contrast $d_s$ (×10$^{-3}$)")
    fig.text(0.01, -0.04, "Dots: 10 seed pairs; diamond: mean; bar: 99.5% t-interval (Bonferroni-consistent, family of 10); "
             "grey band: ±SESOI (1×10$^{-3}$). d > 0: removing the group hurts more than its random control.", fontsize=7.5, color=INK2)
    fig.savefig(FIG / "F1_r1_group_vs_control_contrasts.png"); plt.close(fig)

    g4 = ["A_flag_defects", "B_appendix_closed", "U_documented_union"]
    fig, ax = plt.subplots(1, 2, figsize=(8.6, 2.6), sharey=True, gridspec_kw={"width_ratios": [1.3, 1]})
    contrasts(ax[0], r4["statistics_r4a_ii"], g4, "error_rate", "interval_98_33_difference", 1e3, 1e-3, "R4a-ii corrected data: error rate")
    ax[0].set_xlabel("$d_s$ (×10$^{-3}$); bar = 98.33% t-interval (Holm family of 3)")
    s4 = load(ROOT / "results/r4a/stats_r4a.json")["original_vs_corrected"]["groups"]
    for i, g in enumerate(g4):
        o = r1["statistics"][f"{g}/error_rate"]["mean_d"] * 1e3
        c = s4[g]["mean_d_corrected"] * 1e3
        ax[1].plot([o, c], [i, i], color=GRID, lw=3, zorder=1)
        ax[1].plot(o, i, "o", color=C[1], ms=8, zorder=3, label="original (r1)" if i == 0 else None)
        ax[1].plot(c, i, "s", color=C[0], ms=8, zorder=3, label="corrected (R4a-ii)" if i == 0 else None)
    ax[1].axvline(0, color=INK2, lw=0.8)
    ax[1].set_title("mean $d$: original vs corrected (descriptive)", fontsize=9, loc="left")
    ax[1].set_xlabel("mean $d$ (×10$^{-3}$)")
    ax[1].legend(frameon=False, fontsize=7.5, ncol=2, loc="upper center", bbox_to_anchor=(0.5, -0.22))
    fig.savefig(FIG / "F2_r4a_ii_contrasts_and_original_vs_corrected.png"); plt.close(fig)

    views = ["full", "group:A_flag_defects", "group:B_appendix_closed", "group:C_duplication", "group:D_metadata_hypothesis",
             "group:U_documented_union", "control:A_flag_defects", "control:U_documented_union"]
    names = ["full", "without A", "without B", "without C", "without D", "without U", "A control", "U control"]
    ri = r4["r4a_i"]
    fig, ax = plt.subplots(1, 2, figsize=(8.6, 3.0), sharey=True)
    for j, (mt, title) in enumerate((("recall", "DDoS recall on corrected rows"), ("fpr", "benign FPR on corrected rows"))):
        for i, vname in enumerate(views):
            k, g = (vname, None) if vname == "full" else vname.split(":")
            vals = [r[mt] for r in ri.values() if r["kind"] == k and (g is None or r["group"] == g)]
            ax[j].scatter(vals, np.full(len(vals), i) + np.linspace(-0.18, 0.18, len(vals)), s=16, color=C[0], alpha=0.75, lw=0)
            ax[j].plot(np.mean(vals), i, "D", color=INK, ms=5)
            ax[j].annotate(f"{np.mean(vals):.3f}", (1.0 if mt == "recall" else max(vals), i), xytext=(4, 0), textcoords="offset points", va="center", fontsize=7.5, color=INK2)
        ax[j].set_title(title, fontsize=9, loc="left")
        ax[j].set_xlim(-0.03, 1.12 if mt == "recall" else 0.75)
    ax[0].set_yticks(range(len(views)), names); ax[0].invert_yaxis()
    ax[0].set_xlabel("per model (dots, 10 seeds) and mean (diamond)"); ax[1].set_xlabel("per model and mean")
    fig.savefig(FIG / "F3_r4a_i_transfer_descriptive.png"); plt.close(fig)

    fig, ax = plt.subplots(figsize=(6.4, 3.0))
    keys = [("full", None)] + [(k, g) for g in g1 for k in ("group", "control")]
    for i, (k, g) in enumerate(keys):
        vals = [r["monday"]["fp"] for r in r1["runs"].values() if r["kind"] == k and (g is None or r["group"] == g)]
        ax.scatter(vals, np.full(len(vals), i) + np.linspace(-0.18, 0.18, len(vals)), s=14, color=C[0] if k != "control" else C[1], alpha=0.8, lw=0)
        ax.plot(np.mean(vals), i, "D", color=INK, ms=4.5)
    ax.set_yticks(range(len(keys)), ["full"] + [f"{'without' if k == 'group' else 'ctrl'} {g[0]}" for k, g in keys[1:]]); ax.invert_yaxis()
    ax.set_xlabel("false positives on 494,940 Monday benign rows (dots: 10 seeds; diamond: mean)")
    ax.set_title("Monday benign false positives (blue: group removed; orange: matched control)", fontsize=9, loc="left")
    fig.savefig(FIG / "F4_monday_false_positives.png"); plt.close(fig)

    dc = load(V / "verify_dcnn.json")["seeds"]
    fig, ax = plt.subplots(1, 3, figsize=(8.6, 2.6))
    for j, mt in enumerate(("mcc", "dos_precision", "dos_recall")):
        for i, (p, lab, col) in enumerate((("official", "official", C[1]), ("dedup_model_visible", "filtered", C[0]))):
            vals = [dc[str(s)][p][mt] for s in range(5)]
            ax[j].scatter(np.full(5, i) + np.linspace(-0.12, 0.12, 5), vals, s=18, color=col, lw=0)
            ax[j].annotate(f"{np.mean(vals):.3f}", (i, np.mean(vals)), xytext=(10, 0), textcoords="offset points", fontsize=7.5, color=INK2, va="center")
        for s in range(5):
            ax[j].plot([0, 1], [dc[str(s)]["official"][mt], dc[str(s)]["dedup_model_visible"][mt]], color=GRID, lw=1, zorder=0)
        ax[j].set_xticks([0, 1], ["official\n41,089", "dup-filtered\n37,759"]); ax[j].set_xlim(-0.5, 1.7)
        ax[j].set_title({"mcc": "MCC", "dos_precision": "DoS precision", "dos_recall": "DoS recall"}[mt], fontsize=9, loc="left")
    fig.suptitle("DCNN+SA, five seeds, same models on two test populations (lines join the same seed)", fontsize=9, x=0.01, y=1.06, ha="left")
    fig.savefig(FIG / "F5_dcnn_official_vs_filtered.png"); plt.close(fig)

    me = load(V / "verify_mes.json")["fits"]
    fig, ax = plt.subplots(1, 2, figsize=(8.0, 2.6), sharey=True)
    for j, net in enumerate(("N1_unsw", "N2_ton")):
        for i, (mode, col) in enumerate((("random", C[1]), ("dup_aware", C[0]))):
            vals = [me[f"{mode}_seed{s}"]["test"][f"{net}/ensemble/all"]["mcc"] for s in range(5)]
            ax[j].scatter(np.full(5, i) + np.linspace(-0.12, 0.12, 5), vals, s=18, color=col, lw=0)
            ax[j].annotate(f"mean {np.mean(vals):.3f}", (i, np.mean(vals)), xytext=(10, 0), textcoords="offset points", fontsize=7.5, color=INK2, va="center")
        ax[j].set_xticks([0, 1], ["random split", "duplicate-aware"]); ax[j].set_xlim(-0.5, 1.8)
        ax[j].set_title(f"MES-DNN ensemble MCC, {'NF-UNSW-NB15-v2' if j == 0 else 'NF-ToN-IoT-v2 subsample'}", fontsize=9, loc="left")
        ax[j].axhline(0, color=INK2, lw=0.8)
    ax[0].set_ylabel("MCC per seed (5 seeds)")
    fig.savefig(FIG / "F6_mes_dnn_split_modes.png"); plt.close(fig)

    arr = load(ROOT / "results/corrections/milestone2b/corrected_arr_v2.json")["variants"]
    Ks = ["2", "5", "10", "20"]
    fig, ax = plt.subplots(figsize=(6.0, 2.8))
    for j, (tier, lab) in enumerate((("all", "all registered (23)"), ("direct", "direct extraction defects (16)"),
                                     ("shortcut", "shortcut (6)"), ("hypothesis", "hypothesis only (2)"))):
        lo = [min(v["methods"]["sum_abs"]["arr"][k][tier] for v in arr.values()) * 100 for k in Ks]
        hi = [max(v["methods"]["sum_abs"]["arr"][k][tier] for v in arr.values()) * 100 for k in Ks]
        x = np.arange(4) + (j - 1.5) * 0.18
        ax.vlines(x, lo, hi, color=C[j], lw=5, label=lab)
        for xi, l, h in zip(x, lo, hi):
            if tier == "all":
                ax.annotate(f"{l:.1f}–{h:.1f}", (xi, h), xytext=(0, 3), textcoords="offset points", ha="center", fontsize=7, color=INK2)
    ax.set_xticks(range(4), [f"ARR@{k}" for k in Ks]); ax.set_ylabel("attribution-mass share in top K (%)")
    ax.set_title("AE-XGBoost (M1A seed-0 model) ARR, registry v2; bar = range over 6 SHAP variants", fontsize=9, loc="left")
    ax.set_ylim(-2, 68)
    ax.legend(frameon=False, fontsize=7.5, ncol=4, loc="upper center", bbox_to_anchor=(0.5, -0.12))
    fig.savefig(FIG / "F7_arr_by_k_registry_v2.png"); plt.close(fig)

    fig, ax = plt.subplots(figsize=(6.0, 2.4))
    e1 = [r["metrics"]["errors"] for r in sorted(r1["runs"].values(), key=lambda r: r["seed"]) if r["kind"] == "full"]
    e4 = [r["metrics"]["errors"] for r in sorted(r4["runs_r4a_ii"].values(), key=lambda r: r["seed"]) if r["kind"] == "full"]
    ax.plot(range(10), e1, "o-", color=C[1], ms=6, label="r1 original (33,038 rows)")
    ax.plot(range(10), e4, "s-", color=C[0], ms=6, label="R4a-ii corrected (22,049 rows)")
    ax.set_xticks(range(10)); ax.set_xlabel("model seed"); ax.set_ylabel("test errors (count)")
    ax.set_title("Full AE-XGBoost model: errors per seed (different test populations; not comparable as counts)", fontsize=8.5, loc="left")
    ax.legend(frameon=False, fontsize=7.5)
    fig.savefig(FIG / "F8_full_model_errors_per_seed.png"); plt.close(fig)
    print("figures written:", sorted(p.name for p in FIG.glob("*.png")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
