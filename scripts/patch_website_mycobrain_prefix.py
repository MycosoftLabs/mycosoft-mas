#!/usr/bin/env python3
"""
Patch the Website repo MycoBrain service to support Cloudflare-routed /api/mycobrain/* paths.

Why:
- The sandbox VM cloudflared ingress routes `/api/mycobrain*` directly to the Windows LAN
  MycoBrain service (port 8003).
- That upstream service historically exposed routes at `/health`, `/ports`, `/devices`, ...
- Without adding prefixed aliases, `GET /api/mycobrain/ports` returns 404 and Cloudflare
  routing appears broken even when the service is healthy.

This script adds prefixed aliases by duplicating decorators (idempotent).
"""

from __future__ import annotations

from pathlib import Path


WEBSITE_MYCOSOFT_ROOT = Path(r"C:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website")
TARGET = WEBSITE_MYCOSOFT_ROOT / "services" / "mycobrain" / "mycobrain_service.py"


def replace_once(haystack: str, needle: str, replacement: str) -> str:
    if needle not in haystack:
        raise ValueError(f"Expected to find: {needle!r}")
    if haystack.count(needle) != 1:
        raise ValueError(f"Expected 1 occurrence of {needle!r}, found {haystack.count(needle)}")
    return haystack.replace(needle, replacement)


def ensure_prefixed_alias(src: str, base: str, prefixed: str) -> str:
    """
    If the prefixed decorator already exists, do nothing.
    Otherwise, insert it directly under the base decorator line.
    """
    base_line = f'@app.{base}'
    pref_line = f'@app.{prefixed}'

    if pref_line in src:
        return src
    return replace_once(src, base_line, base_line + "\n" + pref_line)


def main() -> None:
    if not TARGET.exists():
        raise SystemExit(f"[ERROR] Target file not found: {TARGET}")

    original = TARGET.read_text(encoding="utf-8")
    updated = original

    # Duplicate the route decorators so both legacy and Cloudflare-prefixed paths work.
    mappings = [
        ('get("/health")', 'get("/api/mycobrain/health")'),
        ('get("/ports")', 'get("/api/mycobrain/ports")'),
        ('get("/devices")', 'get("/api/mycobrain/devices")'),
        ('post("/devices/connect/{port}")', 'post("/api/mycobrain/devices/connect/{port}")'),
        ('post("/devices/disconnect/{port}")', 'post("/api/mycobrain/devices/disconnect/{port}")'),
        ('get("/devices/{port}/status")', 'get("/api/mycobrain/devices/{port}/status")'),
        ('get("/devices/{port}/sensors")', 'get("/api/mycobrain/devices/{port}/sensors")'),
        ('get("/devices/{port}/diagnostics")', 'get("/api/mycobrain/devices/{port}/diagnostics")'),
        ('post("/devices/{port}/neopixel")', 'post("/api/mycobrain/devices/{port}/neopixel")'),
        ('post("/devices/{port}/buzzer")', 'post("/api/mycobrain/devices/{port}/buzzer")'),
        ('post("/devices/{port}/command")', 'post("/api/mycobrain/devices/{port}/command")'),
        ('websocket("/ws/{port}")', 'websocket("/api/mycobrain/ws/{port}")'),
    ]

    for base, prefixed in mappings:
        updated = ensure_prefixed_alias(updated, base=base, prefixed=prefixed)

    if updated == original:
        print("[OK] No changes needed (prefixed aliases already present).")
        return

    TARGET.write_text(updated, encoding="utf-8")
    print("[OK] Patched:", TARGET)
    print("Next: restart the Windows MycoBrain service on port 8003.")


if __name__ == "__main__":
    main()

