"""
Maps live SOC signals into soc_ops.compliance_controls rows (NIST 800-171 seed).
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


def _db_ready() -> bool:
    return bool(os.getenv("MINDEX_DATABASE_URL") or os.getenv("DATABASE_URL"))


# Minimal starter controls — expanded from TACO mapping over time.
_SEED_CONTROLS: List[Dict[str, Any]] = [
    {
        "control_id": "3.1.1",
        "family": "Access Control",
        "title": "Limit information system access to authorized users",
    },
    {
        "control_id": "3.1.12",
        "family": "Access Control",
        "title": "Monitor / control remote access sessions",
    },
    {
        "control_id": "3.4.1",
        "family": "Configuration Management",
        "title": "Establish baseline configurations",
    },
    {
        "control_id": "3.14.1",
        "family": "System / Communications Protection",
        "title": "Monitor / control communications at external boundaries",
    },
]


async def refresh_control_state_from_signals() -> Dict[str, Any]:
    """
    Pull device inventory + incident + redteam counts and upsert control snapshots.
    """
    if not _db_ready():
        return {"ok": False, "reason": "no_database_url"}

    from mycosoft_mas.soc import repository as soc_repo

    devices = await soc_repo.list_device_inventory(limit=2000)
    incidents = await soc_repo.list_incidents(limit=200)
    open_incidents = [i for i in incidents if (i.get("status") or "") not in ("resolved", "closed")]
    unknown_devices = [d for d in devices if (d.get("classified_as") or "") == "unknown"]

    # Heuristic state: boundary monitoring partial if UniFi-sourced devices exist
    unifi = sum(1 for d in devices if d.get("source") == "unifi")

    updates = 0
    for c in _SEED_CONTROLS:
        snap: Dict[str, Any] = {
            "device_count": len(devices),
            "open_incidents": len(open_incidents),
            "unknown_devices": len(unknown_devices),
            "unifi_clients": unifi,
        }
        state = "unknown"
        if c["control_id"] == "3.14.1":
            state = "implemented" if unifi > 0 else "partial"
        elif c["control_id"] == "3.1.1":
            state = "partial" if devices else "unknown"
        elif c["control_id"] == "3.1.12":
            state = "partial" if unknown_devices else "implemented"
        elif c["control_id"] == "3.4.1":
            state = "partial"

        await soc_repo.upsert_compliance_control(
            control_id=c["control_id"],
            framework="NIST_800_171",
            family=c["family"],
            title=c["title"],
            implementation_state=state,
            evidence_uri=None,
            state_snapshot=snap,
        )
        updates += 1

    logger.info("refresh_control_state_from_signals: upserted %s controls", updates)
    return {"ok": True, "controls_upserted": updates}

