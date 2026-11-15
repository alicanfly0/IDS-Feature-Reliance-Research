"""Write the paper's result tables (LaTeX tabular bodies) from the verified Phase III records.

    .\.venv\Scripts\python.exe paper\tables\make_tables.py

Inputs (read-only):
  phase3_final_review/evidence/verification/verify_{r1,r4a,dcnn,mes}.json
  phase3_final_review/PHASE3_STATISTICAL_FINDINGS.csv
  results/r4a/stats_r4a.json
Every output file starts with a comment naming its sources. No value is typed by hand.
"""
from __future__ import annotations

import csv
import json
import statistics as st
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
V = ROOT / "phase3_final_review" / "evidence" / "verification"
OUT = Path(__file__).resolve().parent
load = lambda p: json.loads(Path(p).read_text(encoding="utf-8"))

r1, r4, dc, me = (load(V / f"verify_{k}.json") for k in ("r1", "r4a", "dcnn", "mes"))
s4 = load(ROOT / "results" / "r4a" / "stats_r4a.json")
with open(ROOT / "phase3_final_review" / "PHASE3_STATISTICAL_FINDINGS.csv", encoding="utf-8") as fh:
    findings = list(csv.DictReader(fh))

GN = {"A_flag_defects": "A", "B_appendix_closed": "B", "C_duplication": "C",
      "D_metadata_hypothesis": "D", "U_documented_union": "U"}
READ = {"difference (below SESOI or interval overlaps it)": "difference $<$ SESOI",
        "practical equivalence at the SESOI": "equivalent within margin",
        "inconclusive": "inconclusive"}


def m(x: float) -> str:
    """Signed value in units of 1e-3 with a real minus sign."""
    s = f"{x * 1e3:+.3f}"
    return s.replace("-", "$-$")


def ci(lo: float, hi: float) -> str:
    return f"[{m(lo)}, {m(hi)}]"


def rng(vals, fmt="{:.3f}", endfmt=None) -> str:
    f = lambda v, fm=fmt: fm.format(v).replace("-", "$-$")
    e = endfmt or fmt
    return f"{f(st.mean(vals))} [{f(min(vals), e)}, {f(max(vals), e)}]"


def write(name: str, header: str, lines: list[str]) -> None:
    (OUT / name).write_text(header + "\n".join(lines) + "\n", encoding="utf-8")
    print("wrote", name)


# ---------------------------------------------------------------- r1 primary family
rows = [f for f in findings if f["family"].startswith("r1 primary")]
order = ["A_flag_defects", "B_appendix_closed", "C_duplication", "D_metadata_hypothesis", "U_documented_union"]
lines = [r"\begin{tabular}{@{}llrrrllrl@{}}", r"\toprule",
         r"Group ($k$) & Endpoint & $\bar\Delta_G$ & $\bar\Delta_R$ & $\bar d$ & 99.5\% difference interval & 99\% TOST interval & $p_{\mathrm{Holm}}$ & Reading \\",
         r"\midrule"]
for g in order:
    for ep, lab in (("error_rate", "error rate"), ("fpr", "Monday FPR")):
        f = next(x for x in rows if x["group"] == g and x["endpoint"] == ep)
        assert f["difference_interval_level_pct"] == "99.5" and f["tost_interval_level_pct"] == "99"
        lines.append(f"{GN[g]} ({f['inputs_removed']}) & {lab} & {m(float(f['mean_delta_group']))} & {m(float(f['mean_delta_control']))} & "
                     f"{m(float(f['mean_d']))} & {ci(float(f['difference_interval_lo']), float(f['difference_interval_hi']))} & "
                     f"{ci(float(f['tost_lo']), float(f['tost_hi']))} & {float(f['p_holm']):.3f} & {READ[f['reading_preregistered']]} \\\\")
lines += [r"\bottomrule", r"\end{tabular}"]
write("tab_r1.tex", "% Source: phase3_final_review/PHASE3_STATISTICAL_FINDINGS.csv (= results/milestone3b/stats_r1.json). Units 1e-3.\n", lines)

# ---------------------------------------------------------------- R4a-ii and original vs corrected
rows = [f for f in findings if f["family"].startswith("R4a-ii primary")]
cmp = s4["original_vs_corrected"]["groups"]
st4 = r4["statistics_r4a_ii"]
lines = [r"\begin{tabular}{@{}lrll r@{}}", r"\toprule",
         r"\multicolumn{5}{@{}l}{(a) R4a-ii: corrected capture, $n=22{,}049$, Holm over 3 tests} \\",
         r"\midrule",
         r"Group ($k$) & $\bar d'$ & 98.33\% difference & 96.67\% TOST & $p_{\mathrm{Holm}}$ \\",
         r"\midrule"]
for g in ("A_flag_defects", "B_appendix_closed", "U_documented_union"):
    f = next(x for x in rows if x["group"] == g)
    assert f["difference_interval_level_pct"] == "98.33" and f["tost_interval_level_pct"] == "96.67"
    lines.append(f"{GN[g]} ({f['inputs_removed']}) & {m(float(f['mean_d']))} & {ci(float(f['difference_interval_lo']), float(f['difference_interval_hi']))} & "
                 f"{ci(float(f['tost_lo']), float(f['tost_hi']))} & {float(f['p_holm']):.3f} \\\\")
lines += [r"\midrule",
          r"\multicolumn{5}{@{}l}{(b) Original vs corrected, observational (no row pairing)} \\",
          r"\midrule",
          r"Group & $\bar d$ (r1) & $\bar d'$ (R4a-ii) & \multicolumn{2}{l}{$\bar d'-\bar d$ [Welch 95\%]} \\",
          r"\midrule"]
for g in ("A_flag_defects", "B_appendix_closed", "U_documented_union"):
    c = cmp[g]
    cm = c["corrected_minus_original"]
    lines.append(f"{GN[g]} & {m(c['mean_d_original'])} & {m(c['mean_d_corrected'])} & \\multicolumn{{2}}{{l}}{{{m(cm['difference'])} {ci(*cm['interval'])}}} \\\\")
lines += [r"\bottomrule", r"\end{tabular}"]
write("tab_r4a.tex", "% Source: PHASE3_STATISTICAL_FINDINGS.csv (R4a-ii rows = results/r4a/stats_r4a.json); "
      "results/r4a/stats_r4a.json original_vs_corrected. Units 1e-3.\n", lines)

# ---------------------------------------------------------------- R4a-i transfer
ri = list(r4["r4a_i"].values())
views = [("full", None, "Full model"), ("group", "A_flag_defects", "Without A"), ("group", "B_appendix_closed", "Without B"),
         ("group", "C_duplication", "Without C"), ("group", "D_metadata_hypothesis", "Without D"),
         ("group", "U_documented_union", "Without U"), ("control", None, "Random controls (50)")]
lines = [r"\begin{tabular}{@{}lllr@{}}", r"\toprule", r"r1 view & DDoS recall & Benign FPR & MCC \\", r"\midrule"]
for kind, g, lab in views:
    sel = [x for x in ri if x["kind"] == kind and (g is None or x["group"] == g)]
    lines.append(f"{lab} & {rng([x['recall'] for x in sel])} & {rng([x['fpr'] for x in sel])} & "
                 f"{st.mean(x['mcc'] for x in sel):.3f}".replace("-", "$-$") + r" \\")
lines += [r"\bottomrule", r"\end{tabular}"]
write("tab_transfer.tex", "% Source: phase3_final_review/evidence/verification/verify_r4a.json -> r4a_i (110 r1 models on 22,049 corrected rows). Mean [min, max] over 10 models per view.\n", lines)

# ---------------------------------------------------------------- full models r1 vs R4a-ii
f1 = [x for x in r1["runs"].values() if x["kind"] == "full"]
f4 = [x for x in r4["runs_r4a_ii"].values() if x["kind"] == "full"]
def col(runs, key, fmt="{:.6f}"):
    count = key in ("errors", "fp", "fn")
    return rng([x["metrics"][key] for x in runs], fmt, "{:.0f}" if count else None)
def spec(runs):
    return rng([1 - x["metrics"]["fpr"] for x in runs], "{:.6f}")
lines = [r"\begin{tabular}{@{}lll@{}}", r"\toprule",
         r"Metric & Original (r1), $T^\star$ & Corrected (R4a-ii), $T'^\star$ \\", r"\midrule",
         f"Test flows (DDoS) & {f1[0]['metrics']['n']:,} ({f1[0]['metrics']['n_pos']:,}) & {f4[0]['metrics']['n']:,} ({f4[0]['metrics']['tp'] + f4[0]['metrics']['fn']:,}) \\\\",
         f"Errors & {col(f1, 'errors', '{:.1f}')} & {col(f4, 'errors', '{:.1f}')} \\\\",
         f"False positives & {col(f1, 'fp', '{:.1f}')} & {col(f4, 'fp', '{:.1f}')} \\\\",
         f"False negatives & {col(f1, 'fn', '{:.1f}')} & {col(f4, 'fn', '{:.1f}')} \\\\",
         f"Accuracy & {col(f1, 'accuracy')} & {col(f4, 'accuracy')} \\\\",
         f"DDoS recall & {col(f1, 'recall')} & {col(f4, 'recall')} \\\\",
         f"Benign recall & {spec(f1)} & {spec(f4)} \\\\",
         f"F1 (DDoS) & {col(f1, 'f1')} & {col(f4, 'f1')} \\\\",
         f"MCC & {col(f1, 'mcc')} & {col(f4, 'mcc')} \\\\",
         f"AUROC & {col(f1, 'auroc')} & {col(f4, 'auroc')} \\\\",
         r"\bottomrule", r"\end{tabular}"]
write("tab_full.tex", "% Source: verify_r1.json runs r1_full_s0..9; verify_r4a.json runs_r4a_ii r4a_full_s0..9. Mean [min, max] over 10 seeds.\n", lines)

# ---------------------------------------------------------------- DCNN
seeds = [dc["seeds"][str(s)] for s in range(5)]
def dcol(pop, key, fmt="{:.3f}"):
    return rng([x[pop][key] for x in seeds], fmt)
lines = [r"\begin{tabular}{@{}lll@{}}", r"\toprule",
         f"Metric & Official ({dc['rows']['test']:,}) & Filtered ({dc['populations']['model_visible']['kept_rows']:,}) \\\\", r"\midrule",
         f"Errors & {dcol('official', 'errors', '{:,.0f}')} & {dcol('dedup_model_visible', 'errors', '{:,.0f}')} \\\\",
         f"False negatives & {dcol('official', 'fn', '{:.0f}')} & {dcol('dedup_model_visible', 'fn', '{:.0f}')} \\\\",
         f"MCC & {dcol('official', 'mcc')} & {dcol('dedup_model_visible', 'mcc')} \\\\",
         f"DoS recall & {dcol('official', 'dos_recall')} & {dcol('dedup_model_visible', 'dos_recall')} \\\\",
         f"DoS precision & {dcol('official', 'dos_precision')} & {dcol('dedup_model_visible', 'dos_precision')} \\\\",
         f"Normal-class FPR & {dcol('official', 'fpr')} & {dcol('dedup_model_visible', 'fpr')} \\\\",
         f"AUROC & {dcol('official', 'roc_auc')} & {dcol('dedup_model_visible', 'roc_auc')} \\\\",
         r"\bottomrule", r"\end{tabular}"]
write("tab_dcnn.tex", "% Source: phase3_final_review/evidence/verification/verify_dcnn.json seeds 0-4. Mean [min, max]; errors and FN mean rounded to integers.\n", lines)

# ---------------------------------------------------------------- MES-DNN
fits = me["fits"]
def mcol(mode, key, metric="mcc"):
    return rng([fits[f"{mode}_seed{s}"]["test"][key][metric] for s in range(5)])
lines = [r"\begin{tabular}{@{}lll@{}}", r"\toprule", r"Model, split & N1: NF-UNSW-NB15-v2 & N2: NF-ToN-IoT-v2 \\", r"\midrule"]
for lab, mode, kind in (("Own base, random", "random", "own"), ("Own base, dup.-aware", "dup_aware", "own"),
                        ("Other base, random", "random", "other"), ("Other base, dup.-aware", "dup_aware", "other"),
                        ("Ensemble, random", "random", "ens"), ("Ensemble, dup.-aware", "dup_aware", "ens")):
    key = {"own": ("N1_unsw/base_N1_unsw/all", "N2_ton/base_N2_ton/all"),
           "other": ("N1_unsw/base_N2_ton/all", "N2_ton/base_N1_unsw/all"),
           "ens": ("N1_unsw/ensemble/all", "N2_ton/ensemble/all")}[kind]
    lines.append(f"{lab} & {mcol(mode, key[0])} & {mcol(mode, key[1])} \\\\")
lines += [r"\bottomrule", r"\end{tabular}"]
write("tab_mes.tex", "% Source: phase3_final_review/evidence/verification/verify_mes.json fits {random,dup_aware}_seed0-4, population 'all' (645,374 test rows per network). MCC mean [min, max].\n", lines)

# ---------------------------------------------------------------- appendix: per-seed full models
r4full = {x["seed"]: x for x in f4}
lines = [r"\begin{tabular}{@{}r rrrr r rrrr@{}}", r"\toprule",
         r" & \multicolumn{5}{c}{Original (r1), $T^\star$ and Monday} & \multicolumn{4}{c}{Corrected (R4a-ii), $T'^\star$} \\",
         r"\cmidrule(lr){2-6}\cmidrule(l){7-10}",
         r"Seed & TN & FP & FN & TP & Mon.\ FP & TN & FP & FN & TP \\", r"\midrule"]
for x in sorted(f1, key=lambda r: r["seed"]):
    a, b = x["metrics"], r4full[x["seed"]]["metrics"]
    lines.append(f"{x['seed']} & {a['tn']:,} & {a['fp']} & {a['fn']} & {a['tp']:,} & {x['monday']['fp']} & "
                 f"{b['tn']:,} & {b['fp']} & {b['fn']} & {b['tp']:,} \\\\")
lines += [r"\bottomrule", r"\end{tabular}"]
write("tab_seeds.tex", "% Source: verify_r1.json runs r1_full_s* (metrics, monday); verify_r4a.json runs_r4a_ii r4a_full_s*.\n", lines)
