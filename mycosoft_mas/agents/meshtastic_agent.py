"""
Meshtastic mesh network agent — health, route visibility, stale-node alerts.

Shares mesh telemetry with CREP / defense agents via A2A when anomalies are detected.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import httpx

from mycosoft_mas.agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)


def _mas_base() -> str:
    return os.environ.get("MAS_API_URL", "http://192.168.0.188:8001").rstrip("/")


class MeshtasticAgent(BaseAgent):
    """
    Monitors Meshtastic data ingested via MQTT bridge / LoRa ingest.

    Task types (``task["type"]``):
    - ``mesh_health`` — fetch ``/api/meshtastic/stats``
    - ``mesh_routes`` — fetch route table from MAS
    - ``mesh_dead_nodes`` — flag nodes not heard within ``stale_hours`` (default 48)
    - ``mesh_full_scan`` — stats + routes + dead-node check; may emit A2A alerts
    """

    def __init__(
        self,
        agent_id: str = "meshtastic-agent",
        name: str = "MeshtasticAgent",
        config: Optional[Dict[str, Any]] = None,
    ):
        cfg = config or {}
        super().__init__(agent_id=agent_id, name=name, config=cfg)
        self.capabilities = [
            "mesh_health",
            "mesh_routes",
            "mesh_dead_nodes",
            "mesh_full_scan",
        ]
        self.stale_hours = float(cfg.get("stale_hours", 48))
        self._last_dead_alert: Optional[str] = None

    async def _mas_get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        url = f"{_mas_base()}/api/meshtastic{path}"
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.get(url, params=params or {})
            r.raise_for_status()
            return r.json()

    async def _handle_mesh_health(self, _task: Dict[str, Any]) -> Dict[str, Any]:
        try:
            stats = await self._mas_get("/stats")
            return {"status": "success", "result": stats}
        except Exception as exc:  # noqa: BLE001
            logger.exception("mesh_health failed")
            return {"status": "error", "message": str(exc)}

    async def _handle_mesh_routes(self, task: Dict[str, Any]) -> Dict[str, Any]:
        limit = int(task.get("limit", 500))
        try:
            data = await self._mas_get("/routes", {"limit": limit})
            return {"status": "success", "result": data}
        except Exception as exc:  # noqa: BLE001
            logger.exception("mesh_routes failed")
            return {"status": "error", "message": str(exc)}

    def _parse_last_heard(self, raw: Any) -> Optional[datetime]:
        if raw is None:
            return None
        if isinstance(raw, datetime):
            return raw if raw.tzinfo else raw.replace(tzinfo=timezone.utc)
        if isinstance(raw, str):
            try:
                s = raw.replace("Z", "+00:00")
                dt = datetime.fromisoformat(s)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt
            except ValueError:
                return None
        return None

    async def _handle_mesh_dead_nodes(self, task: Dict[str, Any]) -> Dict[str, Any]:
        stale_h = float(task.get("stale_hours", self.stale_hours))
        threshold = datetime.now(timezone.utc) - timedelta(hours=stale_h)
        try:
            nodes_resp = await self._mas_get("/nodes", {"limit": 2000, "offset": 0})
            items: List[Dict[str, Any]] = nodes_resp.get("items") or []
            dead: List[Dict[str, Any]] = []
            for row in items:
                lh = self._parse_last_heard(row.get("last_heard_at"))
                if lh is None or lh < threshold:
                    dead.append(
                        {
                            "node_id": row.get("node_id"),
                            "long_name": row.get("long_name"),
                            "last_heard_at": row.get("last_heard_at"),
                        }
                    )
            return {
                "status": "success",
                "result": {
                    "stale_hours": stale_h,
                    "threshold_utc": threshold.isoformat(),
                    "dead_count": len(dead),
                    "dead_nodes": dead[:200],
                },
            }
        except Exception as exc:  # noqa: BLE001
            logger.exception("mesh_dead_nodes failed")
            return {"status": "error", "message": str(exc)}

    async def _maybe_alert_dead_nodes(self, dead_payload: Dict[str, Any]) -> None:
        count = int(dead_payload.get("dead_count") or 0)
        if count == 0:
            return
        digest = f"{count}:{dead_payload.get('threshold_utc')}"
        if digest == self._last_dead_alert:
            return
        self._last_dead_alert = digest
        content = {
            "kind": "meshtastic_stale_nodes",
            "dead_count": count,
            "sample": (dead_payload.get("dead_nodes") or [])[:10],
            "threshold_utc": dead_payload.get("threshold_utc"),
        }
        recipients = self.config.get("alert_recipient_agent_ids")
        try:
            await self.share_with_agents(
                content,
                tags=["meshtastic", "crep", "defense"],
                importance=0.65,
                recipients=recipients if isinstance(recipients, list) else None,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("share_with_agents (mesh alert) failed: %s", exc)

    async def _handle_mesh_full_scan(self, task: Dict[str, Any]) -> Dict[str, Any]:
        health = await self._handle_mesh_health(task)
        routes = await self._handle_mesh_routes(task)
        dead = await self._handle_mesh_dead_nodes(task)
        out: Dict[str, Any] = {
            "status": "success",
            "health": health,
            "routes": routes,
            "dead_nodes": dead,
        }
        if dead.get("status") == "success":
            res = dead.get("result") or {}
            if int(res.get("dead_count") or 0) > 0 and task.get("alert", True):
                await self._maybe_alert_dead_nodes(res)
        return out

    async def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        task_type = task.get("type", "")
        handlers = {
            "mesh_health": self._handle_mesh_health,
            "mesh_routes": self._handle_mesh_routes,
            "mesh_dead_nodes": self._handle_mesh_dead_nodes,
            "mesh_full_scan": self._handle_mesh_full_scan,
        }
        handler = handlers.get(task_type)
        if handler:
            return await handler(task)
        return {"status": "error", "message": f"Unknown task type: {task_type}"}
