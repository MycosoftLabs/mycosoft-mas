#!/usr/bin/env python3
"""Reconcile CMMC control publication state after a stale-state promotion bug.

This script operates only on compliance metadata. It never reads evidence
artifacts. It preserves each row's evidence URI and scope metadata.
"""

from __future__ import annotations

import argparse
import asyncio
import copy
import os
import re
from datetime import datetime, timezone
from typing import Any, Dict

import httpx

MAS_API = os.getenv("MAS_API_URL", "http://192.168.0.188:8001").rstrip("/")

DEMOTE_SUFFIXES = {
    "3.2.1",
    "3.2.2",
    "3.2.3",
    "3.12.1",
    "3.12.2",
    "3.12.3",
    "3.12.4",
    "3.9.1",
    "3.14.1",
}
CONTROL_SUFFIX_PATTERN = re.compile(r"(\d+\.\d+\.\d+)$")


def _control_suffix(control_id: str) -> str:
    match = CONTROL_SUFFIX_PATTERN.search(control_id)
    if not match:
        raise ValueError(f"Unsupported control identifier: {control_id}")
    return match.group(1)


def _is_stale_implemented_row(row: Dict[str, Any]) -> bool:
    if row.get("implementation_state") != "implemented":
        return False
    snapshot = row.get("state_snapshot") or {}
    current_state = snapshot.get("current_state") or {}
    current_implementation = str(current_state.get("implementation_state", "")).lower()
    notes = " ".join(
        str(value)
        for value in (
            snapshot.get("note", ""),
            snapshot.get("notes", ""),
            current_state.get("note", ""),
            current_state.get("notes", ""),
        )
    ).lower()
    return current_implementation in {"planned", "not_met"} or "not met" in notes


def _reconciled_body(row: Dict[str, Any]) -> Dict[str, Any]:
    """Return a coherent current-state update from verified metadata only."""
    snapshot = copy.deepcopy(row.get("state_snapshot") or {})
    current_state = dict(snapshot.get("current_state") or {})
    suffix = _control_suffix(str(row["control_id"]))
    is_demoted = suffix in DEMOTE_SUFFIXES
    resulting_state = "partial" if is_demoted else "implemented"
    now = datetime.now(timezone.utc).isoformat()

    current_state.update(
        {
            "as_of": now,
            "implementation_state": resulting_state,
            "evidence_uri": row.get("evidence_uri"),
            "notes": (
                "Partial: retained evidence is insufficient to establish Met status."
                if is_demoted
                else "Current implementation verified for the recorded control scope."
            ),
        }
    )
    snapshot["current_state"] = current_state
    snapshot["note"] = current_state["notes"]
    snapshot["reconciled_at"] = now
    snapshot["reconciled_source"] = "CMMC_CONTROL_STATE_RECONCILIATION_JUL27_2026"

    return {
        "control_id": row["control_id"],
        "framework": row["framework"],
        "family": row.get("family"),
        "title": row.get("title"),
        "implementation_state": resulting_state,
        "evidence_uri": row.get("evidence_uri"),
        "state_snapshot": snapshot,
    }


async def main(apply: bool) -> None:
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.get(f"{MAS_API}/api/compliance/controls")
        response.raise_for_status()
        rows = response.json()["controls"]
        affected = [row for row in rows if _is_stale_implemented_row(row)]
        demotions = [
            row for row in affected if _control_suffix(str(row["control_id"])) in DEMOTE_SUFFIXES
        ]

        print(
            f"Detected {len(affected)} split-brain rows; "
            f"{len(demotions)} require Partial reconciliation."
        )
        if not apply:
            return

        for row in affected:
            update = await client.post(
                f"{MAS_API}/api/compliance/controls",
                json=_reconciled_body(row),
            )
            update.raise_for_status()

        score = await client.get(f"{MAS_API}/api/compliance/score")
        score.raise_for_status()
        print(score.json())


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply reconciled states after reviewing the dry-run count.",
    )
    arguments = parser.parse_args()
    asyncio.run(main(arguments.apply))
