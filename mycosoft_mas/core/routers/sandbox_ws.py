"""
Sandbox WebSocket Router

FastAPI WebSocket endpoint for sandbox daemon connections.
Node daemons inside ephemeral containers connect here; the Gateway
routes tool requests through these connections.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)

router = APIRouter(tags=["sandbox"])


@router.websocket("/ws/sandbox/{sandbox_id}")
async def sandbox_ws(
    websocket: WebSocket,
    sandbox_id: str,
    token: Optional[str] = Query(None),
):
    """WebSocket endpoint for sandbox daemon connections."""
    await websocket.accept()
    logger.info("Sandbox %s attempting WebSocket connection", sandbox_id)

    gateway = getattr(websocket.app.state, "gateway", None)
    sandbox_mgr = getattr(websocket.app.state, "sandbox_manager", None)

    if gateway is None:
        await websocket.send_json(
            {"type": "error", "payload": {"error": "Gateway not initialized"}}
        )
        await websocket.close()
        return

    try:
        handshake = await websocket.receive_json()
        if handshake.get("type") != "handshake":
            await websocket.send_json({"type": "error", "payload": {"error": "Expected handshake"}})
            await websocket.close()
            return

        hs_token = handshake.get("payload", {}).get("token", "")
        if not hs_token:
            logger.warning("Sandbox %s rejected: no token provided", sandbox_id)
            await websocket.send_json(
                {"type": "error", "payload": {"error": "Authentication token required"}}
            )
            await websocket.close(code=4001)
            return

        if sandbox_mgr:
            sandboxes = await sandbox_mgr.list_sandboxes()
            valid = any(s.sandbox_id == sandbox_id and s.token == hs_token for s in sandboxes)
            if not valid:
                logger.warning("Sandbox %s rejected: invalid token", sandbox_id)
                await websocket.send_json(
                    {"type": "error", "payload": {"error": "Invalid sandbox token"}}
                )
                await websocket.close(code=4003)
                return
        else:
            logger.warning(
                "Sandbox %s rejected: SandboxManager unavailable, cannot validate", sandbox_id
            )
            await websocket.send_json(
                {"type": "error", "payload": {"error": "Cannot validate sandbox token"}}
            )
            await websocket.close(code=4002)
            return

        gateway.register_sandbox_connection(sandbox_id, websocket)
        await websocket.send_json(
            {
                "type": "handshake_ack",
                "payload": {"status": "connected", "sandbox_id": sandbox_id},
            }
        )

        while True:
            msg = await websocket.receive_json()
            if msg.get("type") == "heartbeat":
                if sandbox_mgr:
                    info = sandbox_mgr._sandboxes.get(sandbox_id)
                    if info:
                        import time

                        info.last_activity = time.time()
                continue

            logger.debug("Sandbox %s message: %s", sandbox_id, msg.get("type"))

    except WebSocketDisconnect:
        logger.info("Sandbox %s disconnected", sandbox_id)
    except Exception as exc:
        logger.error("Sandbox %s error: %s", sandbox_id, exc)
    finally:
        gateway.unregister_sandbox_connection(sandbox_id)
