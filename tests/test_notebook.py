"""Regression checks for the Colab notebook (static; nothing is executed)."""
import ast
import json
import re
import subprocess
import sys

from src.config import ROOT

NB_PATH = ROOT / "notebooks" / "colab_runner.ipynb"
NB = json.loads(NB_PATH.read_text(encoding="utf-8"))
CODE = ["".join(c["source"]) for c in NB["cells"] if c["cell_type"] == "code"]
ALL = "\n".join(CODE)


def test_notebook_matches_its_generator(tmp_path):
    out = tmp_path / "nb.ipynb"
    subprocess.run([sys.executable, str(ROOT / "scripts" / "make_colab_notebook.py"), str(out)], check=True,
                   capture_output=True)
    assert json.loads(out.read_text(encoding="utf-8")) == NB


def test_cells_parse_and_have_no_outputs():
    for src in CODE:
        ast.parse("\n".join(l for l in src.splitlines() if not l.lstrip().startswith(("!", "%"))))
    assert all(not c.get("outputs") for c in NB["cells"])


def test_packages_installed_before_xgboost_is_imported():
    first_import = ALL.index("import xgboost")
    assert ALL.index("pip\", \"install\"") < first_import
    assert "importlib.metadata.version(\"xgboost\")" in ALL[:first_import]   # version check without importing


def test_archive_location_matches_plan_and_decision_log():
    archive = re.search(r'ARCHIVE = f"\{DATA_DRIVE\}/([^"]+)"', ALL).group(1)
    drive_path = f"MyDrive/cnet-data/{archive}"
    assert drive_path == "MyDrive/cnet-data/cicids2017_original/MachineLearningCSV.zip"
    assert drive_path in (ROOT / "docs" / "COLAB_EXECUTION_PLAN.md").read_text(encoding="utf-8")
    assert drive_path in (ROOT / "docs" / "decision_log.md").read_text(encoding="utf-8")
    assert '!cp "{ARCHIVE}"' in ALL


def test_d015_guard_precedes_any_drive_access_and_defaults_off():
    assert "D015_AMENDMENT_1_RECORDED = False" in ALL
    guard = ALL.index("assert D015_AMENDMENT_1_RECORDED")
    assert guard < ALL.index("drive.mount") and guard < ALL.index("{ARCHIVE}")


def test_no_token_in_persisted_urls():
    assert not re.search(r"https://[^\"\s]*\{?token\}?@", ALL)
    assert "http.extraHeader" in ALL and 'replace(token, "***")' in ALL


# Milestone 3B-0.1: top-to-bottom execution must never train a full model.
TRAINING = re.compile(r"src\.experiments\.ae_xgb|matrix_3b\W+run|matrix_3b\", \"run\"")
PHRASES = {"AUTHORIZE_LEGACY_BASELINE_RUN": "I confirm this training run is approved",
           "AUTHORIZE_3B_BATCH": "I confirm this training batch is approved"}


def _training_lines():
    """(cell, line, guarded) for every line that would invoke a training entry point."""
    out = []
    for i, src in enumerate(CODE):
        lines = src.splitlines()
        for j, line in enumerate(lines):
            code = line.split("#", 1)[0] if not line.lstrip().startswith("!") else line
            if not TRAINING.search(code) or "--benchmark" in code:
                continue
            guard = next((g for g in reversed(lines[:j]) if g.lstrip().startswith("if ")), "")
            guarded = any(f'{flag} == "{phrase}"' in guard for flag, phrase in PHRASES.items())
            out.append((i, line.strip(), guarded and not line.lstrip().startswith("!")))
    return out


def test_no_active_training_command_runs_by_default():
    found = _training_lines()
    assert found, "expected the guarded training examples to exist"
    unguarded = [f for f in found if not f[2]]
    assert not unguarded, f"training reachable without explicit authorization: {unguarded}"
    for flag in PHRASES:
        assert f'{flag} = ""' in ALL                     # disabled by default
    assert "--confirm-approved" in ALL and "not proof that the approvals exist" in "".join(
        "".join(c["source"]) for c in NB["cells"] if c["cell_type"] == "markdown")


def test_guard_detects_an_active_training_line():
    global CODE
    saved = CODE
    try:
        CODE = saved + ['!python -m src.experiments.ae_xgb --config x.yaml --device cuda --storage s']
        assert any(not g for *_, g in _training_lines())
        CODE = saved + ['x = 1\nsubprocess.run([sys.executable, "-m", "src.experiments.matrix_3b", "run"])']
        assert any(not g for *_, g in _training_lines())
    finally:
        CODE = saved


def test_benchmark_is_described_as_bounded_training_and_dry_run_stays_active():
    md_text = "".join("".join(c["source"]) for c in NB["cells"] if c["cell_type"] == "markdown")
    assert "trains **temporary** model components" in md_text and "No training." not in md_text
    assert any(l.strip().startswith("!python -m src.experiments.matrix_3b plan") for l in ALL.splitlines())
    assert any(l.strip().startswith("!python -m src.experiments.ae_xgb") and "--benchmark" in l for l in ALL.splitlines())
