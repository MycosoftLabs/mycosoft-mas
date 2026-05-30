"""Host-side ESP32 flash via esptool for MycoBrain service (Phase 0 COM4)."""

from __future__ import annotations

import hashlib
import json
import logging
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import httpx

logger = logging.getLogger(__name__)

ALLOWED_PORTS_RAW = os.getenv("MYCOBRAIN_ALLOWED_PORTS", "").strip()
ALLOWED_PORTS = {p.strip() for p in ALLOWED_PORTS_RAW.split(",") if p.strip()}
DEFAULT_PORT = os.getenv("MYCOBRAIN_SERIAL_PORT", "COM4")
DEVICE_ROLE = os.getenv("MYCOBRAIN_DEVICE_ROLE", "standalone")
REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "data"
AUDIT_LOG = DATA_DIR / "firmware_flash_jobs.jsonl"
ARTIFACT_DIR = Path(os.getenv("MYCOBRAIN_FIRMWARE_ARTIFACT_DIR", str(DATA_DIR / "firmware_artifacts")))

_jobs: Dict[str, Dict[str, Any]] = {}
_jobs_lock = threading.Lock()


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _append_audit(entry: Dict[str, Any]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with AUDIT_LOG.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, default=str) + "\n")


def esptool_available() -> bool:
    try:
        import esptool  # noqa: F401

        return True
    except ImportError:
        return bool(shutil.which("esptool") or shutil.which("esptool.py"))


def _resolve_port(port: Optional[str]) -> str:
    chosen = (port or DEFAULT_PORT).strip()
    if ALLOWED_PORTS and chosen not in ALLOWED_PORTS:
        raise ValueError(f"Port {chosen} not in MYCOBRAIN_ALLOWED_PORTS={sorted(ALLOWED_PORTS)}")
    return chosen


def _validate_profile(profile: str, confirm: bool) -> None:
    if not profile or not profile.strip():
        raise ValueError("profile is required")
    expected = DEVICE_ROLE.strip().lower()
    got = profile.strip().lower()
    if expected not in ("standalone", "") and got != expected and not confirm:
        raise ValueError(
            f"profile mismatch: request={got} service_role={expected} (set confirm=true to override)"
        )


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _resolve_artifact(
    *,
    artifact_url: Optional[str],
    artifact_path: Optional[str],
    version: Optional[str],
    profile: Optional[str] = None,
) -> Path:
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)

    if artifact_path:
        p = Path(artifact_path)
        if not p.is_file():
            raise FileNotFoundError(f"artifact_path not found: {p}")
        return p

    if artifact_url:
        parsed = urlparse(artifact_url)
        if parsed.scheme not in ("http", "https", "file"):
            raise ValueError(f"Unsupported artifact_url scheme: {parsed.scheme}")
        if parsed.scheme == "file":
            p = Path(parsed.path)
            if not p.is_file():
                raise FileNotFoundError(f"file URL not found: {p}")
            return p
        dest = ARTIFACT_DIR / f"download_{uuid.uuid4().hex[:12]}.bin"
        with httpx.Client(timeout=120.0, follow_redirects=True) as client:
            r = client.get(artifact_url)
            r.raise_for_status()
            dest.write_bytes(r.content)
        return dest

    if version:
        profile_key = (profile or "").strip().lower()
        if profile_key:
            profile_candidates = list(ARTIFACT_DIR.glob(f"**/*{version}*_{profile_key}_*.bin"))
            if profile_candidates:
                return profile_candidates[0]
        candidates = list(ARTIFACT_DIR.glob(f"**/*{version}*.bin"))
        if not candidates:
            candidates = list(ARTIFACT_DIR.glob(f"*{version}*.bin"))
        if not candidates:
            raise FileNotFoundError(
                f"No local artifact for version={version} profile={profile_key or 'any'} under {ARTIFACT_DIR}. "
                "Publish merged.bin or pass artifact_url."
            )
        return candidates[0]

    raise ValueError("One of artifact_url, artifact_path, or version is required")


def _build_esptool_cmd(port: str, bin_path: Path, dry_run: bool) -> List[str]:
    base = [sys.executable, "-m", "esptool", "--chip", "esp32s3", "--port", port, "--baud", "921600"]
    if dry_run:
        base.extend(["chip_id"])
    else:
        base.extend(
            [
                "--before",
                "default_reset",
                "--after",
                "hard_reset",
                "write_flash",
                "0x0",
                str(bin_path),
            ]
        )
    return base


def _serial_port_probe(port: str) -> Dict[str, Any]:
    try:
        import serial

        ser = serial.Serial(port, 115200, timeout=1)
        ser.close()
        return {"ok": True}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def _run_preflight(port: str, bin_path: Optional[Path], dry_run: bool) -> Dict[str, Any]:
    if dry_run:
        if esptool_available():
            cmd = [sys.executable, "-m", "esptool", "--chip", "esp32s3", "--port", port, "chip_id"]
            try:
                proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                out = (proc.stdout or "") + (proc.stderr or "")
                if proc.returncode == 0:
                    return {"ok": True, "method": "esptool_chip_id", "output_tail": out[-500:]}
            except Exception as exc:
                return {"ok": False, "error": str(exc), "method": "esptool_chip_id"}
        return _serial_port_probe(port)

    if not esptool_available():
        return {"ok": False, "error": "esptool not installed (pip install esptool>=4.7)"}

    cmd = _build_esptool_cmd(port, bin_path or Path("NUL"), dry_run=False)
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        out = (proc.stdout or "") + (proc.stderr or "")
        ok = proc.returncode == 0
        return {"ok": ok, "cmd": cmd, "returncode": proc.returncode, "output_tail": out[-2000:]}
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "esptool flash timed out", "cmd": cmd}
    except Exception as exc:
        return {"ok": False, "error": str(exc), "cmd": cmd}


def create_flash_job(
    *,
    profile: str,
    version: Optional[str] = None,
    artifact_url: Optional[str] = None,
    artifact_path: Optional[str] = None,
    port: Optional[str] = None,
    confirm: bool = False,
    dry_run: bool = True,
    sha256_expected: Optional[str] = None,
) -> Dict[str, Any]:
    _validate_profile(profile, confirm)
    serial_port = _resolve_port(port)
    job_id = f"flash-{uuid.uuid4().hex[:12]}"

    job: Dict[str, Any] = {
        "job_id": job_id,
        "state": "requested",
        "profile": profile,
        "version": version,
        "port": serial_port,
        "dry_run": dry_run,
        "confirm": confirm,
        "created_at": _utc_now(),
        "updated_at": _utc_now(),
        "progress_pct": 0,
        "log_tail": [],
    }

    approve_flash = os.getenv("APPROVE_FLASH", "").strip().lower() in ("1", "true", "yes")
    if not dry_run and not (confirm and approve_flash):
        job["state"] = "failed"
        job["error"] = (
            "Destructive flash blocked: set confirm=true on request AND APPROVE_FLASH=true in service env"
        )
        _append_audit(job)
        with _jobs_lock:
            _jobs[job_id] = job
        return job

    try:
        artifact: Optional[Path] = None
        artifact_error: Optional[str] = None
        try:
            artifact = _resolve_artifact(
                artifact_url=artifact_url, artifact_path=artifact_path, version=version, profile=profile
            )
            job["artifact"] = str(artifact)
            job["artifact_sha256"] = _sha256_file(artifact)
            if sha256_expected and sha256_expected.lower() != job["artifact_sha256"]:
                raise ValueError("sha256 mismatch — refused to flash tampered artifact")
        except (FileNotFoundError, ValueError) as exc:
            artifact_error = str(exc)
            if not dry_run:
                raise

        preflight = _run_preflight(serial_port, artifact, dry_run=dry_run)
        job["preflight"] = preflight
        if artifact_error:
            job["artifact_warning"] = artifact_error

        if dry_run:
            job["state"] = "dry_run_ok" if preflight.get("ok") else "dry_run_partial"
            if not preflight.get("ok"):
                job["error"] = preflight.get("error") or "serial port probe failed"
            job["progress_pct"] = 100 if preflight.get("ok") else 50
            parts = ["Dry-run: esptool available"]
            if preflight.get("ok"):
                parts.insert(0, "port reachable")
            if artifact:
                parts.append(f"artifact sha256={job.get('artifact_sha256', '')[:12]}...")
            elif artifact_error:
                parts.append(f"artifact missing: {artifact_error}")
            job["message"] = "; ".join(parts)
            _append_audit(job)
            with _jobs_lock:
                _jobs[job_id] = job
            return job

        if artifact is None:
            raise ValueError(artifact_error or "artifact required for live flash")

        if not preflight.get("ok"):
            job["state"] = "failed"
            job["error"] = preflight.get("error") or "preflight failed"
            _append_audit(job)
            with _jobs_lock:
                _jobs[job_id] = job
            return job

        job["state"] = "flashing"
        job["updated_at"] = _utc_now()
        # Release serial before esptool write
        cmd = _build_esptool_cmd(serial_port, artifact, dry_run=False)
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        out = (proc.stdout or "") + (proc.stderr or "")
        job["log_tail"] = out.splitlines()[-50:]
        if proc.returncode != 0:
            job["state"] = "failed"
            job["error"] = f"esptool exit {proc.returncode}"
        else:
            job["state"] = "success"
            job["progress_pct"] = 100
        job["updated_at"] = _utc_now()
        _append_audit(job)
        with _jobs_lock:
            _jobs[job_id] = job
        return job

    except Exception as exc:
        job["state"] = "failed"
        job["error"] = str(exc)
        job["updated_at"] = _utc_now()
        _append_audit(job)
        with _jobs_lock:
            _jobs[job_id] = job
        return job


def get_flash_job(job_id: str) -> Optional[Dict[str, Any]]:
    with _jobs_lock:
        return _jobs.get(job_id)


def list_flash_jobs(limit: int = 20) -> List[Dict[str, Any]]:
    with _jobs_lock:
        items = list(_jobs.values())
    items.sort(key=lambda j: j.get("created_at", ""), reverse=True)
    return items[:limit]
