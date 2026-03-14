"""
CREP Bridge — Live worldview and map control from Common Relevant Environmental Picture.

Fetches situational awareness: aviation, maritime, satellites, weather, fungal layer.
Executes CREP map actions via MAS /api/crep/command for autonomous MYCA control.

References: CREP dashboard at /natureos/crep, /dashboard/crep; MAS has crep-agent, crep-collector.
CREP_COMMAND_CONTRACT_MAR13_2026 defines the canonical command schema.

Date: 2026-03-02 (updated 2026-03-13 for autonomy integration)
"""

import os
import logging
from typing import Any, Dict, Optional

import aiohttp

logger = logging.getLogger("myca.os.crep_bridge")


class CREPBridge:
    """Bridge to CREP (Common Relevant Environmental Picture) for live worldview and map control."""

    def __init__(self, os_ref):
        self._os = os_ref
        self._session: Optional[aiohttp.ClientSession] = None
        self._mas_url = os.getenv("MAS_API_URL", "http://192.168.0.188:8001").rstrip("/")

    async def initialize(self):
        self._session = aiohttp.ClientSession()
        logger.info("CREP Bridge initialized")

    async def cleanup(self):
        if self._session and not self._session.closed:
            await self._session.close()

    async def get_worldview_summary(self) -> str:
        """
        Fetch a short text summary of current environmental situation.
        Returns a human-readable summary for LLM context, or empty string on failure.
        """
        if not self._session or self._session.closed:
            return ""

        try:
            async with self._session.get(
                f"{self._mas_url}/api/crep/stream/status",
                timeout=aiohttp.ClientTimeout(total=5),
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    connections = data.get("active_connections", 0)
                    return f"CREP stream: {connections} active dashboard connection(s). Environmental data (aviation, maritime, satellites, weather) available when collectors are running."
            return "CREP: Stream status unknown."
        except Exception as e:
            logger.debug("CREP worldview fetch failed: %s", e)
        return ""

    async def execute_crep_action(
        self,
        tool_name: str,
        args: Dict[str, Any],
        *,
        confirmed: bool = False,
    ) -> Dict[str, Any]:
        """
        Execute a CREP map action via MAS /api/crep/command.

        Args:
            tool_name: CREP tool name (e.g. crep_fly_to, crep_show_layer).
            args: Tool arguments (e.g. {"center": [139.69, 35.69], "zoom": 10}).
            confirmed: Set True for commands that require confirmation (e.g. crep_clear_filters).

        Returns:
            {"success": bool, "frontend_command": dict?, "speak": str?, "error": str?}
        """
        if not self._session or self._session.closed:
            return {"success": False, "error": "CREP bridge session not initialized"}

        try:
            async with self._session.post(
                f"{self._mas_url}/api/crep/command",
                json={"tool": tool_name, "args": args, "confirmed": confirmed},
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return {
                        "success": data.get("success", False),
                        "frontend_command": data.get("frontend_command"),
                        "speak": data.get("speak"),
                        "requires_confirmation": data.get("requires_confirmation", False),
                        "error": data.get("error"),
                    }
                body = await resp.text()
                return {
                    "success": False,
                    "error": f"MAS returned {resp.status}: {body[:200]}",
                }
        except Exception as e:
            logger.warning("CREP action failed: %s", e)
            return {"success": False, "error": str(e)}

    async def get_view_context(self) -> Dict[str, Any]:
        """Request current viewport/timeline context from CREP dashboard."""
        result = await self.execute_crep_action("crep_get_view_context", {})
        if result.get("success") and result.get("frontend_command"):
            return {"context": result["frontend_command"], "success": True}
        return {"success": False, "error": result.get("error", "Unknown")}

    async def get_entity_details(self, entity: Dict[str, Any]) -> Dict[str, Any]:
        """Request details for an entity (plane, vessel, etc.)."""
        result = await self.execute_crep_action("crep_get_entity_details", {"entity": entity})
        if result.get("success") and result.get("frontend_command"):
            return {"details": result["frontend_command"], "success": True}
        return {"success": False, "error": result.get("error", "Unknown")}
