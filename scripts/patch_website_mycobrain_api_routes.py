#!/usr/bin/env python3
"""
Patch the Website repo (Next.js) /api/mycobrain routes to be sandbox-safe:
- Add /api/mycobrain/health endpoint (so infra can healthcheck via Cloudflare).
- Reduce fetch timeouts so Cloudflare doesn't return 504.
- Never return mock data: return empty arrays + explicit errors quickly.

Note: These files live in the Website repo, not this MAS repo.
"""

from __future__ import annotations

from pathlib import Path


WEBSITE_ROOT = Path(r"C:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website")

ROUTE_ROOT = WEBSITE_ROOT / "app" / "api" / "mycobrain"
ROUTE_DEVICES = ROUTE_ROOT / "route.ts"
ROUTE_PORTS = ROUTE_ROOT / "ports" / "route.ts"
ROUTE_HEALTH_DIR = ROUTE_ROOT / "health"
ROUTE_HEALTH = ROUTE_HEALTH_DIR / "route.ts"


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def replace_all(src: str, old: str, new: str) -> str:
    if old not in src:
        raise ValueError(f"Expected to find: {old!r}")
    return src.replace(old, new)


def main() -> None:
    if not WEBSITE_ROOT.exists():
        raise SystemExit(f"[ERROR] Website repo not found: {WEBSITE_ROOT}")
    for p in (ROUTE_DEVICES, ROUTE_PORTS):
        if not p.exists():
            raise SystemExit(f"[ERROR] Missing website route file: {p}")

    # 1) Add /api/mycobrain/health
    health_content = """import { NextResponse } from \"next/server\"\n\nexport const dynamic = \"force-dynamic\"\n\nconst MYCOBRAIN_SERVICE_URL = process.env.MYCOBRAIN_SERVICE_URL || \"http://localhost:8003\"\n\nexport async function GET() {\n  try {\n    const res = await fetch(`${MYCOBRAIN_SERVICE_URL}/health`, {\n      signal: AbortSignal.timeout(3000),\n    }).catch(() => null)\n\n    if (!res?.ok) {\n      return NextResponse.json(\n        {\n          status: \"unhealthy\",\n          serviceUrl: MYCOBRAIN_SERVICE_URL,\n          error: \"MycoBrain service not reachable\",\n          timestamp: new Date().toISOString(),\n        },\n        { status: 503 }\n      )\n    }\n\n    const data = await res.json().catch(() => ({}))\n    return NextResponse.json({ ...data, serviceUrl: MYCOBRAIN_SERVICE_URL })\n  } catch (error) {\n    return NextResponse.json(\n      {\n        status: \"error\",\n        serviceUrl: MYCOBRAIN_SERVICE_URL,\n        error: \"MycoBrain health check failed\",\n        details: String(error),\n        timestamp: new Date().toISOString(),\n      },\n      { status: 503 }\n    )\n  }\n}\n"""
    write_text(ROUTE_HEALTH, health_content)

    # 2) Tighten /ports route timeouts and avoid 500-on-timeout
    ports_src = read_text(ROUTE_PORTS)
    ports_updated = ports_src
    ports_updated = replace_all(ports_updated, "AbortSignal.timeout(10000)", "AbortSignal.timeout(3000)")
    # Catch should be 503 to avoid Cloudflare surfacing 5xx that look like server crashes
    ports_updated = replace_all(
        ports_updated,
        "{ ports: [], error: \"Failed to fetch ports\", details: String(error) },\n      { status: 500 }",
        "{ ports: [], error: \"Failed to fetch ports\", details: String(error), serviceUrl: MYCOBRAIN_SERVICE_URL },\n      { status: 503 }",
    )
    if ports_updated != ports_src:
        write_text(ROUTE_PORTS, ports_updated)

    # 3) Tighten top-level /api/mycobrain route timeouts to avoid 504s
    devices_src = read_text(ROUTE_DEVICES)
    devices_updated = devices_src
    devices_updated = replace_all(devices_updated, "AbortSignal.timeout(5000)", "AbortSignal.timeout(3000)")
    devices_updated = replace_all(devices_updated, "AbortSignal.timeout(2000)", "AbortSignal.timeout(1500)")
    if devices_updated != devices_src:
        write_text(ROUTE_DEVICES, devices_updated)

    print("[OK] Patched Website /api/mycobrain routes:")
    print(" -", ROUTE_HEALTH)
    print(" -", ROUTE_PORTS)
    print(" -", ROUTE_DEVICES)
    print("\nNext: ensure the sandbox website container has MYCOBRAIN_SERVICE_URL=http://192.168.0.172:18003 and rebuild/recreate if needed.")


if __name__ == "__main__":
    main()

