"""
MCP Progress Notifier - February 9, 2026

Publishes progress to Redis agents:tool_calls for Agent Bus integration.
Used by task_management_server and mcp_memory_server for long-running operations.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


async def emit_progress(
    tool_name: str,
    progress: int,
    total: int,
    message: str = "",
    extra: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Emit progress notification to Redis agents:tool_calls.
    Non-blocking; failures are logged but do not raise.
    """
    try:
        from mycosoft_mas.realtime.redis_pubsub import get_client, Channel

        client = await get_client()
        if not client.is_connected():
            return
        data = {
            "type": "progress",
            "tool": tool_name,
            "progress": progress,
            "total": total,
            "message": message,
            **(extra or {}),
        }
        await client.publish(
            Channel.AGENTS_TOOL_CALLS.value,
            data,
            source=f"mcp:{tool_name}",
        )
    except ImportError:
        pass
    except Exception as e:
        logger.debug("MCP progress emit failed: %s", e)
