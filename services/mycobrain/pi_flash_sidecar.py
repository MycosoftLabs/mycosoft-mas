#!/usr/bin/env python3
"""Hyphae Pi host-side ESP32 flash sidecar (SSH fallback when OpenClaw :18789 unavailable).

Usage on Pi:
  python3 pi_flash_sidecar.py --port /dev/ttyACM0 --artifact /path/to/merged.bin --dry-run
  APPROVE_FLASH=true python3 pi_flash_sidecar.py --port /dev/ttyACM0 --artifact ... --confirm

Created: May 29, 2026
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def run_flash(port: str, artifact: Path, dry_run: bool, confirm: bool) -> dict:
    job_id = f"pi-flash-{uuid.uuid4().hex[:12]}"
    job: dict = {
        "job_id": job_id,
        "port": port,
        "artifact": str(artifact),
        "dry_run": dry_run,
        "confirm": confirm,
        "created_at": _utc_now(),
    }

    if not artifact.is_file():
        job["state"] = "failed"
        job["error"] = f"artifact not found: {artifact}"
        return job

    job["artifact_sha256"] = sha256_file(artifact)
    approve = os.getenv("APPROVE_FLASH", "").strip().lower() in ("1", "true", "yes")

    if dry_run:
        cmd = [sys.executable, "-m", "esptool", "--chip", "esp32s3", "--port", port, "chip_id"]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=45)
        job["state"] = "dry_run_ok" if proc.returncode == 0 else "dry_run_partial"
        job["output_tail"] = (proc.stdout or proc.stderr or "")[-1500:]
        return job

    if not (confirm and approve):
        job["state"] = "approval_required"
        job["error"] = "Set --confirm and APPROVE_FLASH=true for live write"
        return job

    # Pause recovery operator if listening on 8787 (best-effort)
    try:
        subprocess.run(
            ["systemctl", "stop", "mycobrain-recovery-operator"],
            capture_output=True,
            timeout=15,
        )
    except Exception:
        pass

    cmd = [
        sys.executable,
        "-m",
        "esptool",
        "--chip",
        "esp32s3",
        "--port",
        port,
        "--baud",
        "921600",
        "--before",
        "default_reset",
        "--after",
        "hard_reset",
        "write_flash",
        "0x0",
        str(artifact),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    out = (proc.stdout or "") + (proc.stderr or "")
    job["output_tail"] = out[-2000:]
    job["state"] = "success" if proc.returncode == 0 else "failed"
    if proc.returncode != 0:
        job["error"] = f"esptool exit {proc.returncode}"

    try:
        subprocess.run(["systemctl", "start", "mycobrain-recovery-operator"], capture_output=True, timeout=15)
    except Exception:
        pass

    job["updated_at"] = _utc_now()
    return job


def main() -> int:
    parser = argparse.ArgumentParser(description="Pi ESP32 flash sidecar for Hyphae-1")
    parser.add_argument("--port", default="/dev/ttyACM0")
    parser.add_argument("--artifact", required=True)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--confirm", action="store_true")
    args = parser.parse_args()

    result = run_flash(args.port, Path(args.artifact), args.dry_run, args.confirm)
    print(json.dumps(result, indent=2))
    audit = Path(os.getenv("PI_FLASH_AUDIT_LOG", "/tmp/pi_firmware_flash_jobs.jsonl"))
    with audit.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(result) + "\n")
    return 0 if result.get("state") in ("success", "dry_run_ok", "dry_run_partial", "approval_required") else 1


if __name__ == "__main__":
    raise SystemExit(main())
