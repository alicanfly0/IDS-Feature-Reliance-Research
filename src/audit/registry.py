"""Forensic artifact registry (configs/artifact_registry.yaml): loading, validation, feature sets."""
from __future__ import annotations

from pathlib import Path

import yaml

from src.config import ROOT

REGISTRY_PATH = ROOT / "configs" / "artifact_registry.yaml"
LEVELS = ("direct_extraction_error", "shortcut_indicator", "unverified_hypothesis")
TARGETS = ("feature", "flow", "label", "generation_process")
# Sources whose findings come with a section and a page in a PDF we hold.
PAGED_SOURCES = ("engelen2021", "lanvin2023")


def load_registry(path: Path = REGISTRY_PATH) -> dict:
    with open(path, encoding="utf-8") as f:
        reg = yaml.safe_load(f)
    problems = validate(reg)
    if problems:
        raise ValueError("invalid artifact registry: " + "; ".join(problems))
    return reg


def validate(reg: dict) -> list[str]:
    problems = []
    ids = set()
    for entry in reg.get("features", []) + reg.get("non_feature_issues", []):
        eid = entry.get("id", "?")
        if eid in ids:
            problems.append(f"{eid}: duplicate id")
        ids.add(eid)
        if entry.get("evidence_level") not in LEVELS:
            problems.append(f"{eid}: evidence_level must be one of {LEVELS}")
        if entry.get("target") not in TARGETS:
            problems.append(f"{eid}: target must be one of {TARGETS}")
        if not entry.get("sources"):
            problems.append(f"{eid}: no sources")
        for src in entry.get("sources", []):
            if src.get("ref") not in reg.get("sources", {}):
                problems.append(f"{eid}: unknown source {src.get('ref')}")
            if not src.get("section") or not src.get("finding"):
                problems.append(f"{eid}: source {src.get('ref')} needs a section and a finding")
            if src.get("ref") in PAGED_SOURCES and not src.get("page"):
                problems.append(f"{eid}: source {src.get('ref')} needs a page")
        # A level above "hypothesis" must rest on a paged source, not only on Phase II or our own notes.
        if entry.get("evidence_level") != "unverified_hypothesis" and not any(
                s.get("ref") in PAGED_SOURCES for s in entry.get("sources", [])):
            problems.append(f"{eid}: {entry.get('evidence_level')} requires a paged source")
    columns = [c for e in reg.get("features", []) for c in e.get("columns", [])]
    if len(columns) != len(set(columns)):
        problems.append("a column is mapped by more than one feature entry")
    for e in reg.get("features", []):
        if not e.get("columns"):
            problems.append(f"{e.get('id')}: feature entry without columns")
    return problems


def column_entries(reg: dict) -> dict[str, dict]:
    """Model column name -> registry feature entry."""
    return {c: e for e in reg["features"] for c in e["columns"]}


def feature_sets(reg: dict, model_columns: list[str]) -> dict:
    """Registered columns per evidence tier, restricted to the model's columns.

    Tiers: 'direct' (direct_extraction_error), 'shortcut' (shortcut_indicator) and 'all'
    (every registered feature, including unverified hypotheses). Registered columns absent
    from the model are listed under 'missing' rather than silently dropped.
    """
    present = set(model_columns)
    tiers = {"direct": set(), "shortcut": set(), "hypothesis": set()}
    key = {"direct_extraction_error": "direct", "shortcut_indicator": "shortcut", "unverified_hypothesis": "hypothesis"}
    missing = []
    for col, entry in column_entries(reg).items():
        if col in present:
            tiers[key[entry["evidence_level"]]].add(col)
        else:
            missing.append(col)
    tiers["all"] = tiers["direct"] | tiers["shortcut"] | tiers["hypothesis"]
    tiers["missing"] = sorted(missing)
    return tiers
