"""
A2A WebSocket Transport - February 9, 2026

WebSocket endpoint for A2A protocol with streaming responses.
Same SendMessageRequest/TaskModel schemas as HTTP. Feature flag: MYCA_A2A_WS_ENABLED.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict
from uuid import uuid4

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)

router = APIRouter(tags=["a2a-websocket"])

MYCA_A2A_WS_ENABLED = os.getenv("MYCA_A2A_WS_ENABLED", "false").lower() in ("1", "true", "yes")


def _sanitize_text(value: str, max_len: int = 50000) -> str:
    if not isinstance(value, str):
        return ""
    sanitized = "".join(c for c in value if ord(c) >= 32 and ord(c) != 127)
    return sanitized[:max_len]


def _extract_user_message(parts: list) -> str:
    if not parts:
        return ""
    texts = []
    for p in parts:
        if isinstance(p, dict) and p.get("text"):
            texts.append(_sanitize_text(str(p["text"]), 10000))
    return " ".join(texts).strip() or ""


@router.websocket("/a2a/v1/ws")
async def a2a_websocket(websocket: WebSocket) -> None:
    """
    A2A WebSocket - streaming message handling.
    Expects JSON messages with SendMessageRequest shape. Streams Task response.
    """
    if not MYCA_A2A_WS_ENABLED:
        await websocket.close(code=4003, reason="A2A WebSocket disabled")
        return

    await websocket.accept()
    session_context: Dict[str, Any] = {}

    try:
        while True:
            raw = await websocket.receive_text()
            data = json.loads(raw)
            msg = data.get("message") or data
            parts = msg.get("parts", [])
            user_text = _extract_user_message(parts)
            if not user_text:
                await websocket.send_json(
                    {
                        "type": "error",
                        "payload": {"message": "Message must contain at least one text part"},
                    }
                )
                continue

            context_id = msg.get("contextId") or session_context.get("context_id") or str(uuid4())
            task_id = str(uuid4())
            session_context["context_id"] = context_id

            # Stream through voice orchestrator
            try:
                from mycosoft_mas.core.routers.voice_orchestrator_api import (
                    VoiceOrchestratorRequest,
                    get_orchestrator,
                )

                orch = get_orchestrator()
                meta = data.get("metadata") or {}
                vo_req = VoiceOrchestratorRequest(
                    message=user_text,
                    conversation_id=context_id,
                    session_id=meta.get("session_id"),
                    user_id=meta.get("user_id") or "a2a-ws-client",
                    source="a2a-ws",
                    modality="text",
                    want_audio=False,
                )
                resp = await orch.process(vo_req)
                response_text = resp.response_text or resp.response or ""
            except Exception as e:
                logger.exception("A2A WS orchestration failed: %s", e)
                response_text = f"I encountered an error: {str(e)}"

            # Stream response in chunks (simulate streaming for now)
            chunk_size = 50
            for i in range(0, len(response_text), chunk_size):
                chunk = response_text[i : i + chunk_size]
                await websocket.send_json(
                    {
                        "type": "token",
                        "payload": {"text": chunk, "task_id": task_id},
                    }
                )

            now = datetime.now(timezone.utc).isoformat()
            await websocket.send_json(
                {
                    "type": "task",
                    "payload": {
                        "id": task_id,
                        "contextId": context_id,
                        "status": {"state": "TASK_STATE_COMPLETED", "timestamp": now},
                        "artifacts": [
                            {
                                "artifactId": str(uuid4()),
                                "name": "response",
                                "parts": [{"text": response_text, "mediaType": "text/plain"}],
                            }
                        ],
                    },
                }
            )
    except WebSocketDisconnect:
        logger.info("A2A WebSocket disconnected")
    except Exception as e:
        logger.error("A2A WebSocket error: %s", e, exc_info=True)
        try:
            await websocket.close(code=1011, reason=str(e)[:123])
        except Exception:
            pass
