#!/usr/bin/env python3
"""Flip PS.L2-3.9.2 + NIST twin 3.9.2 to implemented (RJ Access Agreement signed)."""

from __future__ import annotations

import asyncio
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import httpx

MAS_API = os.getenv("MAS_API_URL", "http://192.168.0.188:8001").rstrip("/")
CONTROL_IDS = ("PS.L2-3.9.2", "3.9.2")
EVIDENCE_URI = "doc:access-agreement#EV-PS-001"
BACKUP_DIR = Path(__file__).resolve().parents[2] / "docs" / "cmmc_evidence"

EVIDENCE = {
    "register_id": "EV-PS-001",
    "artifact": "docs/cmmc_evidence/ps/PS_L2-3.9.2_RJ_Access_Agreement_SIGNED_JUL2026.pdf",
    "sha256": "b2a49cec9d291eade0737baa5ba96d6fc9777cb3406b99174884290eab0dc435",
    "bytes": 319846,
    "signer": "Raljoseph Ricasata (RJ Ricasata, CFO)",
    "signed_date": "2026-07-15",
    "sao_validated": "2026-07-22",
    "envelope": "AC00FC6C-EDA2-84FE-82C7-391A5236C1D9",
}


def _merge_snapshot(existing: dict) -> dict:
    merged = dict(existing or {})
    current_state = dict(merged.get("current_state") or {})
    current_state.update(
        {
            "as_of": datetime.now(timezone.utc).isoformat(),
            "implementation_state": "implemented",
            "evidence_uri": EVIDENCE_URI,
            "notes": f"Current implementation verified via {EVIDENCE_URI}.",
        }
    )
    merged["current_state"] = current_state
    merged["evidence_register_id"] = "EV-PS-001"
    merged["evidence"] = EVIDENCE
    merged["flip_source"] = "cursor_ps_l2_3_9_2_flip_jul22_2026"
    merged["flip_at"] = "2026-07-22"
    merged["note"] = (
        "RJ Access Agreement executed (DocuSign). SAO validated 2026-07-22. "
        "Met via doc:access-agreement#EV-PS-001."
    )
    return merged


async def main() -> None:
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.get(f"{MAS_API}/api/compliance/controls")
        resp.raise_for_status()
        controls = {c["control_id"]: c for c in resp.json().get("controls", [])}
        targets = [controls[cid] for cid in CONTROL_IDS if cid in controls]
        if len(targets) != 2:
            raise RuntimeError(f"Expected 2 controls, found {len(targets)}")

        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        backup_path = BACKUP_DIR / f"soc_ops_ps_3_9_2_flip_backup_{ts}.json"
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        backup_path.write_text(json.dumps(targets, indent=2), encoding="utf-8")
        print(f"Backup: {backup_path}")

        updated: list[str] = []
        for row in targets:
            body = {
                "control_id": row["control_id"],
                "framework": row["framework"],
                "family": row.get("family"),
                "title": row.get("title"),
                "implementation_state": "implemented",
                "evidence_uri": EVIDENCE_URI,
                "state_snapshot": _merge_snapshot(row.get("state_snapshot") or {}),
            }
            up = await client.post(f"{MAS_API}/api/compliance/controls", json=body)
            up.raise_for_status()
            updated.append(row["control_id"])

        score = await client.get(f"{MAS_API}/api/compliance/score")
        score.raise_for_status()
        print("Updated:", ", ".join(updated))
        print("Score:", json.dumps(score.json()))


if __name__ == "__main__":
    asyncio.run(main())
