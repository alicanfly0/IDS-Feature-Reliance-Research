"""Fang DCNN + self-attention on UNSW-NB15, Normal vs DoS (D-009). An adaptation, not a reproduction.

Protocol (approved D-009; adaptations are listed in docs/DCNN_FANG_ADAPTATION.md):
  data        official UNSW_NB15_training-set / testing-set (manifest-verified), rows with attack_cat
              Normal or DoS only; DoS = 1 (the paper treats Normal as the positive class; both
              class-conditional views are reported).
  preprocess  fitted on the training partition only, as the authors' data_utils.py: drop id and
              attack_cat; numeric -> median impute -> winsorise at the train 1st/99th percentiles ->
              MinMax; categorical -> "Unknown" fill -> one-hot (unknown ignored).
  selection   LightGBM (authors' shap_sort.py settings, random_state 42) + SHAP TreeExplainer on the
              training partition; features ranked by mean |SHAP|; K = 22 as approved (the 95 %
              cumulative rule's count is recorded too). Seed-independent, frozen in selection.json.
  training    per seed 0-4: stratified 80/20 fit/validation split (random_state = seed), balanced
              class weights from the fit split, 50 epochs, batch 128, EarlyStopping(val_loss, 10,
              best weights restored), ReduceLROnPlateau(val_loss, 0.1, 5, min_lr 1e-6).
  evaluation  every model scored on (a) the official test rows and (b) the duplicate-filtered test
              rows: test rows whose model-visible float32 input equals any training-partition row are
              removed. A raw-feature duplicate filter is reported as a sensitivity population.

  python -m src.experiments.dcnn_fang select [--check]
  python -m src.experiments.dcnn_fang run --seeds 0 1 2 3 4 [--device cpu]
  python -m src.experiments.dcnn_fang summary
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from src.data.acquire import check_file
from src.data.manifest import ROOT, load_manifest

DATASET_ID = "unsw_nb15"
FILES = {"train": "UNSW_NB15_training-set.csv", "test": "UNSW_NB15_testing-set.csv"}
CLASSES = {"Normal": 0, "DoS": 1}
CATEGORICAL = ["proto", "service", "state"]
DROP = ["id", "attack_cat", "label"]
K = 22
OUT = ROOT / "results/dcnn_fang"
LGBM_PARAMS = dict(n_estimators=300, learning_rate=0.05, max_depth=-1, num_leaves=31, subsample=0.8,
                   colsample_bytree=0.8, objective="binary", random_state=42, verbose=-1)
TRAIN = dict(epochs=50, batch_size=128, lr=5e-4, val_fraction=0.2, es_patience=10, lr_patience=5,
             lr_factor=0.1, min_lr=1e-6, threshold=0.5)


# ------------------------------------------------------------------ data and preprocessing
def load_partition(name: str, root: Path = ROOT) -> pd.DataFrame:
    ds = load_manifest()["datasets"][DATASET_ID]
    entry = {f["name"]: f for f in ds["files"]}[FILES[name]]
    path = root / ds["local_dir"] / FILES[name]
    problems = check_file(path, entry)
    if problems:
        raise RuntimeError(f"{path.name} failed verification: {problems}")
    df = pd.read_csv(path, encoding="utf-8-sig", low_memory=False)
    df = df[df["attack_cat"].isin(CLASSES)].reset_index(drop=True)
    mapped = df["attack_cat"].map(CLASSES)
    if not (mapped == df["label"]).all():
        raise RuntimeError(f"{name}: attack_cat and label disagree")
    return df


@dataclass
class Preprocessor:
    numeric: list
    categorical: list
    median: np.ndarray
    lo: np.ndarray
    hi: np.ndarray
    vmin: np.ndarray
    vmax: np.ndarray
    categories: dict

    @classmethod
    def fit(cls, df: pd.DataFrame) -> "Preprocessor":
        feats = [c for c in df.columns if c not in DROP]
        cat = [c for c in feats if c in CATEGORICAL]
        num = [c for c in feats if c not in CATEGORICAL]
        x = df[num].to_numpy(np.float64)
        med = np.nanmedian(x, axis=0)
        x = np.where(np.isnan(x), med, x)
        lo, hi = np.percentile(x, 1, axis=0), np.percentile(x, 99, axis=0)
        x = np.clip(x, lo, hi)
        cats = {c: sorted(df[c].fillna("Unknown").astype(str).unique()) for c in cat}
        return cls(num, cat, med, lo, hi, x.min(axis=0), x.max(axis=0), cats)

    @property
    def feature_names(self) -> list:
        return self.numeric + [f"{c}_{v}" for c in self.categorical for v in self.categories[c]]

    def transform(self, df: pd.DataFrame) -> np.ndarray:
        x = df[self.numeric].to_numpy(np.float64)
        x = np.where(np.isnan(x), self.median, x)
        x = np.clip(x, self.lo, self.hi)
        span = self.vmax - self.vmin
        x = (x - self.vmin) / np.where(span == 0, 1.0, span)     # sklearn MinMaxScaler: zero span -> 0
        parts = [x]
        for c in self.categorical:
            v = df[c].fillna("Unknown").astype(str).to_numpy()
            parts.append((v[:, None] == np.array(self.categories[c])[None, :]).astype(np.float64))
        return np.hstack(parts)

    def record(self) -> dict:
        return {"numeric": self.numeric, "categorical": self.categorical, "categories": self.categories,
                "n_transformed": len(self.feature_names)}


def _sha(a) -> str:
    return hashlib.sha256(np.ascontiguousarray(a).tobytes()).hexdigest()


def prepare(root: Path = ROOT) -> dict:
    tr, te = load_partition("train", root), load_partition("test", root)
    pre = Preprocessor.fit(tr)
    return {"train": tr, "test": te, "pre": pre, "Xtr": pre.transform(tr), "Xte": pre.transform(te),
            "ytr": tr["label"].to_numpy(np.int64), "yte": te["label"].to_numpy(np.int64)}


# ------------------------------------------------------------------ SHAP feature selection
def select_features(Xtr: np.ndarray, ytr: np.ndarray, names: list, k: int = K) -> dict:
    import lightgbm
    import shap
    model = lightgbm.LGBMClassifier(**LGBM_PARAMS).fit(pd.DataFrame(Xtr, columns=names), ytr)
    sv = shap.TreeExplainer(model).shap_values(pd.DataFrame(Xtr, columns=names))
    if isinstance(sv, list):
        sv = sv[1]
    sv = np.asarray(sv)
    if sv.ndim == 3:
        sv = sv[:, :, 1]
    imp = np.abs(sv).mean(axis=0)
    order = np.argsort(-imp, kind="stable")
    cum = np.cumsum(imp[order]) / imp.sum()
    rule95 = int(np.searchsorted(cum, 0.95) + 1)
    return {"k": k, "selected": [names[i] for i in order[:k]], "selected_index": [int(i) for i in order[:k]],
            "rule95_count": rule95, "cumulative_share_at_k": float(cum[k - 1]),
            "ranking": [{"feature": names[i], "mean_abs_shap": float(imp[i])} for i in order],
            "lgbm_params": LGBM_PARAMS}


# ------------------------------------------------------------------ duplicate-filtered population
def _row_keys(a: np.ndarray) -> np.ndarray:
    """Exact byte image of each row (no hashing, so no collisions)."""
    a = np.ascontiguousarray(a)
    return np.array([r.tobytes() for r in a], dtype=object)


def duplicate_population(d: dict, sel_idx: list) -> dict:
    """Test rows whose input matches any training-partition row are excluded (model-visible = primary)."""
    out = {}
    mv_tr = d["Xtr"][:, sel_idx].astype(np.float32)
    mv_te = d["Xte"][:, sel_idx].astype(np.float32)
    raw_cols = [c for c in d["train"].columns if c not in DROP]
    raw = lambda df: np.array(["\x1f".join(map(repr, r)) for r in df[raw_cols].itertuples(index=False)], dtype=object)
    for name, (ktr, kte) in {"model_visible": (_row_keys(mv_tr), _row_keys(mv_te)),
                             "raw_features": (raw(d["train"]), raw(d["test"]))}.items():
        labels: dict = {}
        for k, yv in zip(ktr, d["ytr"]):
            labels.setdefault(k, set()).add(int(yv))
        dup = np.array([k in labels for k in kte])
        conflict = np.array([k in labels and labels[k] != {int(yv)} for k, yv in zip(kte, d["yte"])])
        out[name] = {"excluded_rows": int(dup.sum()), "kept_rows": int((~dup).sum()),
                     "excluded_by_class": {c: int((dup & (d["yte"] == v)).sum()) for c, v in CLASSES.items()},
                     "kept_by_class": {c: int((~dup & (d["yte"] == v)).sum()) for c, v in CLASSES.items()},
                     "excluded_with_label_conflict": int(conflict.sum()),
                     "kept_mask_sha256": _sha(~dup), "_mask": ~dup}
    return out


# ------------------------------------------------------------------ metrics
def metrics(y: np.ndarray, p: np.ndarray, thr: float = TRAIN["threshold"]) -> dict:
    from sklearn.metrics import average_precision_score, matthews_corrcoef, roc_auc_score
    pred = (p >= thr).astype(int)
    tp = int(((pred == 1) & (y == 1)).sum()); tn = int(((pred == 0) & (y == 0)).sum())
    fp = int(((pred == 1) & (y == 0)).sum()); fn = int(((pred == 0) & (y == 1)).sum())
    div = lambda a, b: float(a / b) if b else float("nan")
    out = {"n": int(len(y)), "n_dos": int(y.sum()), "n_normal": int((y == 0).sum()),
           "tp": tp, "tn": tn, "fp": fp, "fn": fn, "errors": fp + fn,
           "accuracy": div(tp + tn, len(y)), "dos_precision": div(tp, tp + fp), "dos_recall": div(tp, tp + fn),
           "normal_precision": div(tn, tn + fn), "normal_recall_specificity": div(tn, tn + fp),
           "fpr": div(fp, fp + tn), "mcc": float(matthews_corrcoef(y, pred))}
    out["dos_f1"] = div(2 * tp, 2 * tp + fp + fn)
    out["normal_f1"] = div(2 * tn, 2 * tn + fn + fp)
    out["balanced_accuracy"] = (out["dos_recall"] + out["normal_recall_specificity"]) / 2
    if 0 < y.sum() < len(y):
        out["roc_auc"] = float(roc_auc_score(y, p))
        out["pr_auc_dos"] = float(average_precision_score(y, p))
    return out


# ------------------------------------------------------------------ training
def train_seed(seed: int, X: np.ndarray, y: np.ndarray, device: str = "cpu", hp: dict = TRAIN,
               log=print) -> tuple:
    import torch
    from sklearn.model_selection import train_test_split
    from sklearn.utils.class_weight import compute_class_weight

    from src.env import set_seeds
    from src.models.dcnn import DCNNSA

    set_seeds(seed)
    torch.use_deterministic_algorithms(True)
    idx = np.arange(len(y))
    fit, val = train_test_split(idx, test_size=hp["val_fraction"], stratify=y, random_state=seed)
    cw = compute_class_weight("balanced", classes=np.array([0, 1]), y=y[fit])
    Xf, yf = torch.tensor(X[fit], dtype=torch.float32), torch.tensor(y[fit], dtype=torch.float32)
    Xv, yv = torch.tensor(X[val], dtype=torch.float32, device=device), torch.tensor(y[val], dtype=torch.float32, device=device)
    w = torch.tensor(cw, dtype=torch.float32)
    model = DCNNSA(X.shape[1]).to(device)
    opt = torch.optim.Adam(model.parameters(), lr=hp["lr"], betas=(0.9, 0.999), eps=1e-7)
    sched = torch.optim.lr_scheduler.ReduceLROnPlateau(opt, mode="min", factor=hp["lr_factor"],
                                                       patience=hp["lr_patience"], threshold=1e-4,
                                                       threshold_mode="abs", min_lr=hp["min_lr"])
    bce = torch.nn.functional.binary_cross_entropy_with_logits
    gen = torch.Generator().manual_seed(seed)
    best, best_state, best_epoch, wait, hist = float("inf"), None, -1, 0, []
    t0 = time.time()
    for epoch in range(hp["epochs"]):
        model.train()
        perm = torch.randperm(len(yf), generator=gen)
        tot, nb = 0.0, 0
        for s in range(0, len(perm), hp["batch_size"]):
            b = perm[s:s + hp["batch_size"]]
            xb, yb = Xf[b].to(device), yf[b].to(device)
            loss = (w[yf[b].long()].to(device) * bce(model.logits(xb), yb, reduction="none")).mean()
            loss = loss + model.l2_penalty()
            opt.zero_grad(set_to_none=True)
            loss.backward()
            opt.step()
            tot += float(loss); nb += 1
        model.eval()
        with torch.no_grad():
            lv = torch.cat([model.logits(Xv[s:s + 8192]) for s in range(0, len(Xv), 8192)])
            val_loss = float(bce(lv, yv)) + float(model.l2_penalty())
            val_acc = float(((lv >= 0).float() == yv).float().mean())
        lr = opt.param_groups[0]["lr"]
        hist.append({"epoch": epoch + 1, "loss": tot / nb, "val_loss": val_loss, "val_accuracy": val_acc, "lr": lr})
        log(f"  seed {seed} epoch {epoch + 1:2d} loss {tot / nb:.5f} val_loss {val_loss:.5f} "
            f"val_acc {val_acc:.5f} lr {lr:.1e} ({time.time() - t0:.0f}s)")
        if val_loss < best:
            best, best_state, best_epoch, wait = val_loss, copy.deepcopy(model.state_dict()), epoch + 1, 0
        else:
            wait += 1
            if wait >= hp["es_patience"]:
                break
        sched.step(val_loss)
    model.load_state_dict(best_state)
    model.eval()
    info = {"epochs_run": len(hist), "best_epoch": best_epoch, "best_val_loss": best,
            "train_seconds": round(time.time() - t0, 1), "class_weight": [float(c) for c in cw],
            "fit_rows": int(len(fit)), "val_rows": int(len(val)), "fit_index_sha256": _sha(np.sort(fit)),
            "history": hist}
    return model, info


def predict(model, X: np.ndarray, device: str = "cpu") -> np.ndarray:
    import torch
    with torch.no_grad():
        t = torch.tensor(X, dtype=torch.float32, device=device)
        return torch.cat([model(t[s:s + 8192]) for s in range(0, len(t), 8192)]).cpu().numpy().astype(np.float64)


# ------------------------------------------------------------------ commands
def _selection_record(d: dict) -> dict:
    sel = select_features(d["Xtr"], d["ytr"], d["pre"].feature_names)
    ds = load_manifest()["datasets"][DATASET_ID]
    sha = {f["name"]: f["sha256"] for f in ds["files"] if f["name"] in FILES.values()}
    return {"protocol": "D-009 Fang DCNN+SA adaptation", "dataset": DATASET_ID, "files_sha256": sha,
            "rows": {"train": int(len(d["ytr"])), "test": int(len(d["yte"])),
                     "train_dos": int(d["ytr"].sum()), "test_dos": int(d["yte"].sum())},
            "positive_class": "DoS", "preprocessor": d["pre"].record(),
            "train_matrix_sha256": _sha(d["Xtr"]), **sel}


def cmd_select(check: bool = False) -> int:
    d = prepare()
    rec = _selection_record(d)
    path = OUT / "selection.json"
    if check:
        old = json.loads(path.read_text(encoding="utf-8"))
        same = old["selected"] == rec["selected"] and old["train_matrix_sha256"] == rec["train_matrix_sha256"]
        print("selection reproduces" if same else "SELECTION DIFFERS")
        return 0 if same else 1
    pop = duplicate_population(d, rec["selected_index"])
    rec["test_populations"] = {k: {kk: vv for kk, vv in v.items() if kk != "_mask"} for k, v in pop.items()}
    OUT.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rec, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {path.relative_to(ROOT)}: K={rec['k']} (95% rule: {rec['rule95_count']}); "
          f"model-visible duplicate filter keeps {rec['test_populations']['model_visible']['kept_rows']}"
          f"/{len(d['yte'])} test rows")
    return 0


def _identity(sel: dict, seed: int) -> dict:
    from src.env import _git
    return {"seed": seed, "selection_sha256": hashlib.sha256(json.dumps(sel["selected"]).encode()).hexdigest(),
            "train_matrix_sha256": sel["train_matrix_sha256"], "hyperparameters": TRAIN,
            "code_commit": _git().get("commit")}


def cmd_run(seeds: list, device: str = "cpu") -> int:
    import torch

    from src.env import fingerprint, snapshot
    sel = json.loads((OUT / "selection.json").read_text(encoding="utf-8"))
    d = prepare()
    if _sha(d["Xtr"]) != sel["train_matrix_sha256"]:
        raise RuntimeError("training matrix differs from the frozen selection record")
    pop = duplicate_population(d, sel["selected_index"])
    for k, v in pop.items():
        if v["kept_mask_sha256"] != sel["test_populations"][k]["kept_mask_sha256"]:
            raise RuntimeError(f"{k} test population differs from the frozen record")
    Xtr, Xte = d["Xtr"][:, sel["selected_index"]], d["Xte"][:, sel["selected_index"]]
    for seed in seeds:
        rdir = OUT / f"seed{seed}"
        ident = _identity(sel, seed)
        done = rdir / "metrics.json"
        if done.is_file():
            prev = json.loads(done.read_text(encoding="utf-8"))["identity"]
            if {k: v for k, v in prev.items() if k != "code_commit"} == {k: v for k, v in ident.items() if k != "code_commit"}:
                print(f"seed {seed}: already complete, skipped")
                continue
            raise RuntimeError(f"seed {seed}: existing result has a different identity; refusing to overwrite")
        snap = snapshot(seed)
        snap["device"] = device
        model, info = train_seed(seed, Xtr, d["ytr"], device)
        p = predict(model, Xte, device)
        res = {"official": metrics(d["yte"], p)}
        for k, v in pop.items():
            res[f"dedup_{k}"] = metrics(d["yte"][v["_mask"]], p[v["_mask"]])
        rdir.mkdir(parents=True, exist_ok=True)
        torch.save(model.state_dict(), rdir / "model.pt")
        np.save(rdir / "test_proba.npy", p)
        rec = {"identity": ident, "training": info, "test": res, "test_proba_sha256": _sha(p),
               "environment": snap, "environment_fingerprint": fingerprint(snap)}
        done.write_text(json.dumps(rec, indent=2) + "\n", encoding="utf-8")
        o, m = res["official"], res["dedup_model_visible"]
        print(f"seed {seed}: official errors {o['errors']}/{o['n']} MCC {o['mcc']:.5f} | "
              f"dedup errors {m['errors']}/{m['n']} MCC {m['mcc']:.5f} ({info['train_seconds']}s)")
    return 0


def cmd_summary() -> int:
    rows = []
    for f in sorted(OUT.glob("seed*/metrics.json")):
        r = json.loads(f.read_text(encoding="utf-8"))
        for pop, m in r["test"].items():
            rows.append({"seed": r["identity"]["seed"], "population": pop, **{k: m[k] for k in (
                "n", "errors", "fp", "fn", "accuracy", "mcc", "fpr", "dos_recall", "dos_precision", "dos_f1",
                "normal_recall_specificity", "normal_precision", "normal_f1", "roc_auc")}})
    if not rows:
        print("no completed seeds")
        return 1
    df = pd.DataFrame(rows)
    agg = df.drop(columns="seed").groupby("population").agg(["mean", "std", "min", "max"])
    out = {"seeds": sorted(df["seed"].unique().tolist()), "per_seed": rows,
           "aggregate": {p: {c: agg.loc[p, c].to_dict() for c in agg.columns.levels[0]} for p in agg.index}}
    (OUT / "summary.json").write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    with pd.option_context("display.width", 200, "display.max_columns", 20):
        print(df.groupby("population")[["n", "errors", "accuracy", "mcc", "fpr", "dos_recall", "normal_recall_specificity"]].mean())
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("command", choices=("select", "run", "summary"))
    p.add_argument("--check", action="store_true")
    p.add_argument("--seeds", type=int, nargs="+", default=[0, 1, 2, 3, 4])
    p.add_argument("--device", default="cpu")
    a = p.parse_args(argv)
    if a.command == "select":
        return cmd_select(a.check)
    if a.command == "run":
        return cmd_run(a.seeds, a.device)
    return cmd_summary()


if __name__ == "__main__":
    raise SystemExit(main())
