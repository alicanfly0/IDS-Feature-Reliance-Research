"""ARR@K (Phase II, Step 5): share of Top-K attribution mass held by registered artifact features.

    ARR@K = sum_{j in TopK ∩ A} I_j / sum_{j in TopK} I_j,   I_j = mean |SHAP_j|

An attribution indicator only: a high value says the explanation concentrates on registered
features, not that the model causally depends on them or that they are artifacts here.
"""
from __future__ import annotations

import math

import numpy as np


def importance_from_arrays(values, columns, merges=None, aggregation="sum_abs") -> dict[str, float]:
    """Aggregate existing SHAP arrays, with explicit duplicate handling.

    sum_abs = sum individual mean absolute contributions (historical convention).
    signed = mean absolute row-wise signed sum (net contribution of the group).
    Neither constitutes joint-mask/group Shapley values.
    """
    values = np.asarray(values, dtype=np.float64)
    if values.ndim != 2 or values.shape[1] != len(columns) or not len(values):
        raise ValueError("SHAP shape must be nonempty rows x columns")
    if len(set(columns)) != len(columns) or not np.isfinite(values).all():
        raise ValueError("columns must be unique and SHAP values finite")
    if aggregation not in ("sum_abs", "signed"):
        raise ValueError("unknown aggregation")
    merges = merges or {}
    groups = {}
    for i, col in enumerate(columns):
        groups.setdefault(merges.get(col, col), []).append(i)
    return {name: float(np.abs(values[:, inds]).mean(axis=0).sum()) if aggregation == "sum_abs"
            else float(np.abs(values[:, inds].sum(axis=1)).mean()) for name, inds in groups.items()}


def merge_columns(importance: dict[str, float], merges: dict[str, str]) -> dict[str, float]:
    """Sum the importance of columns that are copies of another (e.g. 'Fwd Header Length.1')."""
    out: dict[str, float] = {}
    for col, value in importance.items():
        target = merges.get(col, col)
        out[target] = out.get(target, 0.0) + float(value)
    return out


def top_k(importance: dict[str, float], k: int) -> list[str]:
    """Top-K by importance; ties broken by name so the ranking is deterministic."""
    return [c for c, _ in sorted(importance.items(), key=lambda kv: (-kv[1], kv[0]))[:k]]


def arr_at_k(importance: dict[str, float], artifact_set: set[str], k: int) -> float:
    """NaN when the Top-K importance sums to zero (no attribution mass to share)."""
    if k < 1:
        raise ValueError("k must be >= 1")
    if any(v < 0 or not math.isfinite(v) for v in importance.values()):
        raise ValueError("importances must be finite and non-negative (use mean |SHAP|)")
    top = top_k(importance, k)
    denom = sum(importance[c] for c in top)
    if denom == 0:
        return float("nan")
    return sum(importance[c] for c in top if c in artifact_set) / denom


def arr_table(importance: dict[str, float], tiers: dict[str, set[str]], ks=(2, 5, 10, 20)) -> dict:
    """ARR@K for each registry tier and K, plus which registered columns are in each Top-K."""
    out = {}
    for k in ks:
        top = top_k(importance, k)
        out[k] = {"top_k": top, **{tier: arr_at_k(importance, cols, k) for tier, cols in tiers.items()},
                  **{f"{tier}_in_top_k": [c for c in top if c in cols] for tier, cols in tiers.items()}}
    return out
