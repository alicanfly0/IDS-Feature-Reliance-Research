import json

import pandas as pd
import pytest

from src.data.inspection import inspect_frame, main
from src.data.load import read_flow_csv, read_names_file


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


@pytest.mark.parametrize("name,is_id", [
    ("Source IP", True), ("Dst IP", True), ("IPV4_SRC_ADDR", True), ("srcip", True),
    ("L4_DST_PORT", True), ("Destination Port", True), ("dsport", True),
    ("MIN_IP_PKT_LEN", False), ("MAX_IP_PKT_LEN", False), ("Flow IAT Min", False), ("sttl", False),
])
def test_identifier_name_patterns(name, is_id):
    df = pd.DataFrame({name: [1, 2, 1, 2], "label": [0, 1, 0, 1]})
    assert (inspect_frame(df, "label")["identifier_columns"] == [name]) is is_id


def test_identifier_columns_do_not_hide_duplicates():
    # Same flow contents, unique row ids (as in UNSW-NB15 training-set.csv), one label clash.
    df = pd.DataFrame({
        "id": [1, 2, 3, 4], "dur": [0.1, 0.1, 0.2, 0.3], "proto": ["tcp", "tcp", "udp", "tcp"],
        "attack_cat": ["DoS", "Normal", "Normal", "Normal"], "label": [1, 0, 0, 0],
    })
    report = inspect_frame(df, "label")
    assert report["duplicate_feature_rows"] == 0  # the id makes every row distinct
    assert report["identifier_columns"] == ["id"]
    assert report["duplicate_content_rows"] == 1
    assert report["conflicting_label_duplicates"] == 1
    assert report["label_like_counts"] == {"attack_cat": {"Normal": 3, "DoS": 1}}


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


def test_reader_strips_utf8_bom_and_applies_names_file(tmp_path):
    with_header = tmp_path / "bom.csv"
    with_header.write_bytes("﻿id,label\n1,0\n".encode("utf-8"))
    df, notes = read_flow_csv(with_header)
    assert notes["utf8_bom"] and list(df.columns) == ["id", "label"]

    names_file = tmp_path / "features.csv"
    names_file.write_text("No.,Name,Type \n1,srcip,nominal\n2, Label ,binary\n", encoding="utf-8")
    body = tmp_path / "data.csv"
    body.write_bytes("﻿10.0.0.1,0\n10.0.0.2,1\n".encode("utf-8"))
    df, notes = read_flow_csv(body, header=False, names=read_names_file(names_file))
    assert list(df.columns) == ["srcip", "Label"]
    assert df.iloc[0, 0] == "10.0.0.1"  # BOM not glued to the first value
    assert notes["names_source"] == "names"


def test_names_count_mismatch_raises(tmp_path):
    body = tmp_path / "data.csv"
    body.write_text("1,2,3\n", encoding="utf-8")
    with pytest.raises(ValueError):
        read_flow_csv(body, header=False, names=["a", "b"])


def test_cli_runs_on_directory(tmp_path, toy_flows, capsys):
    toy_flows.to_csv(tmp_path / "a.csv", index=False)
    toy_flows.to_csv(tmp_path / "b.csv", index=False)
    out_json = tmp_path / "report.json"
    out_txt = tmp_path / "report.txt"
    assert main([str(tmp_path), "--label", "Label", "--json", str(out_json), "--txt", str(out_txt)]) == 0
    text = capsys.readouterr().out
    assert "shape: 800 rows" in text
    assert "shape: 800 rows" in out_txt.read_text(encoding="utf-8")
    # Files outside the repository are reported by name only (audit F5: no local paths).
    paths = [f["path"] for f in json.loads(out_json.read_text(encoding="utf-8"))["files"]]
    assert paths == ["a.csv", "b.csv"]


def test_portable_path_is_repository_relative():
    from src.data.inspection import portable_path
    from src.data.manifest import ROOT
    assert portable_path(ROOT / "data" / "raw" / "x" / "f.csv") == "data/raw/x/f.csv"
