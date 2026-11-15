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
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
V = ROOT / "phase3_final_review/evidence/verification"
OUT = Path(__file__).resolve().parent
COL, FULL = 3.45, 7.0
K, G1, G2 = "#000000", "#555555", "#999999"
plt.rcParams.update({
    "font.family": "serif", "font.serif": ["STIXGeneral", "Times New Roman", "DejaVu Serif"], "mathtext.fontset": "stix",
    "font.size": 7.5, "axes.titlesize": 7.5, "axes.labelsize": 7.5, "xtick.labelsize": 6.8, "ytick.labelsize": 6.8,
    "legend.fontsize": 6.6, "axes.linewidth": 0.6, "xtick.major.width": 0.5, "ytick.major.width": 0.5,
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
        ax.scatter(d, np.full(len(d), y) + np.linspace(-0.2, 0.2, len(d)), s=7, facecolors="none", edgecolors=G1, linewidths=0.6, zorder=3)
        lo, hi = np.array(r[iv_key]) * scale
        ax.plot([lo, hi], [y, y], color=K, lw=1.3, zorder=4)
        ax.plot(d.mean(), y, "D", color=K, ms=3.6, zorder=5)
    ax.axvspan(-1, 1, color="#ececec", zorder=0, lw=0)
    ax.axvline(0, color=G1, lw=0.6)
    ax.set_yticks(range(len(groups)), [GN[g] for g in reversed(groups)])
    ax.set_title(title, loc="left")
    ax.set_xlabel(xlabel)
    ax.grid(axis="y", visible=False)


def fig_r1():
    fig, ax = plt.subplots(1, 2, figsize=(FULL, 1.75), sharey=True)
    contrast_panel(ax[0], r1["statistics"], G1_ORDER, "error_rate", "interval_99_5_difference", 1e3,
                   "(a) In-domain error rate, $n=33{,}038$ test flows", r"paired contrast $d_s$ ($\times10^{-3}$)")
    contrast_panel(ax[1], r1["statistics"], G1_ORDER, "fpr", "interval_99_5_difference", 1e3,
                   "(b) Monday benign FPR, $n=494{,}940$ benign flows", r"paired contrast $d_s$ ($\times10^{-3}$)")
    ax[0].set_ylabel("removed group")
    fig.savefig(OUT / "fig_r1_contrasts.pdf"); plt.close(fig)


def fig_r4a():
    fig, ax = plt.subplots(1, 2, figsize=(FULL, 1.45), gridspec_kw={"width_ratios": [1.15, 1]})
    contrast_panel(ax[0], r4["statistics_r4a_ii"], G4_ORDER, "error_rate", "interval_98_33_difference", 1e3,
                   "(a) R4a-ii, corrected capture, $n=22{,}049$ test flows", r"paired contrast $d_s$ ($\times10^{-3}$)")
    ax[0].set_xlim(-1.08, 1.08)
    ax[0].set_xticks([-1, -0.5, 0, 0.5, 1])
    cmp = load(ROOT / "results/r4a/stats_r4a.json")["original_vs_corrected"]["groups"]
    for i, g in enumerate(G4_ORDER):
        y = len(G4_ORDER) - 1 - i
        c = cmp[g]
        o, n = c["mean_d_original"] * 1e3, c["mean_d_corrected"] * 1e3
        ax[1].plot([o, n], [y + 0.12, y - 0.12], color=G2, lw=0.8, zorder=1)
        ax[1].plot(o, y + 0.12, "o", mfc="white", mec=K, ms=4.2, mew=0.8, zorder=3, label="original (r1)" if i == 0 else None)
        ax[1].plot(n, y - 0.12, "s", color=K, ms=3.8, zorder=3, label="corrected (R4a-ii)" if i == 0 else None)
    ax[1].axvline(0, color=G1, lw=0.6)
    ax[1].set_yticks(range(3), [GN[g] for g in reversed(G4_ORDER)])
    ax[1].set_ylim(-0.6, 2.6)
    ax[1].grid(axis="y", visible=False)
    ax[1].set_title("(b) Mean contrast, original vs corrected (observational)", loc="left")
    ax[1].set_xlabel(r"mean $\bar d$ ($\times10^{-3}$)")
    ax[1].legend(frameon=False, loc="center right", handletextpad=0.3)
    fig.savefig(OUT / "fig_r4a_contrasts.pdf"); plt.close(fig)


def fig_transfer():
    views = [("full", None, "full model"), ("group", "A_flag_defects", "without A"), ("group", "B_appendix_closed", "without B"),
             ("group", "C_duplication", "without C"), ("group", "D_metadata_hypothesis", "without D"), ("group", "U_documented_union", "without U"),
             ("control", None, "random controls")]
    ri = r4["r4a_i"].values()
    fig, ax = plt.subplots(1, 2, figsize=(COL, 1.9), sharey=True, gridspec_kw={"width_ratios": [1.25, 1]})
    for j, (m, xl) in enumerate((("recall", "DDoS recall"), ("fpr", "benign FPR"))):
        for i, (k, g, _) in enumerate(views):
            vals = [r[m] for r in ri if r["kind"] == k and (g is None or r["group"] == g)]
            y = len(views) - 1 - i
            ax[j].scatter(vals, np.full(len(vals), y) + np.linspace(-0.22, 0.22, len(vals)), s=5, facecolors="none", edgecolors=G1, linewidths=0.5)
            ax[j].plot(np.mean(vals), y, "D", color=K, ms=3.2)
        ax[j].set_xlabel(xl)
        ax[j].grid(axis="y", visible=False)
    ax[0].set_xlim(-0.04, 1.04)
    ax[1].set_xlim(-0.03, 0.65)
    ax[0].set_yticks(range(len(views)), [v[2] for v in reversed(views)])
    fig.savefig(OUT / "fig_transfer.pdf"); plt.close(fig)


def fig_arr():
    arr = load(ROOT / "results/corrections/milestone2b/corrected_arr_v2.json")["variants"]
    Ks = ["2", "5", "10", "20"]
    tiers = [("all", "all registered (23)", "o", K, K), ("direct", "direct defects (16)", "s", K, "white"),
             ("shortcut", "shortcut (6)", "^", G1, G1), ("hypothesis", "hypothesis (2)", "v", G1, "white")]
    fig, ax = plt.subplots(figsize=(COL, 1.75))
    for j, (t, lab, mk, ec, fc) in enumerate(tiers):
        x = np.arange(4) + (j - 1.5) * 0.17
        lo = [min(v["methods"]["sum_abs"]["arr"][k][t] for v in arr.values()) * 100 for k in Ks]
        hi = [max(v["methods"]["sum_abs"]["arr"][k][t] for v in arr.values()) * 100 for k in Ks]
        ax.vlines(x, lo, hi, color=ec, lw=1.0)
        ax.plot(x, [(a + b) / 2 for a, b in zip(lo, hi)], mk, mec=ec, mfc=fc, ms=3.6, mew=0.7, ls="none", label=lab)
    ax.set_xticks(range(4), [f"$K={k}$" for k in Ks])
    ax.set_ylabel("ARR@$K$ (%)")
    ax.set_ylim(-3, 66)
    ax.legend(frameon=False, ncol=2, loc="upper right", columnspacing=0.8, handletextpad=0.3)
    fig.savefig(OUT / "fig_arr.pdf"); plt.close(fig)


def fig_dcnn():
    dc = load(V / "verify_dcnn.json")["seeds"]
    fig, ax = plt.subplots(1, 3, figsize=(COL, 1.45))
    for j, (m, title) in enumerate((("mcc", "MCC"), ("dos_precision", "DoS precision"), ("dos_recall", "DoS recall"))):
        for s in range(5):
            a, b = dc[str(s)]["official"][m], dc[str(s)]["dedup_model_visible"][m]
            ax[j].plot([0, 1], [a, b], color=G2, lw=0.6, zorder=1)
            ax[j].plot(0, a, "o", mfc="white", mec=K, ms=3.2, mew=0.7, zorder=2)
            ax[j].plot(1, b, "s", color=K, ms=3.0, zorder=2)
        ax[j].set_xticks([0, 1], ["official", "filtered"])
        ax[j].set_xlim(-0.35, 1.35)
        ax[j].set_title(title)
        ax[j].grid(axis="x", visible=False)
    fig.tight_layout(w_pad=0.6)
    fig.savefig(OUT / "fig_dcnn.pdf"); plt.close(fig)


def fig_mes():
    me = load(V / "verify_mes.json")["fits"]
    fig, ax = plt.subplots(1, 2, figsize=(COL, 1.6), sharey=True)
    for j, (net, title) in enumerate((("N1_unsw", "NF-UNSW-NB15-v2"), ("N2_ton", "NF-ToN-IoT-v2 subsample"))):
        for i, (model, lab, mk, fc) in enumerate((("ensemble", "ensemble", "o", K), (f"base_{net}", "own base DNN", "s", "white"))):
            for k, mode in enumerate(("random", "dup_aware")):
                vals = [me[f"{mode}_seed{s}"]["test"][f"{net}/{model}/all"]["mcc"] for s in range(5)]
                x = k + (i - 0.5) * 0.3
                ax[j].plot(np.full(5, x) + np.linspace(-0.06, 0.06, 5), vals, mk, mec=K, mfc=fc, ms=3.0, mew=0.6, ls="none",
                           label=lab if (k == 0 and j == 0) else None)
        ax[j].axhline(0, color=G1, lw=0.6)
        ax[j].set_xticks([0, 1], ["random", "duplicate-\naware"])
        ax[j].set_xlim(-0.5, 1.5)
        ax[j].set_title(title)
        ax[j].grid(axis="x", visible=False)
    ax[0].set_ylabel("MCC (5 seeds)")
    ax[0].legend(frameon=False, loc="center", handletextpad=0.2, borderaxespad=0.1, bbox_to_anchor=(0.53, 0.56), fontsize=6.0)
    fig.savefig(OUT / "fig_mes.pdf"); plt.close(fig)


def fig_errors():
    full = sorted((r for r in r1["runs"].values() if r["kind"] == "full"), key=lambda r: r["seed"])
    f4 = sorted((r for r in r4["runs_r4a_ii"].values() if r["kind"] == "full"), key=lambda r: r["seed"])
    dc = load(V / "verify_dcnn.json")["seeds"]
    fig, ax = plt.subplots(1, 2, figsize=(COL, 1.6), gridspec_kw={"width_ratios": [1.35, 1]})
    s = np.arange(10)
    w = 0.38
    ax[0].bar(s - w / 2, [r["metrics"]["fp"] for r in full], w, color="white", edgecolor=K, lw=0.6, hatch="/////", label="FP (r1)")
    ax[0].bar(s - w / 2, [r["metrics"]["fn"] for r in full], w, bottom=[r["metrics"]["fp"] for r in full], color=G2, edgecolor=K, lw=0.6, label="FN (r1)")
    ax[0].bar(s + w / 2, [r["metrics"]["fp"] for r in f4], w, color="white", edgecolor=G1, lw=0.6, hatch="....", label="FP (R4a-ii)")
    ax[0].bar(s + w / 2, [r["metrics"]["fn"] for r in f4], w, bottom=[r["metrics"]["fp"] for r in f4], color=K, edgecolor=K, lw=0.6, label="FN (R4a-ii)")
    ax[0].set_xticks(s)
    ax[0].set_xlabel("seed")
    ax[0].set_ylabel("errors (count)")
    ax[0].set_title("(a) AE-XGBoost full model")
    ax[0].legend(frameon=False, ncol=2, loc="upper center", fontsize=5.8, handlelength=1.2, columnspacing=0.6, bbox_to_anchor=(0.5, 1.02))
    ax[0].set_ylim(0, 19)
    ax[0].grid(axis="x", visible=False)
    for k, (pop, lab) in enumerate((("official", "official"), ("dedup_model_visible", "filtered"))):
        fp = float(np.mean([dc[str(i)][pop]["fp"] for i in range(5)]))
        fn = float(np.mean([dc[str(i)][pop]["fn"] for i in range(5)]))
        ax[1].bar(k - 0.17, fp, 0.32, color="white", edgecolor=K, lw=0.6, hatch="/////", label="FP" if k == 0 else None)
        ax[1].bar(k + 0.17, fn, 0.32, color=G2, edgecolor=K, lw=0.6, label="FN" if k == 0 else None)
        ax[1].text(k - 0.17, fp * 1.12, f"{fp:,.0f}", ha="center", va="bottom", fontsize=5.8)
        ax[1].text(k + 0.17, fn * 1.12, f"{fn:,.1f}", ha="center", va="bottom", fontsize=5.8)
    ax[1].set_yscale("log")
    ax[1].set_ylim(10, 2e4)
    ax[1].set_xticks([0, 1], ["official", "filtered"])
    ax[1].set_ylabel("mean errors, 5 seeds (log)")
    ax[1].set_title("(b) DCNN+SA")
    ax[1].legend(frameon=False, loc="upper right", fontsize=5.8, ncol=2, columnspacing=0.6)
    ax[1].grid(axis="x", visible=False)
    fig.tight_layout(w_pad=0.8)
    fig.savefig(OUT / "fig_errors.pdf"); plt.close(fig)


if __name__ == "__main__":
    for f in (fig_r1, fig_r4a, fig_transfer, fig_arr, fig_dcnn, fig_mes, fig_errors):
        f()
    print(sorted(p.name for p in OUT.glob("fig_*.pdf")))
