"""Tests for scripts/flybrain_fetch_connectome.py (spec §1 SHA-256 verification, §12).

Everything runs on tiny generated files; no network, no real connectome.
The parquet conversion test needs pyarrow and is skipped when it is absent.
The real-data test is skipped unless FLYBRAIN_DATA_DIR holds the two files.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "flybrain_fetch_connectome.py"


@pytest.fixture(scope="module")
def fetch():
    spec = importlib.util.spec_from_file_location("flybrain_fetch_connectome", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _write_completeness(path: Path, n: int) -> None:
    lines = [",Completed"] + [f"{720575940600000000 + i},True" for i in range(n)]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_parquet(path: Path) -> None:
    pa = pytest.importorskip("pyarrow")
    pq = pytest.importorskip("pyarrow.parquet")
    table = pa.table(
        {
            "Presynaptic_ID": pa.array([1, 1, 2], pa.int64()),
            "Postsynaptic_ID": pa.array([2, 3, 3], pa.int64()),
            "Presynaptic_Index": pa.array([0, 0, 1], pa.int64()),
            "Postsynaptic_Index": pa.array([1, 2, 2], pa.int64()),
            "Connectivity": pa.array([1, 2, 10], pa.int64()),
            "Excitatory": pa.array([1, -1, 1], pa.int64()),
            "Excitatory x Connectivity": pa.array([1, -2, 10], pa.int64()),
        }
    )
    pq.write_table(table, path)


# ---------------------------------------------------------------------------
# hashing and verification
# ---------------------------------------------------------------------------


def test_sha256_file_matches_hashlib(fetch, tmp_path):
    payload = b"flybrain" * 1000
    p = tmp_path / "blob.bin"
    p.write_bytes(payload)
    assert fetch.sha256_file(p) == _sha(payload)
    actual, ok = fetch.verify_file(p, _sha(payload).upper())
    assert ok is True and actual == _sha(payload)
    assert fetch.verify_file(p, None) == (_sha(payload), None)
    assert fetch.verify_file(p, "0" * 64)[1] is False


def test_ensure_file_copies_and_verifies(fetch, tmp_path):
    src_dir = tmp_path / "src"
    dest = tmp_path / "dest"
    src_dir.mkdir()
    _write_completeness(src_dir / fetch.COMPLETENESS_FILE, 3)
    good = _sha((src_dir / fetch.COMPLETENESS_FILE).read_bytes())
    known = {fetch.COMPLETENESS_FILE: good}

    entry = fetch.ensure_file(fetch.COMPLETENESS_FILE, dest, source_dir=src_dir, known=known)
    assert entry["action"] == "copied" and entry["sha256_ok"] is True
    assert (dest / fetch.COMPLETENESS_FILE).is_file()
    assert not (dest / (fetch.COMPLETENESS_FILE + ".part")).exists()

    # Idempotent: a second call hashes the existing file and skips the copy.
    again = fetch.ensure_file(fetch.COMPLETENESS_FILE, dest, source_dir=src_dir, known=known)
    assert again["action"] == "skipped" and again["sha256_ok"] is True


def test_hash_mismatch_is_rejected_and_kept(fetch, tmp_path):
    src_dir = tmp_path / "src"
    dest = tmp_path / "dest"
    src_dir.mkdir()
    _write_completeness(src_dir / fetch.COMPLETENESS_FILE, 3)
    known = {fetch.COMPLETENESS_FILE: "f" * 64}

    with pytest.raises(fetch.HashMismatch) as excinfo:
        fetch.ensure_file(fetch.COMPLETENESS_FILE, dest, source_dir=src_dir, known=known)
    assert excinfo.value.expected == "f" * 64
    assert not (dest / fetch.COMPLETENESS_FILE).exists()
    rejected = dest / (fetch.COMPLETENESS_FILE + ".rejected")
    assert rejected.is_file()
    assert rejected.read_bytes() == (src_dir / fetch.COMPLETENESS_FILE).read_bytes()


def test_main_exits_2_on_mismatch(fetch, tmp_path, monkeypatch, capsys):
    src_dir = tmp_path / "src"
    dest = tmp_path / "dest"
    src_dir.mkdir()
    _write_completeness(src_dir / fetch.COMPLETENESS_FILE, 3)
    monkeypatch.setitem(fetch.KNOWN_SHA256, fetch.COMPLETENESS_FILE, "e" * 64)

    code = fetch.main(["--source-dir", str(src_dir), "--dest", str(dest)])
    assert code == fetch.EXIT_HASH_MISMATCH == 2
    out = json.loads(capsys.readouterr().out)
    assert "mismatch" in out["error"]
    assert (dest / (fetch.COMPLETENESS_FILE + ".rejected")).is_file()
    assert out["manifest"]["files"][fetch.COMPLETENESS_FILE]["present"] is False


def test_stale_file_is_rejected_then_refetched_in_same_run(fetch, tmp_path, monkeypatch):
    """A truncated on-disk file must be moved aside and re-fetched in one run (no --source-dir)."""
    dest = tmp_path / "dest"
    dest.mkdir()
    good_dir = tmp_path / "good"
    good_dir.mkdir()
    _write_completeness(good_dir / fetch.COMPLETENESS_FILE, 3)
    good_bytes = (good_dir / fetch.COMPLETENESS_FILE).read_bytes()
    known = {fetch.COMPLETENESS_FILE: _sha(good_bytes)}
    # Partial/corrupt copy already sitting at the destination.
    (dest / fetch.COMPLETENESS_FILE).write_bytes(good_bytes[:10])

    calls = []

    def _fake_download(url, target, timeout=60.0):
        calls.append(url)
        target.write_bytes(good_bytes)
        return target

    monkeypatch.setattr(fetch, "download_file", _fake_download)

    entry = fetch.ensure_file(
        fetch.COMPLETENESS_FILE, dest, known=known, base_url="http://example.invalid/base"
    )
    assert calls == [f"http://example.invalid/base/{fetch.COMPLETENESS_FILE}"]
    assert entry["action"] == "downloaded" and entry["sha256_ok"] is True
    assert (dest / fetch.COMPLETENESS_FILE).read_bytes() == good_bytes
    rejected = dest / (fetch.COMPLETENESS_FILE + ".rejected")
    assert rejected.is_file() and rejected.read_bytes() == good_bytes[:10]


def test_no_verify_records_hash_without_judging(fetch, tmp_path):
    src_dir = tmp_path / "src"
    dest = tmp_path / "dest"
    src_dir.mkdir()
    _write_completeness(src_dir / fetch.COMPLETENESS_FILE, 2)
    known = {fetch.COMPLETENESS_FILE: "a" * 64}
    entry = fetch.ensure_file(
        fetch.COMPLETENESS_FILE, dest, source_dir=src_dir, known=known, verify=False
    )
    assert entry["sha256_ok"] is None
    assert entry["sha256"] == _sha((src_dir / fetch.COMPLETENESS_FILE).read_bytes())
    assert (dest / fetch.COMPLETENESS_FILE).is_file()


def test_count_neurons_excludes_header(fetch, tmp_path):
    p = tmp_path / fetch.COMPLETENESS_FILE
    _write_completeness(p, 5)
    assert fetch.count_neurons(p) == 5


# ---------------------------------------------------------------------------
# parquet -> npz conversion
# ---------------------------------------------------------------------------


def test_convert_parquet_to_npz_keys_and_dtypes(fetch, tmp_path):
    np = pytest.importorskip("numpy")
    parquet = tmp_path / fetch.CONNECTIVITY_PARQUET
    _write_parquet(parquet)
    npz = tmp_path / fetch.CONNECTIVITY_NPZ
    sha = fetch.sha256_file(parquet)

    info = fetch.convert_parquet_to_npz(parquet, npz, n_neurons=3, source_sha256=sha)
    assert info["n_synapses"] == 3 and info["n_neurons"] == 3
    assert npz.is_file() and not npz.with_name(npz.name + ".part.npz").exists()

    with np.load(npz, allow_pickle=False) as archive:
        assert sorted(archive.files) == sorted(fetch.NPZ_KEYS)
        assert archive["pre"].dtype == np.int32
        assert archive["post"].dtype == np.int32
        assert archive["weight"].dtype == np.float32
        assert archive["n_neurons"].dtype == np.int64 and int(archive["n_neurons"]) == 3
        assert str(archive["source_sha256"]) == sha
        assert archive["pre"].tolist() == [0, 0, 1]
        assert archive["post"].tolist() == [1, 2, 2]
        assert archive["weight"].tolist() == [1.0, -2.0, 10.0]  # signed weights preserved

    inspected = fetch.inspect_npz(npz)
    assert inspected["keys_ok"] is True and inspected["source_sha256"] == sha
    assert fetch.npz_matches_source(npz, sha) is True
    assert fetch.npz_matches_source(npz, "0" * 64) is False


def test_convert_rejects_index_out_of_range(fetch, tmp_path):
    pytest.importorskip("numpy")
    parquet = tmp_path / fetch.CONNECTIVITY_PARQUET
    _write_parquet(parquet)
    with pytest.raises(ValueError):
        fetch.convert_parquet_to_npz(
            parquet, tmp_path / fetch.CONNECTIVITY_NPZ, n_neurons=2, source_sha256="x"
        )


def test_main_end_to_end_on_tiny_files(fetch, tmp_path, monkeypatch, capsys):
    np = pytest.importorskip("numpy")
    src_dir = tmp_path / "src"
    dest = tmp_path / "dest"
    src_dir.mkdir()
    _write_completeness(src_dir / fetch.COMPLETENESS_FILE, 3)
    _write_parquet(src_dir / fetch.CONNECTIVITY_PARQUET)
    monkeypatch.setitem(
        fetch.KNOWN_SHA256,
        fetch.COMPLETENESS_FILE,
        fetch.sha256_file(src_dir / fetch.COMPLETENESS_FILE),
    )
    monkeypatch.setitem(
        fetch.KNOWN_SHA256,
        fetch.CONNECTIVITY_PARQUET,
        fetch.sha256_file(src_dir / fetch.CONNECTIVITY_PARQUET),
    )

    code = fetch.main(["--source-dir", str(src_dir), "--dest", str(dest)])
    assert code == 0
    out = json.loads(capsys.readouterr().out)
    assert out["steps"][fetch.CONNECTIVITY_NPZ]["action"] == "converted"
    assert out["manifest"]["ready"] is True
    assert sorted(out["manifest"]["npz"]["keys"]) == sorted(fetch.NPZ_KEYS)

    # Second run: nothing is re-copied or re-converted.
    code = fetch.main(["--source-dir", str(src_dir), "--dest", str(dest)])
    assert code == 0
    out = json.loads(capsys.readouterr().out)
    assert out["steps"][fetch.COMPLETENESS_FILE]["action"] == "skipped"
    assert out["steps"][fetch.CONNECTIVITY_PARQUET]["action"] == "skipped"
    assert out["steps"][fetch.CONNECTIVITY_NPZ]["action"] == "skipped"

    # --npz-only: the parquet is dropped and later runs need no parquet at all.
    code = fetch.main(["--source-dir", str(src_dir), "--dest", str(dest), "--npz-only"])
    assert code == 0
    capsys.readouterr()
    assert not (dest / fetch.CONNECTIVITY_PARQUET).exists()
    code = fetch.main(["--dest", str(dest), "--npz-only"])  # no source, no network
    assert code == 0
    out = json.loads(capsys.readouterr().out)
    assert out["manifest"]["ready"] is True
    with np.load(dest / fetch.CONNECTIVITY_NPZ, allow_pickle=False) as archive:
        assert int(archive["n_neurons"]) == 3

    # --print-manifest only hashes what exists.
    code = fetch.main(["--print-manifest", "--dest", str(dest)])
    assert code == 0
    manifest = json.loads(capsys.readouterr().out)
    assert manifest["ready"] is True
    assert manifest["files"][fetch.CONNECTIVITY_PARQUET]["present"] is False


def test_print_manifest_on_empty_dir_is_honest(fetch, tmp_path, capsys):
    code = fetch.main(["--print-manifest", "--dest", str(tmp_path / "nothing")])
    assert code == 0
    manifest = json.loads(capsys.readouterr().out)
    assert manifest["ready"] is False
    assert manifest["npz"] is None
    assert all(v.get("present") is False for v in manifest["files"].values())


def test_no_parquet_reader_exits_3(fetch, tmp_path, monkeypatch, capsys):
    pytest.importorskip("numpy")
    src_dir = tmp_path / "src"
    dest = tmp_path / "dest"
    src_dir.mkdir()
    _write_completeness(src_dir / fetch.COMPLETENESS_FILE, 3)
    (src_dir / fetch.CONNECTIVITY_PARQUET).write_bytes(b"not really parquet")
    monkeypatch.setitem(fetch.KNOWN_SHA256, fetch.COMPLETENESS_FILE, None)
    monkeypatch.setitem(fetch.KNOWN_SHA256, fetch.CONNECTIVITY_PARQUET, None)

    def _no_reader(_path):
        raise fetch.NoParquetReader("neither pyarrow nor pandas is importable; pip install pyarrow")

    monkeypatch.setattr(fetch, "_read_parquet_columns", _no_reader)
    code = fetch.main(["--source-dir", str(src_dir), "--dest", str(dest)])
    assert code == fetch.EXIT_NO_PARQUET_READER == 3
    out = json.loads(capsys.readouterr().out)
    assert "pip install pyarrow" in out["error"]


# ---------------------------------------------------------------------------
# real data (skipped unless FLYBRAIN_DATA_DIR holds the files)
# ---------------------------------------------------------------------------


def _real_dir():
    raw = os.getenv("FLYBRAIN_DATA_DIR", "").strip()
    if not raw:
        return None
    d = Path(raw)
    if (d / "2025_Completeness_783.csv").is_file() and (d / "2025_Connectivity_783.npz").is_file():
        return d
    return None


@pytest.mark.skipif(_real_dir() is None, reason="FLYBRAIN_DATA_DIR with real files not set")
def test_real_manifest_hashes_match_known(fetch, capsys):
    import time

    t0 = time.time()
    code = fetch.main(["--print-manifest", "--dest", str(_real_dir())])
    elapsed = time.time() - t0
    assert code == 0
    manifest = json.loads(capsys.readouterr().out)
    comp = manifest["files"][fetch.COMPLETENESS_FILE]
    assert comp["sha256_ok"] is True, comp
    assert manifest["npz"]["keys_ok"] is True
    assert manifest["npz"]["n_neurons"] == 138639
    assert manifest["npz"]["source_sha256_ok"] is True
    assert manifest["ready"] is True
    print(f"real manifest in {elapsed:.2f}s")
