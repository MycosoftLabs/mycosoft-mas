#!/usr/bin/env python3
"""Probe Mycosoft UniFi gateway for CISA KEV CVE-2026-34908/09/10 exposure."""

from __future__ import annotations

import json
import os
import ssl
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

DEFAULT_HOST = os.environ.get("UNIFI_HOST", "192.168.0.1")
DEFAULT_PORT = int(os.environ.get("UNIFI_KEV_CHECK_PORT", "443"))
SCRIPT_DIR = Path(__file__).resolve().parent
DETECTOR = SCRIPT_DIR / "cve_2026_34908_check.py"


def ensure_detector() -> Path:
    if DETECTOR.exists():
        return DETECTOR
    url = "https://raw.githubusercontent.com/BishopFox/CVE-2026-34908-check/main/cve_2026_34908_check.py"
    urllib.request.urlretrieve(url, DETECTOR)
    return DETECTOR


def fingerprint(host: str, port: int) -> dict:
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    url = f"https://{host}:{port}/"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "MycosoftUniFiKEVProbe/1.0"})
        with urllib.request.urlopen(req, context=ctx, timeout=10) as resp:
            body = resp.read(4000).decode("utf-8", "replace")
            markers = [
                m
                for m in ("UniFi OS", "UniFi", "UDM", "Dream Machine", "ubiquiti")
                if m.lower() in body.lower()
            ]
            return {
                "reachable": True,
                "status": resp.status,
                "is_unifi_os": bool(markers),
                "markers": markers,
            }
    except Exception as exc:  # noqa: BLE001
        return {"reachable": False, "error": str(exc), "is_unifi_os": False}


def run_detector(host: str, port: int) -> dict:
    detector = ensure_detector()
    target = f"{host}:{port}"
    proc = subprocess.run(
        [sys.executable, str(detector), target, "--json"],
        capture_output=True,
        text=True,
        timeout=45,
        check=False,
    )
    if proc.returncode not in (0, 1, 2):
        return {"target": target, "verdict": "ERROR", "error": proc.stderr.strip() or proc.stdout.strip()}
    try:
        data = json.loads(proc.stdout)
        return data[0] if isinstance(data, list) and data else {"raw": proc.stdout}
    except json.JSONDecodeError:
        return {"target": target, "verdict": "ERROR", "error": proc.stdout.strip() or proc.stderr.strip()}


def main() -> int:
    host = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_HOST
    port = int(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_PORT
    report = {
        "host": host,
        "port": port,
        "cves": ["CVE-2026-34908", "CVE-2026-34909", "CVE-2026-34910"],
        "fingerprint": fingerprint(host, port),
        "detector": run_detector(host, port),
        "remediation": "Upgrade UniFi OS Server to 5.0.8+ (Ubiquiti SAB-064)",
    }
    print(json.dumps(report, indent=2))
    verdict = report.get("detector", {}).get("verdict", "")
    return 1 if verdict == "VULNERABLE" else 0


if __name__ == "__main__":
    raise SystemExit(main())
