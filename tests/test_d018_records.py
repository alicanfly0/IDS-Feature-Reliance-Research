"""D-018 records: the committed paired file reproduces the committed comparison (no data needed);
where the Git-ignored run folders exist, their artifacts still match the recorded checksums."""
import hashlib
import json

import pandas as pd
import pytest
from sklearn.metrics import confusion_matrix, f1_score, matthews_corrcoef, roc_auc_score

from src.config import ROOT
from src.experiments.compare_ablation import mcnemar_exact

STEM = ROOT / "results" / "comparisons" / "ae_xgb_d008_trackB_noDstPort-seed0-cpu-3054b399-vs-full"
COMPARISON = json.loads(STEM.with_name(STEM.name + ".json").read_text(encoding="utf-8"))
VERIFICATION = json.loads(STEM.with_name(STEM.name + ".verification.json").read_text(encoding="utf-8"))
PAIRED = pd.read_csv(STEM.with_name(STEM.name + ".paired_test.csv.gz"))


def test_paired_file_reproduces_metrics_and_mcnemar():
    assert len(PAIRED) == 33486 and PAIRED.source_row.is_unique
    assert PAIRED.y_true.value_counts().to_dict() == {1: 19233, 0: 14253}
    for side, key in (("full", "full_on_common"), ("ablated", "ablated_on_common")):
        y, pred, prob = PAIRED.y_true, PAIRED[f"y_pred_{side}"], PAIRED[f"prob_ddos_{side}"]
        assert ((prob >= 0.5).astype(int) == pred).all()
        tn, fp, fn, tp = confusion_matrix(y, pred, labels=[0, 1]).ravel()
        assert COMPARISON[key]["confusion_matrix"] == {"tn": tn, "fp": fp, "fn": fn, "tp": tp}
        assert COMPARISON[key]["f1"] == pytest.approx(f1_score(y, pred), abs=1e-12)
        assert COMPARISON[key]["mcc"] == pytest.approx(matthews_corrcoef(y, pred), abs=1e-12)
        assert COMPARISON[key]["auroc"] == pytest.approx(roc_auc_score(y, prob), abs=1e-12)
    assert round(COMPARISON["full_on_common"]["f1"], 6) == 0.999870
    assert round(COMPARISON["full_on_common"]["mcc"], 6) == 0.999695
    assert round(COMPARISON["ablated_on_common"]["f1"], 6) == 0.999818
    assert round(COMPARISON["ablated_on_common"]["mcc"], 6) == 0.999572
    ok_f, ok_a = PAIRED.y_pred_full == PAIRED.y_true, PAIRED.y_pred_ablated == PAIRED.y_true
    b, c = int((ok_f & ~ok_a).sum()), int((~ok_f & ok_a).sum())
    assert (b, c) == (3, 1) and mcnemar_exact(b, c) == COMPARISON["paired"]["mcnemar_exact_p"] == 0.625


def test_exclusion_record_is_consistent():
    ex = pd.DataFrame(VERIFICATION["excluded_rows"])
    assert (ex.partition == "val").sum() == 357 and (ex.partition == "test").sum() == 391
    assert set(ex.label) == {"BENIGN"}
    assert ex[ex.partition == "test"].reason.value_counts().to_dict() == {
        "twin_of_train": 228, "twin_of_train_and_val": 136, "twin_of_val": 27}
    assert not set(ex[ex.partition == "test"].source_row) & set(PAIRED.source_row)   # excluded rows not scored
    assert VERIFICATION["overlap_after_exclusion_77_features"] == {"train_val": 0, "train_test": 0, "val_test": 0}


RUN_FILES = VERIFICATION["artifact_sha256"]


@pytest.mark.skipif(not all((ROOT / p).is_file() for p in RUN_FILES), reason="local run folders not present")
def test_run_artifacts_unchanged():
    changed = [p for p, h in RUN_FILES.items() if hashlib.sha256((ROOT / p).read_bytes()).hexdigest() != h]
    assert changed == []
