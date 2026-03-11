"""
Voice v9 WebSocket Router - March 2, 2026.

Unified v9 session stream: session state, transcript chunks, events, latency, etc.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from mycosoft_mas.voice_v9.schemas import TranscriptChunk, TranscriptRole
from mycosoft_mas.voice_v9.services import (
    CognitiveRouter,
    MASBridge,
    get_interrupt_manager,
    get_persona_lock_service,
    get_voice_gateway,
    get_truth_mirror_bus,
)

logger = logging.getLogger("voice_v9.ws")

router = APIRouter(tags=["voice-v9-ws"])


async def _send_json(ws: WebSocket, data: dict) -> None:
    await ws.send_json(data)


@router.websocket("/ws/voice/v9")
async def voice_v9_websocket(
    websocket: WebSocket,
) -> None:
    """
    Unified v9 voice session WebSocket.
    Supports: session creation, transcript ingestion, event stream, latency traces.
    """
    await websocket.accept()
    gateway = get_voice_gateway()
    truth_bus = get_truth_mirror_bus()
    cognitive_router = CognitiveRouter()
    mas_bridge = MASBridge()
    session_id: str | None = None

    await _send_json(websocket, {
        "type": "connected",
        "message": "Voice v9 WebSocket connected",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })

    try:
        while True:
            msg = await websocket.receive()
            if msg.get("type") == "websocket.disconnect":
                break

            text = msg.get("text")
            if not text:
                continue

            try:
                data = json.loads(text)
            except json.JSONDecodeError:
                await _send_json(websocket, {"type": "error", "message": "Invalid JSON"})
                continue

            msg_type = data.get("type")

            if msg_type == "ping":
                await _send_json(websocket, {
                    "type": "pong",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })

            elif msg_type == "create_session":
                user_id = data.get("user_id", "morgan")
                conv_id = data.get("conversation_id")
                session = gateway.create_session(user_id=user_id, conversation_id=conv_id)
                session_id = session.session_id
                await _send_json(websocket, {
                    "type": "session_created",
                    "session_id": session.session_id,
                    "conversation_id": session.conversation_id,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })

            elif msg_type == "transcript":
                sid = data.get("session_id") or session_id
                if not sid:
                    await _send_json(websocket, {"type": "error", "message": "No session"})
                    continue
                text_val = data.get("text", "")
                role = TranscriptRole.USER if data.get("role", "user") == "user" else TranscriptRole.ASSISTANT
                chunk = TranscriptChunk(
                    session_id=sid,
                    role=role,
                    text=text_val,
                    is_final=data.get("is_final", True),
                    source=data.get("source", "browser_stt"),
                )
                gateway.add_transcript_chunk(chunk)
                await _send_json(websocket, {
                    "type": "transcript_ack",
                    "chunk_id": chunk.chunk_id,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })
                # Generate an assistant turn for finalized user transcripts.
                if role == TranscriptRole.USER and chunk.is_final and text_val.strip():
                    try:
                        route_result = await cognitive_router.route(
                            session_id=sid,
                            user_text=text_val,
                            context={"user_id": "morgan"},
                        )
                        assistant_text = (route_result.get("response") or "").strip()

                        if route_result.get("target") == "mas_bridge" and not assistant_text:
                            bridge_result = await mas_bridge.chat(
                                session_id=sid,
                                conversation_id=gateway.get_session(sid).conversation_id if gateway.get_session(sid) else sid,
                                user_id="morgan",
                                message=text_val,
                            )
                            assistant_text = (bridge_result.get("response") or "").strip()

                        if assistant_text:
                            assistant_chunk = TranscriptChunk(
                                session_id=sid,
                                role=TranscriptRole.ASSISTANT,
                                text=assistant_text,
                                is_final=True,
                                source=str(route_result.get("provider") or route_result.get("target") or "voice_v9"),
                            )
                            gateway.add_transcript_chunk(assistant_chunk)
                            await _send_json(websocket, {
                                "type": "assistant_text",
                                "session_id": sid,
                                "text": assistant_text,
                                "provider": route_result.get("provider") or route_result.get("target"),
                                "timestamp": datetime.now(timezone.utc).isoformat(),
                            })
                    except Exception as route_exc:
                        logger.exception("Voice v9 route failure: %s", route_exc)
                        await _send_json(websocket, {
                            "type": "error",
                            "message": f"Routing failure: {route_exc}",
                        })

            elif msg_type == "end_session":
                sid = data.get("session_id") or session_id
                if sid:
                    gateway.end_session(sid)
                    session_id = None
                await _send_json(websocket, {
                    "type": "session_ended",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })

            elif msg_type == "get_interrupt":
                sid = data.get("session_id") or session_id
                if not sid or not gateway.get_session(sid):
                    await _send_json(websocket, {"type": "error", "message": "No session"})
                    continue
                mgr = get_interrupt_manager(sid)
                state = mgr.get_interrupt_state()
                await _send_json(websocket, {
                    "type": "interrupt_state",
                    "session_id": sid,
                    "is_speaking": state.is_speaking,
                    "has_interrupted_draft": state.has_interrupted_draft,
                    "interrupted_draft_text": state.interrupted_draft_text,
                    "barge_in_count": state.barge_in_count,
                    "state": state.state,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })

            elif msg_type == "barge_in":
                sid = data.get("session_id") or session_id
                if not sid or not gateway.get_session(sid):
                    await _send_json(websocket, {"type": "error", "message": "No session"})
                    continue
                mgr = get_interrupt_manager(sid)
                mgr.request_barge_in(data.get("user_input"))
                await _send_json(websocket, {
                    "type": "barge_in_acked",
                    "session_id": sid,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })

            elif msg_type == "get_persona":
                sid = data.get("session_id") or session_id
                if not sid or not gateway.get_session(sid):
                    await _send_json(websocket, {"type": "error", "message": "No session"})
                    continue
                svc = get_persona_lock_service()
                state = svc.get_state(sid)
                payload = {**state.model_dump(), "timestamp": datetime.now(timezone.utc).isoformat()}
                await _send_json(websocket, {"type": "persona_state", **payload})

            else:
                await _send_json(websocket, {"type": "unknown", "received_type": msg_type})

    except WebSocketDisconnect:
        pass
    except Exception as exc:
        logger.exception("Voice v9 WebSocket error: %s", exc)
    finally:
        if session_id:
            gateway.end_session(session_id)
