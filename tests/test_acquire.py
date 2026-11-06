import hashlib
import zipfile

import pytest

from src.data.acquire import check_file, cmd_download, cmd_verify, safe_extract

PAYLOAD = b"a,b\n1,2\n"


def _manifest(source, sha=None, size=len(PAYLOAD)):
    return {"datasets": {"toy": {"local_dir": "raw/toy", "files": [
        {"name": "toy.csv", "size_bytes": size, "sha256": sha,
         "download": {"method": "direct", "url": source.as_uri()}},
        {"name": "form.zip", "download": {"method": "manual", "instructions": "fill the form"}},
    ]}}}


def test_direct_download_verifies_size_and_hash(tmp_path):
    src = tmp_path / "src.csv"
    src.write_bytes(PAYLOAD)
    manifest = _manifest(src, sha=hashlib.sha256(PAYLOAD).hexdigest())
    assert cmd_download(manifest, "toy", root=tmp_path) == 0
    assert (tmp_path / "raw/toy/toy.csv").read_bytes() == PAYLOAD
    assert check_file(tmp_path / "raw/toy/toy.csv", manifest["datasets"]["toy"]["files"][0]) == []
    # verify still fails overall: the manual-source file has not been acquired
    assert cmd_verify(manifest, "toy", root=tmp_path) == 1


def test_size_or_hash_mismatch_fails(tmp_path):
    src = tmp_path / "src.csv"
    src.write_bytes(PAYLOAD)
    assert cmd_download(_manifest(src, size=999), "toy", root=tmp_path) == 1
    assert check_file(tmp_path / "raw/toy/toy.csv", {"sha256": "0" * 64}) == ["sha256 mismatch"]
    assert check_file(tmp_path / "nope.csv", {}) == ["missing"]
    path = tmp_path / "raw/toy/toy.csv"
    assert check_file(path, {"publisher_md5": hashlib.md5(path.read_bytes()).hexdigest()}) == []
    assert check_file(path, {"publisher_md5": "0" * 32}) == ["publisher md5 mismatch"]


def test_manual_sources_are_skipped(tmp_path, capsys):
    src = tmp_path / "src.csv"
    src.write_bytes(PAYLOAD)
    cmd_download(_manifest(src), "toy", root=tmp_path)
    assert "manual download needed" in capsys.readouterr().out
    assert not (tmp_path / "raw/toy/form.zip").exists()


def test_safe_extract(tmp_path):
    good = tmp_path / "good.zip"
    with zipfile.ZipFile(good, "w") as zf:
        zf.writestr("dir/data.csv", PAYLOAD)
    assert safe_extract(good, tmp_path / "out") == {"dir/data.csv": "dir/data.csv"}
    assert (tmp_path / "out/dir/data.csv").read_bytes() == PAYLOAD


def test_safe_extract_makes_trailing_space_dirs_windows_safe(tmp_path):
    # GeneratedLabelledFlows.zip stores its CSVs under "TrafficLabelling /".
    z = tmp_path / "glf.zip"
    with zipfile.ZipFile(z, "w") as zf:
        zf.writestr("TrafficLabelling /Monday.csv", PAYLOAD)
    written = safe_extract(z, tmp_path / "out")
    assert written == {"TrafficLabelling/Monday.csv": "TrafficLabelling /Monday.csv"}
    assert (tmp_path / "out/TrafficLabelling/Monday.csv").read_bytes() == PAYLOAD


@pytest.mark.parametrize("member", ["../evil.csv", "/abs/evil.csv", "a/../../evil.csv"])
def test_safe_extract_rejects_path_traversal(tmp_path, member):
    bad = tmp_path / "bad.zip"
    with zipfile.ZipFile(bad, "w") as zf:
        zf.writestr(member, PAYLOAD)
    with pytest.raises(ValueError):
        safe_extract(bad, tmp_path / "out")
    assert not (tmp_path / "evil.csv").exists()
