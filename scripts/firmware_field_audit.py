#!/usr/bin/env python3
"""One-shot field firmware audit — probes serial :8003 and Jetson agents."""

from __future__ import annotations

import asyncio
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from mycosoft_mas.devices.firmware_audit import (  # noqa: E402
    CANONICAL_SIDE_A_VERSION,
    COMPATIBILITY_MATRIX,
    probe_agent,
    probe_openclaw,
    score_firmware,
)

TARGETS = [
    {
        "label": "Local serial (MycoBrain service)",
        "device_id": "local-serial-com7",
        "agent_url": os.environ.get("MYCOBRAIN_SERVICE_URL", "http://127.0.0.1:8003"),
        "openclaw_url": None,
    },
    {
        "label": "Mushroom 1 Jetson",
        "device_id": "mycobrain-mushroom1-jetson-123",
        "agent_url": "http://192.168.0.123:8787",
        "openclaw_url": "http://192.168.0.123:18789",
    },
    {
        "label": "Hyphae 1 Jetson",
        "device_id": "mycobrain-hyphae1-jetson-228",
        "agent_url": "http://192.168.0.228:8787",
        "openclaw_url": "http://192.168.0.228:18789",
    },
]


async def audit_target(target: dict) -> dict:
    agent_probe = await probe_agent(target["agent_url"])
    oc_probe: dict = {"reachable": False}
    if target.get("openclaw_url"):
        oc_probe = await probe_openclaw(target["openclaw_url"])

    fw = str(agent_probe.get("fw_version") or "")
    tier, missing, action = score_firmware(fw, [], agent_probe, oc_probe)
    return {
        "label": target["label"],
        "device_id": target["device_id"],
        "agent_url": target["agent_url"],
        "openclaw_url": target.get("openclaw_url"),
        "firmware_version": fw,
        "compatibility_tier": tier,
        "missing_capabilities": missing,
        "recommended_action": action,
        "agent_probe": agent_probe,
        "openclaw_probe": oc_probe,
    }


async def main() -> None:
    results = []
    for t in TARGETS:
        results.append(await audit_target(t))

    doc_path = ROOT / "docs" / "FIRMWARE_AUDIT_MAY27_2026.md"
    lines = [
        "# Firmware Audit — May 27, 2026",
        "",
        f"**Date:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        "**Status:** Complete (automated probe)",
        f"**Canonical Side A target:** `{CANONICAL_SIDE_A_VERSION}`",
        "",
        "## Summary",
        "",
    ]
    for r in results:
        lines.append(
            f"- **{r['label']}** (`{r['device_id']}`): tier **{r['compatibility_tier']}**, "
            f"firmware `{r['firmware_version'] or 'unknown'}`"
        )
    lines.extend(["", "## Probe details", ""])
    for r in results:
        lines.append(f"### {r['label']}")
        lines.append(f"- Agent: `{r['agent_url']}` — reachable={r['agent_probe'].get('reachable')}")
        if r.get("openclaw_url"):
            lines.append(
                f"- OpenClaw: `{r['openclaw_url']}` — reachable={r['openclaw_probe'].get('reachable')}"
            )
        lines.append(f"- Recommended: {r['recommended_action']}")
        lines.append("")
        lines.append("```json")
        lines.append(json.dumps(r, indent=2)[:4000])
        lines.append("```")
        lines.append("")

    lines.extend(["## Compatibility matrix", ""])
    for row in COMPATIBILITY_MATRIX:
        lines.append(f"- **{row['capability']}** — {row['label']} (min: {row.get('min_firmware', 'n/a')})")

    doc_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {doc_path}")
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
