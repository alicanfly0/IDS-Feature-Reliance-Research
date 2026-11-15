"""Result figures for the Phase IV paper, drawn only from verified Phase III records (vector PDF).

    python paper/figures/make_paper_figures.py      (from the repository root)

Inputs (all committed):
  phase3_final_review/evidence/verification/verify_r1.json     110 r1 fits, re-scored from predictions
  phase3_final_review/evidence/verification/verify_r4a.json    70 R4a-ii fits + 110 R4a-i scorings
  phase3_final_review/evidence/verification/verify_dcnn.json   DCNN, 5 seeds x 3 test populations
  phase3_final_review/evidence/verification/verify_mes.json    MES-DNN, 10 ensemble fits
  results/r4a/stats_r4a.json                                   original-vs-corrected Welch comparison
  results/corrections/milestone2b/corrected_arr_v2.json        ARR@K, registry v2, 6 SHAP variants
Styling is grayscale-safe: identity is carried by marker shape and fill, never by colour alone.
Sizes are set for the printed IEEE column (3.5 in) and page (7.16 in); figures are placed at 100%,
so the smallest text in any figure is 7 pt.
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
V = ROOT / "phase3_final_review/evidence/verification"
OUT = Path(__file__).resolve().parent
COL, FULL = 3.45, 7.0
K, G1, G2 = "#000000", "#555555", "#999999"
plt.rcParams.update({
    "font.family": "serif", "font.serif": ["STIXGeneral", "Times New Roman", "DejaVu Serif"], "mathtext.fontset": "stix",
    "font.size": 8.5, "axes.titlesize": 8.5, "axes.labelsize": 8.5, "xtick.labelsize": 8, "ytick.labelsize": 8,
    "legend.fontsize": 7.5, "axes.linewidth": 0.6, "xtick.major.width": 0.5, "ytick.major.width": 0.5,
    "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "grid.color": "#dddddd", "grid.linewidth": 0.4,
    "pdf.fonttype": 42, "savefig.bbox": "tight", "savefig.pad_inches": 0.02})
load = lambda p: json.loads(Path(p).read_text(encoding="utf-8"))
r1, r4 = load(V / "verify_r1.json"), load(V / "verify_r4a.json")
GN = {"A_flag_defects": "A", "B_appendix_closed": "B", "C_duplication": "C", "D_metadata_hypothesis": "D", "U_documented_union": "U"}
G1_ORDER = ["A_flag_defects", "B_appendix_closed", "C_duplication", "D_metadata_hypothesis", "U_documented_union"]
G4_ORDER = ["A_flag_defects", "B_appendix_closed", "U_documented_union"]


def contrast_panel(ax, stat, groups, ep, iv_key, scale, title, xlabel):
    for i, g in enumerate(groups):
        r = stat[f"{g}/{ep}"]
        d = np.array(r["d"]) * scale
        y = len(groups) - 1 - i
        ax.scatter(d, np.full(len(d), y) + np.linspace(-0.22, 0.22, len(d)), s=12, facecolors="none", edgecolors=G1, linewidths=0.7, zorder=3)
        lo, hi = np.array(r[iv_key]) * scale
        ax.plot([lo, hi], [y, y], color=K, lw=1.6, zorder=4)
        ax.plot(d.mean(), y, "D", color=K, ms=4.6, zorder=5)
    ax.axvspan(-1, 1, color="#ececec", zorder=0, lw=0)
    ax.axvline(0, color=G1, lw=0.6)
    ax.set_yticks(range(len(groups)), [GN[g] for g in reversed(groups)])
    ax.set_title(title, loc="left")
    ax.set_xlabel(xlabel)
    ax.grid(axis="y", visible=False)


def contrast_legend(ax, level):
    h = [Line2D([], [], ls="none", marker="o", mfc="none", mec=G1, ms=4, label="seed"),
         Line2D([], [], ls="none", marker="D", color=K, ms=4.2, label="mean"),
         Line2D([], [], color=K, lw=1.6, label=f"{level} difference interval"),
         Patch(facecolor="#ececec", label=r"$\pm\delta$ (SESOI)")]
    ax.legend(handles=h, frameon=False, ncol=4, loc="upper left", bbox_to_anchor=(0.0, -0.27), handletextpad=0.4, columnspacing=1.2)


def fig_r1():
    fig, ax = plt.subplots(1, 2, figsize=(FULL, 2.45), sharey=True)
    contrast_panel(ax[0], r1["statistics"], G1_ORDER, "error_rate", "interval_99_5_difference", 1e3,
                   "(a) In-domain error rate, $n=33{,}038$ test flows", r"paired contrast $d_s$ ($\times10^{-3}$)")
    contrast_panel(ax[1], r1["statistics"], G1_ORDER, "fpr", "interval_99_5_difference", 1e3,
                   "(b) Monday benign FPR, $n=494{,}940$ benign flows", r"paired contrast $d_s$ ($\times10^{-3}$)")
    ax[0].set_ylabel("removed group")
    contrast_legend(ax[0], "99.5%")
    fig.savefig(OUT / "fig_r1_contrasts.pdf"); plt.close(fig)


def fig_r4a():
    fig, ax = plt.subplots(1, 2, figsize=(FULL, 2.2), gridspec_kw={"width_ratios": [1.15, 1]})
    contrast_panel(ax[0], r4["statistics_r4a_ii"], G4_ORDER, "error_rate", "interval_98_33_difference", 1e3,
                   "(a) R4a-ii, corrected capture, $n=22{,}049$ test flows", r"paired contrast $d_s$ ($\times10^{-3}$)")
    ax[0].set_xlim(-1.08, 1.08)
    ax[0].set_xticks([-1, -0.5, 0, 0.5, 1])
    contrast_legend(ax[0], "98.33%")
    cmp = load(ROOT / "results/r4a/stats_r4a.json")["original_vs_corrected"]["groups"]
    for i, g in enumerate(G4_ORDER):
        y = len(G4_ORDER) - 1 - i
        c = cmp[g]
        o, n = c["mean_d_original"] * 1e3, c["mean_d_corrected"] * 1e3
        ax[1].plot([o, n], [y + 0.12, y - 0.12], color=G2, lw=0.9, zorder=1)
        ax[1].plot(o, y + 0.12, "o", mfc="white", mec=K, ms=5.5, mew=0.9, zorder=3, label="original (r1)" if i == 0 else None)
        ax[1].plot(n, y - 0.12, "s", color=K, ms=5, zorder=3, label="corrected (R4a-ii)" if i == 0 else None)
    ax[1].axvline(0, color=G1, lw=0.6)
    ax[1].set_yticks(range(3), [GN[g] for g in reversed(G4_ORDER)])
    ax[1].set_ylim(-0.6, 2.6)
    ax[1].grid(axis="y", visible=False)
    ax[1].set_title("(b) Mean contrast, two captures (observational)", loc="left")
    ax[1].set_xlabel(r"mean $\bar d$ ($\times10^{-3}$)")
    ax[1].legend(frameon=False, loc="center right", handletextpad=0.3)
    fig.savefig(OUT / "fig_r4a_contrasts.pdf"); plt.close(fig)


def fig_transfer():
    views = [("full", None, "full model"), ("group", "A_flag_defects", "without A"), ("group", "B_appendix_closed", "without B"),
             ("group", "C_duplication", "without C"), ("group", "D_metadata_hypothesis", "without D"), ("group", "U_documented_union", "without U"),
             ("control", None, "random controls")]
    ri = r4["r4a_i"].values()
    fig, ax = plt.subplots(1, 2, figsize=(COL, 2.75), sharey=True, gridspec_kw={"width_ratios": [1.3, 1]})
    for j, (m, xl) in enumerate((("recall", "DDoS recall (%)"), ("fpr", "benign FPR (%)"))):
        for i, (k, g, _) in enumerate(views):
            vals = np.array([r[m] for r in ri if r["kind"] == k and (g is None or r["group"] == g)]) * 100
            y = len(views) - 1 - i
            ax[j].plot([vals.min(), vals.max()], [y, y], color=G2, lw=2.2, solid_capstyle="butt", zorder=1)
            ax[j].scatter(vals, np.full(len(vals), y) + np.linspace(-0.25, 0.25, len(vals)), s=10, facecolors="none", edgecolors=K, linewidths=0.6, zorder=2)
            ax[j].plot(vals.mean(), y, "D", color=K, ms=4.4, zorder=3)
            if j == 0 and k == "full":
                ax[j].annotate(f"range {vals.min():.0f}–{vals.max():.1f}%,\nmean {vals.mean():.1f}%", (vals.max(), y), xytext=(-2, 7),
                               textcoords="offset points", ha="right", va="bottom", fontsize=7.5)
        ax[j].set_xlabel(xl)
        ax[j].grid(axis="y", visible=False)
    ax[0].set_xlim(-4, 104)
    ax[1].set_xlim(-3, 65)
    ax[0].set_ylim(-0.7, len(views) - 0.1)
    ax[0].set_yticks(range(len(views)), [v[2] for v in reversed(views)])
    h = [Line2D([], [], ls="none", marker="o", mfc="none", mec=K, ms=4, label="one model"),
         Line2D([], [], ls="none", marker="D", color=K, ms=4.2, label="mean"),
         Line2D([], [], color=G2, lw=2.2, label="min–max")]
    fig.legend(handles=h, frameon=False, ncol=3, loc="lower center", bbox_to_anchor=(0.55, 0.0), handletextpad=0.3, columnspacing=1.0)
    fig.subplots_adjust(bottom=0.24, wspace=0.08)
    fig.savefig(OUT / "fig_transfer.pdf"); plt.close(fig)


def fig_arr():
    arr = load(ROOT / "results/corrections/milestone2b/corrected_arr_v2.json")["variants"]
    Ks = ["2", "5", "10", "20"]
    tiers = [("all", "all registered (23; not group U)", "o", K, K), ("direct", "direct defects (16)", "s", K, "white"),
             ("shortcut", "shortcut (6)", "^", G1, G1), ("hypothesis", "hypothesis (2)", "v", G1, "white")]
    fig, ax = plt.subplots(figsize=(COL, 2.35))
    for j, (t, lab, mk, ec, fc) in enumerate(tiers):
        x = np.arange(4) + (j - 1.5) * 0.18
        lo = [min(v["methods"]["sum_abs"]["arr"][k][t] for v in arr.values()) * 100 for k in Ks]
        hi = [max(v["methods"]["sum_abs"]["arr"][k][t] for v in arr.values()) * 100 for k in Ks]
        ax.vlines(x, lo, hi, color=ec, lw=1.3)
        ax.plot(x, [(a + b) / 2 for a, b in zip(lo, hi)], mk, mec=ec, mfc=fc, ms=4.8, mew=0.8, ls="none", label=lab)
    ax.set_xticks(range(4), [f"$K={k}$" for k in Ks])
    ax.set_ylabel("ARR@$K$ (%)")
    ax.set_ylim(-3, 92)
    ax.grid(axis="x", visible=False)
    ax.legend(frameon=False, ncol=2, loc="upper right", columnspacing=0.8, handletextpad=0.3)
    fig.savefig(OUT / "fig_arr.pdf"); plt.close(fig)


def fig_dcnn():
    d = load(V / "verify_dcnn.json")
    dc = d["seeds"]
    fig, ax = plt.subplots(1, 3, figsize=(COL, 2.2))
    for j, (m, title) in enumerate((("mcc", "MCC"), ("dos_precision", "DoS precision"), ("dos_recall", "DoS recall"))):
        for s in range(5):
            a, b = dc[str(s)]["official"][m], dc[str(s)]["dedup_model_visible"][m]
            ax[j].plot([0, 1], [a, b], color=G2, lw=0.8, zorder=1)
            ax[j].plot(0, a, "o", mfc="white", mec=K, ms=4.4, mew=0.8, zorder=2)
            ax[j].plot(1, b, "s", color=K, ms=4.2, zorder=2)
        ax[j].set_xticks([0, 1], ["official", "filtered"], rotation=30, ha="right", rotation_mode="anchor")
        ax[j].set_xlim(-0.35, 1.35)
        ax[j].set_title(title)
        ax[j].grid(axis="x", visible=False)
    fig.tight_layout(w_pad=0.5)
    fig.savefig(OUT / "fig_dcnn.pdf"); plt.close(fig)


def fig_mes():
    me = load(V / "verify_mes.json")["fits"]
    fig, ax = plt.subplots(2, 2, figsize=(COL, 3.3), sharey=True, sharex=True)
    nets = (("N1_unsw", "N1 (NF-UNSW-NB15-v2)"), ("N2_ton", "N2 (NF-ToN-IoT-v2)"))
    rows = (("base", "own base DNN", "s", "white"), ("ensemble", "stacked ensemble", "o", K))
    for i, (model, rlab, mk, fc) in enumerate(rows):
        for j, (net, title) in enumerate(nets):
            key = f"{net}/base_{net}/all" if model == "base" else f"{net}/ensemble/all"
            for k, mode in enumerate(("random", "dup_aware")):
                vals = [me[f"{mode}_seed{s}"]["test"][key]["mcc"] for s in range(5)]
                ax[i, j].plot(np.full(5, k) + np.linspace(-0.12, 0.12, 5), vals, mk, mec=K, mfc=fc, ms=4.6, mew=0.8, ls="none")
                ax[i, j].plot([k - 0.22, k + 0.22], [np.mean(vals)] * 2, color=K, lw=1.2)
            ax[i, j].axhline(0, color=G1, lw=0.6)
            ax[i, j].set_xlim(-0.5, 1.5)
            ax[i, j].set_ylim(-0.25, 1.05)
            ax[i, j].grid(axis="x", visible=False)
            if i == 0:
                ax[i, j].set_title(title, fontsize=7.5)
            if j == 0:
                ax[i, j].set_ylabel(f"{rlab}\nMCC")
        ax[1, 0].set_xticks([0, 1], ["random", "dup.-aware"])
        ax[1, 1].set_xticks([0, 1], ["random", "dup.-aware"])
    fig.text(0.56, -0.02, "split protocol (models retrained under each)", ha="center", fontsize=8)
    fig.tight_layout(h_pad=0.6, w_pad=0.4)
    fig.savefig(OUT / "fig_mes.pdf"); plt.close(fig)


def fig_errors():
    full = sorted((r for r in r1["runs"].values() if r["kind"] == "full"), key=lambda r: r["seed"])
    f4 = sorted((r for r in r4["runs_r4a_ii"].values() if r["kind"] == "full"), key=lambda r: r["seed"])
    dc = load(V / "verify_dcnn.json")["seeds"]
    fig, ax = plt.subplots(1, 2, figsize=(COL, 2.55), gridspec_kw={"width_ratios": [1.45, 1]})
    s = np.arange(10)
    w = 0.38
    ax[0].bar(s - w / 2, [r["metrics"]["fp"] for r in full], w, color="white", edgecolor=K, lw=0.6, hatch="/////", label="FP, original")
    ax[0].bar(s - w / 2, [r["metrics"]["fn"] for r in full], w, bottom=[r["metrics"]["fp"] for r in full], color=G2, edgecolor=K, lw=0.6, label="FN, original")
    ax[0].bar(s + w / 2, [r["metrics"]["fp"] for r in f4], w, color="white", edgecolor=G1, lw=0.6, hatch="....", label="FP, corrected")
    ax[0].bar(s + w / 2, [r["metrics"]["fn"] for r in f4], w, bottom=[r["metrics"]["fp"] for r in f4], color=K, edgecolor=K, lw=0.6, label="FN, corrected")
    ax[0].set_xticks(s)
    ax[0].set_xlabel("seed")
    ax[0].set_ylabel("errors (count)")
    ax[0].set_title("(a) AE-XGBoost full model", fontsize=8.5)
    ax[0].set_ylim(0, 10)
    ax[0].grid(axis="x", visible=False)
    for k, (pop, lab) in enumerate((("official", "official"), ("dedup_model_visible", "filtered"))):
        fp = float(np.mean([dc[str(i)][pop]["fp"] for i in range(5)]))
        fn = float(np.mean([dc[str(i)][pop]["fn"] for i in range(5)]))
        ax[1].bar(k - 0.18, fp, 0.34, color="white", edgecolor=K, lw=0.6, hatch="/////")
        ax[1].bar(k + 0.18, fn, 0.34, color=G2, edgecolor=K, lw=0.6)
        ax[1].text(k - 0.18, fp * 1.15, f"{fp:,.0f}", ha="center", va="bottom", fontsize=7)
        ax[1].text(k + 0.18, fn * 1.15, f"{fn:,.0f}", ha="center", va="bottom", fontsize=7)
    ax[1].set_yscale("log")
    ax[1].set_ylim(10, 3e4)
    ax[1].set_xticks([0, 1], ["official", "filtered"])
    ax[1].set_ylabel("mean errors, log scale")
    ax[1].set_xlabel("test rows")
    ax[1].set_title("(b) DCNN+SA", fontsize=8.5)
    ax[1].grid(axis="x", visible=False)
    # one legend per panel, each naming its own populations
    ha = [Patch(facecolor="white", edgecolor=K, hatch="/////", label="FP, original"),
          Patch(facecolor=G2, edgecolor=K, label="FN, original"),
          Patch(facecolor="white", edgecolor=G1, hatch="....", label="FP, corrected"),
          Patch(facecolor=K, edgecolor=K, label="FN, corrected")]
    ax[0].legend(handles=ha, frameon=False, ncol=2, loc="upper center", bbox_to_anchor=(0.5, -0.3),
                 handlelength=1.3, columnspacing=0.8, handletextpad=0.4)
    hb = [Patch(facecolor="white", edgecolor=K, hatch="/////", label="false pos."),
          Patch(facecolor=G2, edgecolor=K, label="false neg.")]
    ax[1].legend(handles=hb, frameon=False, ncol=1, loc="upper center", bbox_to_anchor=(0.5, -0.3),
                 handlelength=1.3, handletextpad=0.4)
    fig.tight_layout(w_pad=0.8)
    fig.savefig(OUT / "fig_errors.pdf"); plt.close(fig)


if __name__ == "__main__":
    for f in (fig_r1, fig_r4a, fig_transfer, fig_arr, fig_dcnn, fig_mes, fig_errors):
        f()
    print(sorted(p.name for p in OUT.glob("fig_*.pdf")))
