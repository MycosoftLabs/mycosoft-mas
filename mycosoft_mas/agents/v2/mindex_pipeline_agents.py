"""
MINDEX App Overhaul (May 03, 2026) — pipeline agents calling real MINDEX APIs only.

No mock payloads: empty or error when MINDEX is unreachable or credentials unset.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List

import httpx

from mycosoft_mas.runtime import AgentCategory, AgentTask

from .base_agent_v2 import BaseAgentV2


def _mindex_base() -> str:
    return os.environ.get("MINDEX_API_URL", "http://192.168.0.189:8000").rstrip("/")


def _mas_base() -> str:
    return os.environ.get("MAS_API_URL", "http://192.168.0.188:8001").rstrip("/")


def _mindex_headers() -> dict[str, str]:
    headers: dict[str, str] = {"Accept": "application/json", "Content-Type": "application/json"}
    token = os.environ.get("MINDEX_INTERNAL_TOKEN", "").strip()
    if token:
        headers["X-Internal-Token"] = token
        return headers
    key = os.environ.get("MINDEX_API_KEY", "").strip()
    if key:
        headers["X-API-Key"] = key
    return headers


def _anchor_thresholds() -> dict[str, float]:
    raw = os.environ.get("MINDEX_ANCHOR_TIER_THRESHOLDS", "").strip()
    if not raw:
        return {"defense": 50_000.0, "research": 10_000.0, "default": 0.0}
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, dict):
            return {str(k): float(v) for k, v in parsed.items()}
    except (json.JSONDecodeError, TypeError, ValueError):
        pass
    return {"defense": 50_000.0, "research": 10_000.0, "default": 0.0}


class AnchorRouterAgent(BaseAgentV2):
    """Select anchor tier from score thresholds; POST anchors to MINDEX ledger."""

    @property
    def agent_type(self) -> str:
        return "anchor_router"

    @property
    def category(self) -> str:
        return AgentCategory.DATA.value

    @property
    def display_name(self) -> str:
        return "MINDEX Anchor Router"

    @property
    def description(self) -> str:
        return "Routes content-hash anchors to MINDEX ledger with tier policy"

    def get_capabilities(self) -> List[str]:
        return ["select_tier", "post_anchor", "fusarium_defense_gate"]

    async def on_start(self):
        self.register_handler("select_tier", self._select_tier)
        self.register_handler("post_anchor", self._post_anchor)
        self.register_handler("fusarium_defense_gate", self._fusarium_gate)

    async def _select_tier(self, task: AgentTask) -> Dict[str, Any]:
        score = float(task.payload.get("score") or 0)
        thresholds = _anchor_thresholds()
        tier = "default"
        if score >= thresholds.get("defense", 50_000):
            tier = "defense"
        elif score >= thresholds.get("research", 10_000):
            tier = "research"
        fusarium = bool(task.payload.get("fusarium_defense"))
        if fusarium and tier == "default":
            tier = "defense"
        return {"tier": tier, "score": score, "thresholds": thresholds, "fusarium_defense": fusarium}

    async def _post_anchor(self, task: AgentTask) -> Dict[str, Any]:
        body = {
            "entity_type": task.payload.get("entity_type", "taxon"),
            "entity_id": task.payload.get("entity_id", ""),
            "content_hash_hex": task.payload.get("content_hash_hex", ""),
            "tier": task.payload.get("tier", "dag"),
        }
        if not body["entity_id"] or len(str(body["content_hash_hex"])) < 64:
            return {"status": "error", "detail": "entity_id and content_hash_hex (64 hex) required"}
        url = f"{_mindex_base()}/api/mindex/ledger/anchor"
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                r = await client.post(url, json=body, headers=_mindex_headers())
                data = r.json() if r.content else {}
                return {"status_code": r.status_code, "body": data}
        except httpx.HTTPError as e:
            return {"status": "error", "detail": str(e)}

    async def _fusarium_gate(self, task: AgentTask) -> Dict[str, Any]:
        """When FUSARIUM defense is active, force defense-tier routing metadata (no mock events)."""
        active = bool(task.payload.get("active", True))
        return {"fusarium_defense_active": active, "forced_tier": "defense" if active else None}


class DataSynthesisAgent(BaseAgentV2):
    """Triggers synthesis prep by reading real compound catalog slices from MINDEX."""

    @property
    def agent_type(self) -> str:
        return "data_synthesis"

    @property
    def category(self) -> str:
        return AgentCategory.DATA.value

    @property
    def display_name(self) -> str:
        return "MINDEX Data Synthesis"

    @property
    def description(self) -> str:
        return "Samples MINDEX compounds/taxa for downstream NLM / training jobs"

    def get_capabilities(self) -> List[str]:
        return ["sample_compounds", "sample_taxa"]

    async def on_start(self):
        self.register_handler("sample_compounds", self._sample_compounds)
        self.register_handler("sample_taxa", self._sample_taxa)

    async def _sample_compounds(self, task: AgentTask) -> Dict[str, Any]:
        limit = int(task.payload.get("limit") or 20)
        limit = max(1, min(limit, 200))
        url = f"{_mindex_base()}/api/mindex/compounds"
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                r = await client.get(url, params={"limit": limit, "offset": 0}, headers=_mindex_headers())
                data = r.json() if r.content else {}
                return {"status_code": r.status_code, "source": "mindex", "payload": data}
        except httpx.HTTPError as e:
            return {"status": "error", "detail": str(e)}

    async def _sample_taxa(self, task: AgentTask) -> Dict[str, Any]:
        limit = int(task.payload.get("limit") or 20)
        limit = max(1, min(limit, 200))
        url = f"{_mindex_base()}/api/mindex/taxa"
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                r = await client.get(url, params={"limit": limit}, headers=_mindex_headers())
                data = r.json() if r.content else {}
                return {"status_code": r.status_code, "source": "mindex", "payload": data}
        except httpx.HTTPError as e:
            return {"status": "error", "detail": str(e)}


class ChemistrySynthesisAgent(BaseAgentV2):
    """Prepares analogue / training dataset manifests from live MINDEX compound slices."""

    @property
    def agent_type(self) -> str:
        return "chemistry_synthesis"

    @property
    def category(self) -> str:
        return AgentCategory.DATA.value

    @property
    def display_name(self) -> str:
        return "MINDEX Chemistry Synthesis"

    @property
    def description(self) -> str:
        return "Builds dataset descriptors from MINDEX compounds for NLM / Petri training"

    def get_capabilities(self) -> List[str]:
        return ["export_compound_slice"]

    async def on_start(self):
        self.register_handler("export_compound_slice", self._export_compound_slice)

    async def _export_compound_slice(self, task: AgentTask) -> Dict[str, Any]:
        limit = int(task.payload.get("limit") or 50)
        limit = max(1, min(limit, 500))
        url = f"{_mindex_base()}/api/mindex/compounds"
        try:
            async with httpx.AsyncClient(timeout=45.0) as client:
                r = await client.get(url, params={"limit": limit, "offset": 0}, headers=_mindex_headers())
                data = r.json() if r.content else {}
                return {
                    "status_code": r.status_code,
                    "record_count": len((data.get("data") or data.get("results") or [])) if isinstance(data, dict) else 0,
                    "raw": data,
                }
        except httpx.HTTPError as e:
            return {"status": "error", "detail": str(e)}


class DataQAAgent(BaseAgentV2):
    """Compares MINDEX aggregate health vs explicit expectations (real API only)."""

    @property
    def agent_type(self) -> str:
        return "data_qa"

    @property
    def category(self) -> str:
        return AgentCategory.DATA.value

    @property
    def display_name(self) -> str:
        return "MINDEX Data QA"

    @property
    def description(self) -> str:
        return "Runs consistency checks against MINDEX /health/all"

    def get_capabilities(self) -> List[str]:
        return ["health_snapshot", "assert_minimum_taxa"]

    async def on_start(self):
        self.register_handler("health_snapshot", self._health_snapshot)
        self.register_handler("assert_minimum_taxa", self._assert_minimum_taxa)

    async def _health_snapshot(self, task: AgentTask) -> Dict[str, Any]:
        url = f"{_mindex_base()}/api/mindex/health/all"
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                r = await client.get(url, headers=_mindex_headers())
                data = r.json() if r.content else {}
                return {"status_code": r.status_code, "health_all": data}
        except httpx.HTTPError as e:
            return {"status": "error", "detail": str(e)}

    async def _assert_minimum_taxa(self, task: AgentTask) -> Dict[str, Any]:
        minimum = int(task.payload.get("minimum", 0))
        snap = await self._health_snapshot(task)
        if snap.get("status") == "error":
            return snap
        counts = (snap.get("health_all") or {}).get("counts") or {}
        taxon = counts.get("taxon")
        if taxon is None:
            return {"ok": False, "reason": "taxon_count_unavailable", "counts": counts}
        ok = int(taxon) >= minimum
        return {"ok": ok, "taxon_count": taxon, "minimum": minimum}


class DeviceDistributionAgent(BaseAgentV2):
    """Reads live MAS device registry + MINDEX network nodes for coverage-style reporting (no invented placements)."""

    @property
    def agent_type(self) -> str:
        return "device_distribution"

    @property
    def category(self) -> str:
        return AgentCategory.DATA.value

    @property
    def display_name(self) -> str:
        return "MINDEX Device Distribution"

    @property
    def description(self) -> str:
        return "Correlates MAS /api/devices with MINDEX /api/mindex/network/nodes for distribution snapshots"

    def get_capabilities(self) -> List[str]:
        return ["inventory_snapshot", "storage_nodes_snapshot"]

    async def on_start(self):
        self.register_handler("inventory_snapshot", self._inventory_snapshot)
        self.register_handler("storage_nodes_snapshot", self._storage_nodes_snapshot)

    async def _inventory_snapshot(self, task: AgentTask) -> Dict[str, Any]:
        del task
        url = f"{_mas_base()}/api/devices"
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                r = await client.get(url)
                data = r.json() if r.content else {}
                if isinstance(data, dict) and isinstance(data.get("count"), int):
                    n = int(data["count"])
                else:
                    devices = data.get("devices") if isinstance(data, dict) else None
                    n = len(devices) if isinstance(devices, list) else 0
                return {"status_code": r.status_code, "device_count": n, "raw": data}
        except httpx.HTTPError as e:
            return {"status": "error", "detail": str(e)}

    async def _storage_nodes_snapshot(self, task: AgentTask) -> Dict[str, Any]:
        del task
        url = f"{_mindex_base()}/api/mindex/network/nodes"
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                r = await client.get(url, headers=_mindex_headers())
                data = r.json() if r.content else {}
                nodes = data.get("items") or data.get("nodes") or data.get("data") or []
                count = len(nodes) if isinstance(nodes, list) else 0
                return {"status_code": r.status_code, "node_count": count, "raw": data}
        except httpx.HTTPError as e:
            return {"status": "error", "detail": str(e)}


class SequenceToolsAgent(BaseAgentV2):
    """Kingdom-gated sequence tooling (BLAST/MAFFT/etc.) — wire to external compute; no fake alignments."""

    @property
    def agent_type(self) -> str:
        return "sequence_tools"

    @property
    def category(self) -> str:
        return AgentCategory.DATA.value

    @property
    def display_name(self) -> str:
        return "MINDEX Sequence Tools"

    @property
    def description(self) -> str:
        return "Routes primer/ITS/COI/16S/rbcL/matK style jobs to configured executors (pending integration)"

    def get_capabilities(self) -> List[str]:
        return ["status", "submit_stub"]

    async def on_start(self):
        self.register_handler("status", self._status)
        self.register_handler("submit_stub", self._submit_stub)

    async def _status(self, task: AgentTask) -> Dict[str, Any]:
        del task
        return {
            "blast_web_configured": bool(os.environ.get("NCBI_BLAST_URL") or os.environ.get("BLAST_REST_URL")),
            "mafft_cli_configured": bool(os.environ.get("MAFFT_BIN")),
            "message": "Submit real jobs only when executors are configured; no mock alignments returned.",
        }

    async def _submit_stub(self, task: AgentTask) -> Dict[str, Any]:
        payload = task.payload if isinstance(task.payload, dict) else {}
        kingdom = str(payload.get("kingdom") or "").strip()
        tool = str(payload.get("tool") or "").strip().lower()
        if not kingdom or not tool:
            return {"ok": False, "reason": "kingdom_and_tool_required", "payload_keys": list(payload.keys())}
        return {
            "ok": False,
            "reason": "executor_not_wired",
            "kingdom": kingdom,
            "tool": tool,
            "hint": "Point BLAST/MAFFT workers via env and replace submit_stub with real dispatch.",
        }
