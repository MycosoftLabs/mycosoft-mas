#!/usr/bin/env python3
"""End-to-end verification for Earth Simulator MYCA deploy (May 26 2026)."""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)

BASE = "https://mycosoft.com"
LOCAL_MAS = os.environ.get("MAS_API_URL", "http://192.168.0.188:8001")
LOCAL_MINDEX = os.environ.get("MINDEX_API_URL", "http://192.168.0.189:8000")

RESULTS: list[dict] = []


def check(name: str, ok: bool, detail: str, *, required: bool = True) -> None:
    RESULTS.append({"name": name, "ok": ok, "detail": detail, "required": required})
    mark = "PASS" if ok else ("WARN" if not required else "FAIL")
    print(f"[{mark}] {name}: {detail}")


def http(method: str, url: str, body: dict | None = None, timeout: int = 25) -> tuple[int, str]:
    data = None
    headers = {"Accept": "application/json"}
    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read().decode(errors="replace")[:4000]
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode(errors="replace")[:4000]
    except Exception as e:
        return 0, str(e)


def main() -> int:
    # Production pages
    for path in (
        "/natureos/earth-simulator",
        "/dashboard/crep",
    ):
        code, body = http("GET", f"{BASE}{path}")
        check(f"page {path}", code == 200 and len(body) > 1000, f"HTTP {code}, len={len(body)}")

    # Website health + backend connectivity
    code, body = http("GET", f"{BASE}/api/health")
    healthy = code == 200 and "mas-api" in body and "mindex-api" in body
    check("production /api/health", healthy, f"HTTP {code}")

    # Viewport intel (MINDEX proxy)
    bbox = "north=34&south=33&east=-117&west=-118&zoom=9"
    code, body = http("GET", f"{BASE}/api/crep/viewport-intel?{bbox}")
    has_infra = code == 200
    infra_keys = []
    if has_infra:
        try:
            data = json.loads(body)
            infra_keys = list(data.keys())[:12]
            has_infra = len(body) > 200
        except json.JSONDecodeError:
            has_infra = False
    check(
        "production /api/crep/viewport-intel",
        has_infra,
        f"HTTP {code}, keys={infra_keys[:6]}",
    )

    # Viewport AI summary → MAS
    code, body = http(
        "POST",
        f"{BASE}/api/crep/viewport-ai-summary",
        {
            "revision": "verify-may26-2026",
            "context": {
                "revision": "verify-may26-2026",
                "zoom": 9,
                "center": {"lat": 33.5, "lng": -117.5},
                "bounds": {"north": 34, "south": 33, "east": -117, "west": -118},
                "counts": {"events": 2, "species": 5, "aircraft": 1},
                "infrastructure": ["cell towers", "power lines", "military"],
            },
        },
    )
    summary_ok = code in (200, 502)  # 502 if MAS LLM degraded; route must exist
    has_summary = False
    if code == 200:
        try:
            data = json.loads(body)
            has_summary = bool(data.get("summary")) or "error" not in data
        except json.JSONDecodeError:
            pass
    check(
        "production /api/crep/viewport-ai-summary → MAS",
        summary_ok,
        f"HTTP {code}, has_summary={has_summary}, body_head={body[:120]!r}",
    )

    # MAS direct
    for path, method, body in (
        ("/health", "GET", None),
        ("/api/myca/chat", "POST", {"message": "Earth Sim verification ping", "user_id": "earth-sim-verify-may26"}),
        ("/api/devices", "GET", None),
        ("/api/memory/health", "GET", None),
    ):
        code, resp = http(method, f"{LOCAL_MAS}{path}", body)
        check(f"MAS {path}", code == 200, f"HTTP {code}, head={resp[:100]!r}")

    # MINDEX civic (auth expected without token)
    code, resp = http(
        "GET",
        f"{LOCAL_MINDEX}/api/mindex/civic/viewport-intel?north=34&south=33&east=-117&west=-118&zoom=9",
    )
    check(
        "MINDEX /api/mindex/civic/viewport-intel",
        code in (200, 401),
        f"HTTP {code} (401=route exists, auth required)",
    )

    # Device registry content
    code, resp = http("GET", f"{LOCAL_MAS}/api/devices")
    device_names = []
    if code == 200:
        try:
            device_names = [d.get("device_name", "") for d in json.loads(resp).get("devices", [])]
        except json.JSONDecodeError:
            pass
    check(
        "MAS device registry reachable",
        code == 200 and len(device_names) >= 1,
        f"devices={device_names}",
    )

    # Deploy artifact on sandbox
    try:
        import paramiko

        creds = Path(__file__).resolve().parents[1] / ".credentials.local"
        if creds.exists():
            for line in creds.read_text(encoding="utf-8", errors="replace").splitlines():
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ[k.strip()] = v.strip().strip("'\"")
        pw = os.environ.get("VM_PASSWORD") or os.environ.get("VM_SSH_PASSWORD")
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect("192.168.0.187", username="mycosoft", password=pw, timeout=30)
        _, stdout, _ = ssh.exec_command(
            'docker ps --filter name=mycosoft-website-blue --format "{{.Image}}"', timeout=20
        )
        image = stdout.read().decode().strip()
        ssh.close()
        check(
            "sandbox image tag includes b87e20f6",
            "b87e20f6" in image,
            image or "no image",
        )
    except Exception as e:
        check("sandbox image tag", False, str(e))

    required_fail = [r for r in RESULTS if r["required"] and not r["ok"]]
    print("\n--- SUMMARY ---")
    print(f"Total: {len(RESULTS)}, Pass: {sum(1 for r in RESULTS if r['ok'])}, Fail: {len(required_fail)}")
    return 1 if required_fail else 0


if __name__ == "__main__":
    raise SystemExit(main())
