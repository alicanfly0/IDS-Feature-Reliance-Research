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
