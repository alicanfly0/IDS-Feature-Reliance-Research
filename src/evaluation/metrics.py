"""Binary classification metrics with an explicit positive class (1 = attack)."""
from __future__ import annotations

import numpy as np
from sklearn import metrics as skm


def binary_metrics(y_true, prob_positive, threshold: float = 0.5) -> dict:
    """Threshold is fixed in advance (not tuned on the evaluated partition)."""
    y_true = np.asarray(y_true).astype(int)
    prob = np.asarray(prob_positive, dtype=float)
    if not np.isfinite(prob).all():
        raise ValueError("non-finite predicted probabilities")
    pred = (prob >= threshold).astype(int)
    tn, fp, fn, tp = skm.confusion_matrix(y_true, pred, labels=[0, 1]).ravel()
    both_classes = len(np.unique(y_true)) == 2
    return {
        "n": int(len(y_true)),
        "class_counts": {"negative_0": int((y_true == 0).sum()), "positive_1": int((y_true == 1).sum())},
        "threshold": threshold,
        "confusion_matrix": {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)},
        "accuracy": float(skm.accuracy_score(y_true, pred)),
        "precision": float(skm.precision_score(y_true, pred, pos_label=1, zero_division=0)),
        "recall": float(skm.recall_score(y_true, pred, pos_label=1, zero_division=0)),
        "f1": float(skm.f1_score(y_true, pred, pos_label=1, zero_division=0)),
        "macro_f1": float(skm.f1_score(y_true, pred, average="macro", labels=[0, 1], zero_division=0)),
        "auroc": float(skm.roc_auc_score(y_true, prob)) if both_classes else None,
        "mcc": float(skm.matthews_corrcoef(y_true, pred)),
    }
