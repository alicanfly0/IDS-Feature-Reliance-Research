import hashlib

from src.data.manifest import load_manifest, local_status, sha256_file, validate_manifest

EXPECTED_DATASETS = {
    "cicids2017_original", "cicids2017_engelen_wtmc2021", "unsw_nb15", "nf_unsw_nb15_v2",
}
MIRROR_HOSTS = ("kaggle.com", "huggingface.co", "github.com/datasets")


def test_manifest_is_well_formed():
    assert validate_manifest(load_manifest()) == []


def test_manifest_covers_the_four_planned_datasets():
    assert set(load_manifest()["datasets"]) == EXPECTED_DATASETS


def test_no_mirror_used_as_source():
    for entry in load_manifest()["datasets"].values():
        src = entry["official_source"]
        for url in (src["landing_page"], src["download"]):
            assert not any(host in url for host in MIRROR_HOSTS), url


def test_nothing_marked_acquired_without_checksums():
    for ds_id, entry in load_manifest()["datasets"].items():
        if entry["status"] != "not_acquired":
            assert all(f.get("sha256") for f in entry["files"]), ds_id


def test_validator_catches_problems():
    bad = {"datasets": {"x": {"name": "x", "status": "verified", "official_source": {}, "files": [{"name": "a"}]}}}
    problems = validate_manifest(bad)
    assert any("missing 'license'" in p for p in problems)
    assert any("official_source.download" in p for p in problems)
    assert any("no sha256" in p for p in problems)


def test_sha256_and_local_status(tmp_path):
    (tmp_path / "d").mkdir()
    f = tmp_path / "d" / "a.csv"
    f.write_bytes(b"x,y\n1,2\n")
    expected = hashlib.sha256(b"x,y\n1,2\n").hexdigest()
    assert sha256_file(f) == expected
    manifest = {"datasets": {"toy": {"local_dir": "d", "files": [
        {"name": "a.csv", "sha256": expected}, {"name": "b.csv", "sha256": None}]}}}
    rows = local_status(manifest, root=tmp_path, compute_hash=True)
    assert rows[0]["present"] and rows[0]["sha256_match"] is True
    assert not rows[1]["present"]
