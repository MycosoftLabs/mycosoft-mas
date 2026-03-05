"""
OpenWork Bridge — Connects MYCA OS to OpenCode for coding tasks.

Uses the OpenCode REST API (opencode serve on 127.0.0.1:4096):
- POST /session — create session
- POST /session/:id/message — send prompt and get response (synchronous)

When OpenCode is available, coding tasks are routed here instead of Claude Code CLI.
Fallback to run_claude_code when OpenCode is down.

Date: 2026-03-05
"""

import asyncio
import logging
import os
from typing import Any, Dict, Optional

import aiohttp

logger = logging.getLogger("myca.os.openwork")


class OpenWorkBridge:
    """Bridge to OpenCode server for autonomous coding tasks."""

    def __init__(self, os_ref: Any):
        self._os = os_ref
        self._session: Optional[aiohttp.ClientSession] = None
        self._base_url = os.getenv("OPENCODE_URL", "http://127.0.0.1:4096")

    async def initialize(self) -> None:
        """Create aiohttp session."""
        self._session = aiohttp.ClientSession()
        logger.info("OpenWorkBridge initialized (OpenCode at %s)", self._base_url)

    async def cleanup(self) -> None:
        """Close aiohttp session."""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None

    async def health_check(self) -> Dict[str, Any]:
        """Check if OpenCode server is reachable."""
        if not self._session:
            await self.initialize()
        try:
            async with self._session.get(f"{self._base_url}/global/health") as r:
                ok = r.status == 200
                body = await r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
                return {"healthy": ok, "status": r.status, "detail": body}
        except Exception as e:
            logger.debug("OpenCode health check failed: %s", e)
            return {"healthy": False, "error": str(e)}

    async def run_task(self, prompt: str, title: Optional[str] = None) -> Dict[str, Any]:
        """
        Run a coding task via OpenCode: create session, send message, return result.
        """
        if not self._session:
            await self.initialize()
        try:
            # Create session
            async with self._session.post(
                f"{self._base_url}/session",
                json={"title": title or "MYCA coding task"},
            ) as r:
                if r.status != 200:
                    return {"status": "failed", "error": f"Session create failed: {r.status}"}
                session_data = await r.json()
            session_id = session_data.get("id") or session_data.get("sessionID")
            if not session_id:
                return {"status": "failed", "error": "No session ID in response"}

            # Send message and get response (synchronous endpoint)
            async with self._session.post(
                f"{self._base_url}/session/{session_id}/message",
                json={"parts": [{"type": "text", "text": prompt}]},
            ) as r:
                if r.status != 200:
                    return {"status": "failed", "error": f"Message failed: {r.status}"}
                msg_data = await r.json()

            # Extract text from response parts
            parts = msg_data.get("parts", []) or msg_data.get("info", {}).get("parts", [])
            texts = [
                p.get("text", "") or p.get("content", "")
                for p in parts
                if isinstance(p, dict) and (p.get("type") == "text" or "text" in p or "content" in p)
            ]
            output = "\n".join(t for t in texts if t)

            return {
                "status": "completed",
                "output": output[:5000],
                "returncode": 0,
                "summary": f"OpenCode task: {prompt[:100]}",
            }
        except asyncio.TimeoutError:
            return {"status": "timeout", "summary": "OpenCode task timed out"}
        except Exception as e:
            logger.warning("OpenWork run_task failed: %s", e)
            return {"status": "failed", "error": str(e)}
