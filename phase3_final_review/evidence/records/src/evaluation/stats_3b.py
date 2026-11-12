"""Milestone 3B statistics (protocol r1, PROPOSED). Pure NumPy; no model code.

ORIENTATION (all endpoints are "lower is better": error rate, FPR, log loss)
    removal effect   Δ_x,s = metric(model without x, seed s) − metric(full model, seed s)
                     > 0  removing x made the model WORSE (more errors / false positives)
    contrast         d_s   = Δ_group,s − Δ_control(draw s),s
                     > 0  removing the group hurt MORE than removing a random size-matched control
                     < 0  removing the group hurt LESS (or helped more) than the control
Intervals, tables and figures use this orientation unchanged.

ASSUMPTIONS of the sign-flip test (docs/MILESTONE_3B0_READINESS.md §1)
- Pairs s = 0..9 are independent given the fixed evaluation rows (separate training seeds and
  independent control draws; the shared test set makes every inference CONDITIONAL on it).
- Exactness holds under the SHARP null that, within each pair, the group and the control draw are
  exchangeable (the group behaves like one more random draw), so d_s is symmetric about 0.
- For the weaker null "equal mean effect" with unequal spread or skew, the test is only
  approximate; the t-interval is then the sensitivity analysis.
- Zero contrasts (ties, common with tiny error counts) carry no sign information; they are kept in
  the mean but reduce the attainable p-value to 2 / 2^(number of non-zero d_s).
"""
from __future__ import annotations

import itertools
import math

import numpy as np

LOWER_IS_BETTER = ("error_rate", "fpr", "log_loss")


def removal_effect(ablated: float, full: float) -> float:
    """Δ = ablated − full for lower-is-better metrics (> 0: removal worsened the model)."""
    return float(ablated) - float(full)


def contrasts(group_effects, control_effects) -> np.ndarray:
    g, c = np.asarray(group_effects, float), np.asarray(control_effects, float)
    if g.shape != c.shape or g.ndim != 1:
        raise ValueError("group and control effects must be paired 1-D arrays (one per seed/draw pair)")
    if not (np.isfinite(g).all() and np.isfinite(c).all()):
        raise ValueError("non-finite effect")
    return g - c


def sign_flip_test(d, tol: float = 1e-12) -> dict:
    """Exact two-sided sign-flip (randomization) test of mean(d) = 0 under the sharp null."""
    d = np.asarray(d, float)
    nz = d[np.abs(d) > tol]
    m = len(nz)
    observed = abs(d.sum())
    if m == 0:
        return {"p": 1.0, "n": len(d), "n_nonzero": 0, "min_attainable_p": 1.0, "mean": float(d.mean())}
    count = 0
    for signs in itertools.product((1.0, -1.0), repeat=m):
        if abs(float(np.dot(signs, nz))) >= observed - tol:
            count += 1
    return {"p": count / 2 ** m, "n": len(d), "n_nonzero": m, "min_attainable_p": min(1.0, 2 / 2 ** m),
            "mean": float(d.mean())}


def t_interval(d, level: float) -> tuple[float, float]:
    """Student-t interval for the mean of paired contrasts (sensitivity; assumes near-normal d)."""
    from scipy import stats
    d = np.asarray(d, float)
    n = len(d)
    if n < 2:
        raise ValueError("need at least two paired units")
    se = d.std(ddof=1) / math.sqrt(n)
    q = stats.t.ppf(0.5 + level / 2, n - 1)
    return float(d.mean() - q * se), float(d.mean() + q * se)


def holm(pvalues: dict[str, float], alpha: float = 0.05) -> dict[str, dict]:
    """Holm step-down; returns adjusted p and rejection per hypothesis (keys sorted for determinism)."""
    items = sorted(pvalues.items(), key=lambda kv: (kv[1], kv[0]))
    m, out, running, stop = len(items), {}, 0.0, False
    for i, (k, p) in enumerate(items):
        adj = min(1.0, max(running, (m - i) * p))
        running = adj
        reject = (not stop) and p <= alpha / (m - i)
        stop = stop or not reject
        out[k] = {"p": p, "p_holm": adj, "reject": reject, "threshold": alpha / (m - i)}
    return dict(sorted(out.items()))


def reading(d, sesoi: float, family_size: int = 10, alpha: float = 0.05, holm_reject: bool | None = None) -> dict:
    """Pre-registered three-way reading (resolution doc §4.4, corrected orientation).

    holm_reject comes from `holm` over the whole primary family. Intervals are t-based at the
    Bonferroni-consistent level 1 - alpha/family_size (difference) and 1 - 2*alpha/family_size (TOST).
    """
    d = np.asarray(d, float)
    sf = sign_flip_test(d)
    lo, hi = t_interval(d, 1 - alpha / family_size)
    elo, ehi = t_interval(d, 1 - 2 * alpha / family_size)
    testable = sf["min_attainable_p"] <= alpha / family_size
    if holm_reject and (lo > sesoi or hi < -sesoi):
        label = "practically relevant difference"
    elif holm_reject:
        label = "difference (below SESOI or interval overlaps it)"
    elif -sesoi < elo and ehi < sesoi:
        label = "practical equivalence at the SESOI"
    else:
        label = "inconclusive"
    direction = "group removal hurts more than control" if d.mean() > 0 else (
        "group removal hurts less than control" if d.mean() < 0 else "no mean difference")
    return {"mean_contrast": float(d.mean()), "direction": direction, "sign_flip": sf,
            "exact_test_can_reach_holm_threshold": testable,
            "interval_difference": [lo, hi], "interval_equivalence": [elo, ehi], "sesoi": sesoi, "reading": label}


def clopper_pearson(k: int, n: int, level: float = 0.95) -> tuple[float, float]:
    from scipy import stats
    if n <= 0 or not 0 <= k <= n:
        raise ValueError("need 0 <= k <= n and n > 0")
    a = 1 - level
    lo = 0.0 if k == 0 else float(stats.beta.ppf(a / 2, k, n - k + 1))
    hi = 1.0 if k == n else float(stats.beta.ppf(1 - a / 2, k + 1, n - k))
    return lo, hi


def cluster_bootstrap_diff(err_a, err_b, clusters, n_boot: int = 2000, seed: int = 0, level: float = 0.95) -> dict:
    """Paired bootstrap of mean(err_a) - mean(err_b) resampling whole clusters (content groups or
    time blocks). Row-sampling uncertainty only, conditional on the trained models. Reports how many
    distinct replicate values occurred so very low error counts are visible."""
    a, b = np.asarray(err_a, float), np.asarray(err_b, float)
    cl = np.asarray(clusters)
    if not (a.shape == b.shape == cl.shape):
        raise ValueError("paired arrays and clusters must align")
    ids, inv = np.unique(cl, return_inverse=True)
    sum_d = np.bincount(inv, weights=a - b, minlength=len(ids))
    size = np.bincount(inv, minlength=len(ids)).astype(float)
    rng = np.random.RandomState(seed)
    reps = np.empty(n_boot)
    for i in range(n_boot):
        pick = rng.randint(0, len(ids), len(ids))
        w = np.bincount(pick, minlength=len(ids))
        reps[i] = (w * sum_d).sum() / (w * size).sum()
    q = (1 - level) / 2
    return {"estimate": float((a - b).mean()), "interval": [float(np.quantile(reps, q)), float(np.quantile(reps, 1 - q))],
            "distinct_replicates": int(len(np.unique(np.round(reps, 12)))), "n_clusters": int(len(ids)),
            "n_boot": n_boot, "seed": seed, "conditional_on": "trained models and this capture"}
