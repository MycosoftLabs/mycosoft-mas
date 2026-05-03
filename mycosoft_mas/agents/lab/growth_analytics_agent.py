"""
Growth analytics agent — summarizes latest MINDEX telemetry only.

When no samples exist, returns an explicit empty instrument narrative (no fabricated biomass curves).
"""

from __future__ import annotations

import logging
import os
from collections import defaultdict
from typing import Any, Dict, List

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


class GrowthAnalyticsAgent(BaseAgent):
    """Aggregates device telemetry streams from MINDEX for lab growth context."""

    def __init__(self, agent_id: str, name: str, config: Dict[str, Any]):
        super().__init__(agent_id=agent_id, name=name, config=config or {})
        self.capabilities = ["telemetry_summary", "growth_context"]

    async def _fetch_latest_samples(self, limit: int, offset: int) -> List[Dict[str, Any]]:
        headers = _mindex_headers()
        if "X-Internal-Token" not in headers and "X-API-Key" not in headers:
            return []
        url = f"{_mindex_base()}/telemetry/devices/latest"
        params = {"limit": max(1, min(limit, 200)), "offset": max(0, offset)}
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                r = await client.get(url, headers=headers, params=params)
                r.raise_for_status()
                payload = r.json()
                if isinstance(payload, dict):
                    data = payload.get("data")
                    if isinstance(data, list):
                        return [x for x in data if isinstance(x, dict)]
                return []
        except Exception as exc:
            logger.warning("GrowthAnalyticsAgent telemetry fetch failed: %s", exc)
            return []

    async def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        task_type = task.get("type", "summarize_telemetry")
        if task_type != "summarize_telemetry":
            return {
                "status": "error",
                "message": "unsupported_task",
                "result": {"detail": "Use type=summarize_telemetry"},
            }

        limit = int(task.get("limit") or 50)
        offset = int(task.get("offset") or 0)
        rows = await self._fetch_latest_samples(limit=limit, offset=offset)
        if not rows:
            return {
                "status": "success",
                "result": {
                    "has_instrument_data": False,
                    "narrative": "No MINDEX telemetry samples returned — connect MycoBrain or ingest before growth analytics can reflect live instruments.",
                    "sample_count": 0,
                    "devices": [],
                },
            }

        by_device: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        for row in rows:
            slug = str(row.get("device_slug") or row.get("device_name") or "unknown")
            by_device[slug].append(row)

        devices_out = []
        for slug, samples in by_device.items():
            keys = {str(s.get("stream_key") or "metric") for s in samples}
            latest = max(
                (s.get("recorded_at") or "" for s in samples),
                default="",
            )
            devices_out.append(
                {
                    "device_slug": slug,
                    "stream_keys": sorted(keys),
                    "latest_recorded_at": latest,
                    "sample_rows": len(samples),
                }
            )

        narrative = (
            f"MINDEX reports {len(rows)} recent telemetry sample rows across {len(by_device)} device(s). "
            "Use stream keys (temperature, humidity, gas, etc.) for environmental scoring — "
            "this summary does not infer biomass without calibrated models on those streams."
        )

        return {
            "status": "success",
            "result": {
                "has_instrument_data": True,
                "narrative": narrative,
                "sample_count": len(rows),
                "devices": devices_out,
                "pagination": {"limit": limit, "offset": offset},
            },
        }
