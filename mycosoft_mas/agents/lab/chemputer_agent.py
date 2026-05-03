"""
Chemputer agent — experiment-plan hints for compounds that exist in MINDEX only.

No mock compounds: resolves structure via MINDEX GET /compounds/{id} using service credentials.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, Optional

import httpx

from mycosoft_mas.agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)


def _mindex_base() -> str:
    base = os.environ.get("MINDEX_API_URL", "http://192.168.0.189:8000").rstrip("/")
    if not base.endswith("/api/mindex"):
        base = f"{base}/api/mindex"
    return base


def _mindex_headers() -> Dict[str, str]:
    token = os.environ.get("MINDEX_INTERNAL_TOKEN", "").strip()
    key = os.environ.get("MINDEX_API_KEY", "").strip()
    if token:
        return {"X-Internal-Token": token, "Accept": "application/json"}
    if key:
        return {"X-API-Key": key, "Accept": "application/json"}
    return {"Accept": "application/json"}


class ChemputerAgent(BaseAgent):
    """Plans downstream chemistry steps from MINDEX-backed compound records."""

    def __init__(self, agent_id: str, name: str, config: Dict[str, Any]):
        super().__init__(agent_id=agent_id, name=name, config=config or {})
        self.capabilities = ["chemputer_plan", "mindex_compounds"]

    async def _fetch_compound(self, compound_id: str) -> Optional[Dict[str, Any]]:
        if not compound_id or not str(compound_id).strip():
            return None
        headers = _mindex_headers()
        if "X-Internal-Token" not in headers and "X-API-Key" not in headers:
            logger.warning("ChemputerAgent: MINDEX credentials not configured")
            return None
        url = f"{_mindex_base()}/compounds/{compound_id.strip()}"
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                r = await client.get(url, headers=headers)
                if r.status_code == 404:
                    return None
                r.raise_for_status()
                data = r.json()
                return data if isinstance(data, dict) else None
        except Exception as exc:
            logger.warning("ChemputerAgent MINDEX fetch failed: %s", exc)
            return None

    async def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        task_type = task.get("type", "plan_compound")
        if task_type != "plan_compound":
            return {
                "status": "error",
                "message": "unsupported_task",
                "result": {"detail": "Use type=plan_compound with compound_id"},
            }

        compound_id = task.get("compound_id")
        smiles_in = (task.get("smiles") or "").strip()
        if smiles_in:
            return {
                "status": "error",
                "message": "smiles_not_accepted_without_mindex_resolution",
                "result": {
                    "detail": "Provide compound_id from MINDEX only; raw SMILES is not accepted in MVP.",
                },
            }

        record = await self._fetch_compound(str(compound_id))
        if not record:
            return {
                "status": "error",
                "message": "compound_not_found_or_mindex_unreachable",
                "result": {},
            }

        name = record.get("name") or record.get("compound_name") or "Compound"
        formula = record.get("formula") or record.get("molecular_formula")
        mw = record.get("molecular_weight")
        inchikey = record.get("inchikey")

        steps = [
            {
                "step": 1,
                "action": "Confirm identity",
                "detail": f"Cross-check {name} using MINDEX record fields (formula={formula!s}, MW={mw!s}).",
            },
            {
                "step": 2,
                "action": "Stereochemistry / registry linkage",
                "detail": f"Use InChIKey {inchikey!s} when present for unambiguous structure validation.",
            },
            {
                "step": 3,
                "action": "Analytical queue",
                "detail": "Schedule LC–MS / NMR only after structure confirmation — no simulated spectra in MVP.",
            },
        ]

        return {
            "status": "success",
            "result": {
                "agent": self.name,
                "compound_id": str(compound_id),
                "mindex_record": record,
                "experiment_plan": {"steps": steps, "source": "mindex_only"},
            },
        }
