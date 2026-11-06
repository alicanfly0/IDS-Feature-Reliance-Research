import pandas as pd

from src.data.inspection import inspect_frame, main
from src.data.load import read_flow_csv


def _reasons(report, column):
    return [f["reason"] for f in report["leakage_candidates"] if f["column"] == column]


def test_report_counts(toy_flows):
    df = pd.concat([toy_flows, toy_flows.iloc[[0]]], ignore_index=True)
    report = inspect_frame(df, "Label")
    assert report["shape"] == [401, toy_flows.shape[1]]
    assert report["label_counts"] == {"BENIGN": 300, "ATTACK": 101}
    assert report["missing"] == {"Flow Bytes/s": 1}
    assert report["infinite"] == {"Flow Bytes/s": 1}
    assert report["negative"] == {"Flow Duration": 1}
    assert report["duplicate_rows"] == 1
    assert report["feature_types"]["proto"] == "categorical"


def test_leakage_flags(toy_flows):
    report = inspect_frame(toy_flows, "Label")
    assert any("flow_id" in r for r in _reasons(report, "Flow ID"))
    assert any("ip_address" in r for r in _reasons(report, "Source IP"))
    assert any("timestamp" in r for r in _reasons(report, "Timestamp"))
    assert any("port" in r for r in _reasons(report, "Destination Port"))
    assert any("separator" in r for r in _reasons(report, "Destination Port"))
    assert _reasons(report, "Bwd URG Flags") == ["constant column"]


def test_conflicting_label_duplicates():
    df = pd.DataFrame({"a": [1, 1, 2, 2], "b": [0, 0, 5, 5], "Label": ["X", "Y", "X", "X"]})
    report = inspect_frame(df, "Label")
    assert report["duplicate_feature_rows"] == 2
    assert report["conflicting_label_duplicates"] == 1


def test_reader_handles_cicids_style_quirks(tmp_path):
    # Leading spaces, a repeated column name, an "Infinity" token and a cp1252 byte.
    raw = (
        " Destination Port, Fwd Header Length, Fwd Header Length,Flow Bytes/s, Label\r\n"
        "80,20,20,Infinity,Web Attack – Brute Force\r\n"  # en dash -> byte 0x96
        "443,32,32,12.5,BENIGN\r\n"
    ).encode("cp1252")
    path = tmp_path / "quirky.csv"
    path.write_bytes(raw)
    df, notes = read_flow_csv(path)
    assert notes["encoding"] == "cp1252"
    assert notes["duplicated_names"] == ["Fwd Header Length"]
    assert list(df.columns) == ["Destination Port", "Fwd Header Length", "Fwd Header Length.1", "Flow Bytes/s", "Label"]
    assert inspect_frame(df, "Label")["infinite"] == {"Flow Bytes/s": 1}


def test_cli_runs_on_directory(tmp_path, toy_flows, capsys):
    toy_flows.to_csv(tmp_path / "a.csv", index=False)
    toy_flows.to_csv(tmp_path / "b.csv", index=False)
    out_json = tmp_path / "report.json"
    assert main([str(tmp_path), "--label", "Label", "--json", str(out_json)]) == 0
    text = capsys.readouterr().out
    assert "shape: 800 rows" in text
    assert out_json.exists()
