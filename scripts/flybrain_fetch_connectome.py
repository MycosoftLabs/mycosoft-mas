#!/usr/bin/env python3
"""Fetch, verify and convert the FlyWire v783 connectome for the FlyBrain module.

Spec: docs/FLYBRAIN_MODULE_SEP14_2026.md §1 (licenses, SHA-256 at load) and §12
(deployment). The FlyWire v783 public release carries FlyWire's own data terms
(CC BY-NC 4.0 at the time of writing), so the data is never committed to a
Mycosoft repository: this script places it on the NAS
(``FLYBRAIN_DATA_DIR``, default ``/mnt/mycosoft-nas/models/flybrain``).

What it does, in order:

1. ``2025_Completeness_783.csv`` and ``2025_Connectivity_783.parquet`` are
   downloaded from ``config.UPSTREAM_RAW_BASE`` with urllib (streamed to a
   ``.part`` file, renamed on completion) or copied from ``--source-dir``
   (a local clone such as ``/home/user/eonsystemspbc/fly-brain/data``).
2. Each file's SHA-256 is compared with ``config.KNOWN_SHA256``. A mismatch
   keeps the file as ``<name>.rejected`` and exits with code 2. Files whose
   hash already matches are skipped (idempotent).
3. The parquet is converted to ``2025_Connectivity_783.npz`` with keys
   ``pre`` (int32), ``post`` (int32), ``weight`` (float32), ``n_neurons``
   (int64) and ``source_sha256`` (str) using pyarrow, falling back to pandas.
   With neither importable the script exits with code 3 and says so.
4. A manifest JSON is printed at the end. ``--print-manifest`` only hashes
   what exists and prints that manifest (no network, no conversion).

Exit codes: 0 ok, 1 fetch/IO error, 2 SHA-256 mismatch, 3 no parquet reader.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import shutil
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

_REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_config():
    """Import ``mycosoft_mas.flybrain.config`` without dragging in the whole MAS package.

    ``mycosoft_mas/__init__.py`` may import heavy modules; the config module
    itself is standard-library only, so it is loaded straight from its file.
    """
    cfg_path = _REPO_ROOT / "mycosoft_mas" / "flybrain" / "config.py"
    spec = importlib.util.spec_from_file_location("_flybrain_config", cfg_path)
    if spec is None or spec.loader is None:  # pragma: no cover - repo layout broken
        raise RuntimeError(f"cannot load FlyBrain config from {cfg_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module  # dataclasses need the module registered
    spec.loader.exec_module(module)
    return module


config = _load_config()

COMPLETENESS_FILE: str = config.COMPLETENESS_FILE
CONNECTIVITY_PARQUET: str = config.CONNECTIVITY_PARQUET
CONNECTIVITY_NPZ: str = config.CONNECTIVITY_NPZ
KNOWN_SHA256: Dict[str, str] = dict(config.KNOWN_SHA256)
UPSTREAM_RAW_BASE: str = config.UPSTREAM_RAW_BASE

PARQUET_PRE_COL = "Presynaptic_Index"
PARQUET_POST_COL = "Postsynaptic_Index"
PARQUET_WEIGHT_COL = "Excitatory x Connectivity"
NPZ_KEYS = ("pre", "post", "weight", "n_neurons", "source_sha256")

EXIT_OK = 0
EXIT_ERROR = 1
EXIT_HASH_MISMATCH = 2
EXIT_NO_PARQUET_READER = 3

CHUNK = 1 << 20  # 1 MiB


class HashMismatch(Exception):
    def __init__(self, path: Path, expected: str, actual: str):
        super().__init__(f"{path.name}: SHA-256 mismatch expected={expected} actual={actual}")
        self.path = path
        self.expected = expected
        self.actual = actual


class NoParquetReader(Exception):
    pass


# ---------------------------------------------------------------------------
# hashing / verification
# ---------------------------------------------------------------------------


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(CHUNK), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_file(path: Path, expected: Optional[str]) -> Tuple[str, Optional[bool]]:
    """Return ``(actual_sha256, ok)``; ``ok`` is ``None`` when no expected hash is known."""
    actual = sha256_file(path)
    if not expected:
        return actual, None
    return actual, actual.lower() == expected.lower()


def reject_file(path: Path) -> Path:
    """Move a file that failed verification to ``<name>.rejected`` (kept for inspection)."""
    rejected = path.with_name(path.name + ".rejected")
    if rejected.exists():
        rejected.unlink()
    path.rename(rejected)
    return rejected


# ---------------------------------------------------------------------------
# acquisition
# ---------------------------------------------------------------------------


def _log(msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)


def download_file(url: str, dest: Path, timeout: float = 60.0) -> Path:
    """Stream ``url`` to ``dest`` via a ``.part`` file, then rename."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    part = dest.with_name(dest.name + ".part")
    started = time.time()
    done = 0
    req = urllib.request.Request(url, headers={"User-Agent": "mycosoft-flybrain-fetch/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp, open(part, "wb") as out:
        total = resp.headers.get("Content-Length")
        total_i = int(total) if total and total.isdigit() else None
        last_report = 0.0
        while True:
            block = resp.read(CHUNK)
            if not block:
                break
            out.write(block)
            done += len(block)
            now = time.time()
            if now - last_report > 2.0:
                pct = f" ({100.0 * done / total_i:.0f}%)" if total_i else ""
                _log(f"  ... {done / 1e6:.1f} MB{pct}")
                last_report = now
    os.replace(part, dest)
    _log(f"  downloaded {dest.name}: {done / 1e6:.1f} MB in {time.time() - started:.1f}s")
    return dest


def copy_file(src: Path, dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    part = dest.with_name(dest.name + ".part")
    shutil.copyfile(src, part)
    os.replace(part, dest)
    _log(f"  copied {src} -> {dest}")
    return dest


def ensure_file(
    name: str,
    dest_dir: Path,
    *,
    source_dir: Optional[Path] = None,
    base_url: str = UPSTREAM_RAW_BASE,
    known: Optional[Dict[str, str]] = None,
    verify: bool = True,
) -> Dict[str, Any]:
    """Make ``dest_dir/name`` present and (optionally) verified. Idempotent.

    Returns a manifest entry. Raises :class:`HashMismatch` (after moving the
    file to ``.rejected``) when verification fails.
    """
    known = KNOWN_SHA256 if known is None else known
    expected = known.get(name)
    dest = dest_dir / name
    entry: Dict[str, Any] = {
        "path": str(dest),
        "expected_sha256": expected,
        "sha256": None,
        "sha256_ok": None,
        "size": None,
        "action": None,
    }

    if dest.is_file() and expected:
        actual, ok = verify_file(dest, expected)
        if ok:
            entry.update(sha256=actual, sha256_ok=True, size=dest.stat().st_size, action="skipped")
            _log(f"{name}: present and SHA-256 matches, skipping")
            return entry
        # Move the bad copy aside now so the branch below fetches a fresh one in this run
        # (dest.is_file() would otherwise short-circuit to "existing" and fail again).
        rejected = reject_file(dest)
        _log(f"{name}: SHA-256 differs from known value; kept as {rejected.name}, re-fetching")

    if source_dir is not None:
        src = Path(source_dir) / name
        if not src.is_file():
            raise FileNotFoundError(f"{src} does not exist")
        _log(f"{name}: copying from {source_dir}")
        copy_file(src, dest)
        entry["action"] = "copied"
    elif not dest.is_file():
        url = f"{base_url.rstrip('/')}/{name}"
        _log(f"{name}: downloading {url}")
        download_file(url, dest)
        entry["action"] = "downloaded"
    else:
        entry["action"] = "existing"

    entry["size"] = dest.stat().st_size
    if verify:
        actual, ok = verify_file(dest, expected)
        entry["sha256"] = actual
        entry["sha256_ok"] = ok
        if ok is False:
            rejected = reject_file(dest)
            entry["path"] = str(rejected)
            entry["action"] = "rejected"
            raise HashMismatch(dest, expected or "", actual)
        if ok is None:
            _log(f"{name}: no known SHA-256; recorded {actual}")
    else:
        entry["sha256"] = sha256_file(dest)
        entry["sha256_ok"] = None
        _log(f"{name}: verification skipped (--no-verify); sha256={entry['sha256']}")
    return entry


# ---------------------------------------------------------------------------
# conversion
# ---------------------------------------------------------------------------


def count_neurons(completeness_csv: Path) -> int:
    """Number of neuron rows in the completeness CSV (header ``,Completed`` excluded)."""
    n = 0
    with open(completeness_csv, "r", encoding="utf-8") as fh:
        header = fh.readline()
        if not header.startswith(","):
            # No header: the first line is a data row.
            n += 1 if header.strip() else 0
        for line in fh:
            if line.strip():
                n += 1
    return n


def _read_parquet_columns(parquet: Path):
    """Return ``(pre, post, weight)`` numpy arrays; pyarrow first, pandas fallback."""
    columns = [PARQUET_PRE_COL, PARQUET_POST_COL, PARQUET_WEIGHT_COL]
    try:
        import pyarrow.parquet as pq  # type: ignore

        table = pq.read_table(parquet, columns=columns)
        arrays = [table.column(c).to_numpy(zero_copy_only=False) for c in columns]
        return arrays[0], arrays[1], arrays[2], "pyarrow"
    except ImportError:
        pass
    try:
        import pandas as pd  # type: ignore

        frame = pd.read_parquet(parquet, columns=columns)
        return (
            frame[PARQUET_PRE_COL].to_numpy(),
            frame[PARQUET_POST_COL].to_numpy(),
            frame[PARQUET_WEIGHT_COL].to_numpy(),
            "pandas",
        )
    except ImportError as exc:
        raise NoParquetReader(
            "neither pyarrow nor pandas is importable; install a parquet reader with "
            "'pip install pyarrow' and re-run"
        ) from exc


def convert_parquet_to_npz(
    parquet: Path,
    npz: Path,
    *,
    n_neurons: int,
    source_sha256: str,
) -> Dict[str, Any]:
    """Write ``npz`` with keys pre/post/weight/n_neurons/source_sha256 from ``parquet``."""
    import numpy as np

    started = time.time()
    pre_raw, post_raw, w_raw, reader = _read_parquet_columns(parquet)
    pre = np.asarray(pre_raw).astype(np.int32, copy=False)
    post = np.asarray(post_raw).astype(np.int32, copy=False)
    weight = np.asarray(w_raw).astype(np.float32, copy=False)
    if pre.shape != post.shape or pre.shape != weight.shape:
        raise ValueError("parquet columns have inconsistent lengths")
    if pre.size:
        lo = int(min(pre.min(), post.min()))
        hi = int(max(pre.max(), post.max()))
        if lo < 0 or hi >= n_neurons:
            raise ValueError(
                f"synapse indices span [{lo}, {hi}] but completeness lists {n_neurons} neurons"
            )
    npz.parent.mkdir(parents=True, exist_ok=True)
    part = npz.with_name(npz.name + ".part.npz")
    np.savez_compressed(
        part,
        pre=pre,
        post=post,
        weight=weight,
        n_neurons=np.int64(n_neurons),
        source_sha256=np.str_(source_sha256),
    )
    os.replace(part, npz)
    info = {
        "path": str(npz),
        "reader": reader,
        "n_synapses": int(pre.size),
        "n_neurons": int(n_neurons),
        "source_sha256": source_sha256,
        "keys": list(NPZ_KEYS),
        "seconds": round(time.time() - started, 2),
        "size": npz.stat().st_size,
    }
    _log(
        f"converted {parquet.name} -> {npz.name}: {pre.size} synapses, "
        f"{n_neurons} neurons via {reader} in {info['seconds']}s"
    )
    return info


def inspect_npz(npz: Path) -> Dict[str, Any]:
    """Describe an existing npz without loading the big arrays' contents into the manifest."""
    import numpy as np

    with np.load(npz, allow_pickle=False) as archive:
        keys = list(archive.files)
        info: Dict[str, Any] = {
            "path": str(npz),
            "keys": keys,
            "size": npz.stat().st_size,
            "keys_ok": all(k in keys for k in NPZ_KEYS),
        }
        if "pre" in keys:
            info["n_synapses"] = int(archive["pre"].shape[0])
        if "n_neurons" in keys:
            info["n_neurons"] = int(archive["n_neurons"])
        if "source_sha256" in keys:
            info["source_sha256"] = str(archive["source_sha256"])
    return info


def npz_matches_source(npz: Path, expected_source_sha: Optional[str]) -> bool:
    """True when ``npz`` exists, has every required key, and its source hash equals ``expected``."""
    if not npz.is_file() or not expected_source_sha:
        return False
    try:
        info = inspect_npz(npz)
    except Exception:
        return False
    return bool(info.get("keys_ok")) and info.get("source_sha256", "").lower() == (
        expected_source_sha.lower()
    )


# ---------------------------------------------------------------------------
# manifest
# ---------------------------------------------------------------------------


def build_manifest(dest_dir: Path, known: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """Hash whatever exists in ``dest_dir``; never fetches or converts."""
    known = KNOWN_SHA256 if known is None else known
    manifest: Dict[str, Any] = {
        "schema_version": "flybrain.fetch_manifest/v1",
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "data_dir": str(dest_dir),
        "upstream": UPSTREAM_RAW_BASE,
        "license": (
            "FlyWire v783 public release; FlyWire data terms apply (CC BY-NC 4.0 at time of "
            "writing). Not redistributed in Mycosoft repositories."
        ),
        "files": {},
        "npz": None,
        "ready": False,
    }
    for name in (COMPLETENESS_FILE, CONNECTIVITY_PARQUET):
        path = dest_dir / name
        if path.is_file():
            actual, ok = verify_file(path, known.get(name))
            manifest["files"][name] = {
                "path": str(path),
                "size": path.stat().st_size,
                "sha256": actual,
                "expected_sha256": known.get(name),
                "sha256_ok": ok,
            }
        else:
            rejected = dest_dir / (name + ".rejected")
            manifest["files"][name] = {
                "path": str(path),
                "present": False,
                "rejected_copy": str(rejected) if rejected.is_file() else None,
            }
    npz = dest_dir / CONNECTIVITY_NPZ
    if npz.is_file():
        try:
            info = inspect_npz(npz)
            expected = known.get(CONNECTIVITY_PARQUET)
            info["source_sha256_ok"] = (
                info.get("source_sha256", "").lower() == expected.lower() if expected else None
            )
            manifest["npz"] = info
        except Exception as exc:  # unreadable archive is reported, not hidden
            manifest["npz"] = {"path": str(npz), "error": str(exc)}
    comp = manifest["files"].get(COMPLETENESS_FILE, {})
    npz_info = manifest["npz"] or {}
    manifest["ready"] = bool(
        comp.get("sha256_ok") and npz_info.get("keys_ok") and npz_info.get("source_sha256_ok")
    )
    return manifest


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="flybrain_fetch_connectome",
        description=(
            "Fetch the FlyWire v783 connectome (completeness CSV + connectivity parquet) onto "
            "the NAS, verify SHA-256 and convert the parquet to npz for the FlyBrain module."
        ),
    )
    parser.add_argument(
        "--dest",
        type=Path,
        default=None,
        help="destination directory (default: FLYBRAIN_DATA_DIR / NAS / repo data/flybrain)",
    )
    parser.add_argument(
        "--source-dir",
        type=Path,
        default=None,
        help="copy the two files from this local directory instead of downloading",
    )
    parser.add_argument(
        "--no-verify",
        action="store_true",
        help="do not compare SHA-256 with the known values (hashes are still recorded)",
    )
    parser.add_argument(
        "--npz-only",
        action="store_true",
        help=(
            "keep only the npz on disk: skip fetching the parquet when a matching npz already "
            "exists, and delete the parquet after a successful conversion"
        ),
    )
    parser.add_argument(
        "--print-manifest",
        action="store_true",
        help="only hash what already exists in --dest and print the manifest (no fetch)",
    )
    return parser


def main(argv: Optional[list] = None) -> int:
    args = build_parser().parse_args(argv)
    dest_dir: Path = args.dest if args.dest is not None else config.resolve_data_dir()
    dest_dir = dest_dir.expanduser()

    if args.print_manifest:
        manifest = build_manifest(dest_dir)
        print(json.dumps(manifest, indent=2))
        return EXIT_OK

    dest_dir.mkdir(parents=True, exist_ok=True)
    verify = not args.no_verify
    result: Dict[str, Any] = {"steps": {}}
    npz_path = dest_dir / CONNECTIVITY_NPZ
    parquet_path = dest_dir / CONNECTIVITY_PARQUET
    known_parquet_sha = KNOWN_SHA256.get(CONNECTIVITY_PARQUET)

    try:
        result["steps"][COMPLETENESS_FILE] = ensure_file(
            COMPLETENESS_FILE, dest_dir, source_dir=args.source_dir, verify=verify
        )
        n_neurons = count_neurons(dest_dir / COMPLETENESS_FILE)

        if args.npz_only and npz_matches_source(npz_path, known_parquet_sha):
            _log(f"{CONNECTIVITY_NPZ}: present with matching source_sha256, skipping parquet")
            result["steps"][CONNECTIVITY_PARQUET] = {"action": "skipped (npz-only)"}
            result["steps"][CONNECTIVITY_NPZ] = dict(inspect_npz(npz_path), action="skipped")
        else:
            entry = ensure_file(
                CONNECTIVITY_PARQUET, dest_dir, source_dir=args.source_dir, verify=verify
            )
            result["steps"][CONNECTIVITY_PARQUET] = entry
            source_sha = entry["sha256"]
            if npz_matches_source(npz_path, source_sha):
                _log(f"{CONNECTIVITY_NPZ}: already derived from this parquet, skipping conversion")
                result["steps"][CONNECTIVITY_NPZ] = dict(inspect_npz(npz_path), action="skipped")
            else:
                result["steps"][CONNECTIVITY_NPZ] = dict(
                    convert_parquet_to_npz(
                        parquet_path, npz_path, n_neurons=n_neurons, source_sha256=source_sha
                    ),
                    action="converted",
                )
        if args.npz_only and parquet_path.is_file():
            parquet_path.unlink()
            _log(f"{CONNECTIVITY_PARQUET}: removed, npz retained (--npz-only)")
            result["steps"][CONNECTIVITY_PARQUET]["action"] += " + removed"
    except HashMismatch as exc:
        _log(f"ERROR: {exc}; file kept as {exc.path.name}.rejected")
        result["error"] = str(exc)
        result["manifest"] = build_manifest(dest_dir)
        print(json.dumps(result, indent=2))
        return EXIT_HASH_MISMATCH
    except NoParquetReader as exc:
        _log(f"ERROR: {exc}")
        result["error"] = str(exc)
        result["manifest"] = build_manifest(dest_dir)
        print(json.dumps(result, indent=2))
        return EXIT_NO_PARQUET_READER
    except (urllib.error.URLError, OSError, ValueError) as exc:
        _log(f"ERROR: {exc}")
        result["error"] = str(exc)
        result["manifest"] = build_manifest(dest_dir)
        print(json.dumps(result, indent=2))
        return EXIT_ERROR

    result["manifest"] = build_manifest(dest_dir)
    print(json.dumps(result, indent=2))
    return EXIT_OK if result["manifest"]["ready"] else EXIT_ERROR


if __name__ == "__main__":
    sys.exit(main())
