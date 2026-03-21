"""
Voice Stream WebSocket Router - Feb 28, 2026

Bidirectional voice streaming:
- Binary audio in (client -> MAS -> PersonaPlex Bridge)
- TTS audio/text out (Bridge -> MAS -> client)

NO MOCK DATA - Real PersonaPlex Bridge + voice pipeline.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from mycosoft_mas.voice.full_duplex_voice import FullDuplexVoice

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Voice Stream"])


@router.websocket("/ws/voice/stream")
async def voice_stream(
    websocket: WebSocket,
    session_id: Optional[str] = None,
    conversation_id: Optional[str] = None,
    user_id: Optional[str] = None,
) -> None:
    """Bidirectional voice streaming session."""
    await websocket.accept()

    async def send_audio(audio_bytes: bytes) -> None:
        await websocket.send_bytes(audio_bytes)

    async def send_text(text: str) -> None:
        await websocket.send_json(
            {
                "type": "text",
                "text": text,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )

    voice = FullDuplexVoice(
        audio_callback=send_audio,
        text_callback=send_text,
    )

    await voice.start()
    await voice.start_session(
        session_id=session_id,
        conversation_id=conversation_id,
        user_id=user_id,
        connect_bridge=True,
    )

    await websocket.send_json(
        {
            "type": "connected",
            "message": "Voice stream connected",
            "session_id": voice.session_id,
            "conversation_id": voice.conversation_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    )

    try:
        while True:
            message = await websocket.receive()
            if message.get("type") == "websocket.disconnect":
                break

            if "bytes" in message and message["bytes"] is not None:
                await voice.send_audio_chunk(message["bytes"])
                continue

            text_payload = message.get("text")
            if not text_payload:
                continue

            try:
                data = json.loads(text_payload)
            except json.JSONDecodeError:
                data = {"type": "text", "text": text_payload}

            message_type = data.get("type")
            if message_type == "ping":
                await websocket.send_json(
                    {"type": "pong", "timestamp": datetime.now(timezone.utc).isoformat()}
                )
            elif message_type in {"text", "transcript"}:
                transcript = data.get("text") or data.get("transcript") or ""
                if transcript:
                    result = await voice.handle_user_input(transcript)
                    await websocket.send_json(
                        {
                            "type": "result",
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                            "data": result,
                        }
                    )
            elif message_type == "speak":
                text = data.get("text") or ""
                if text:
                    await voice.speak(text, can_interrupt=data.get("can_interrupt", True))
            elif message_type == "pause":
                await voice.pause_session()
            elif message_type == "resume":
                await voice.resume_session()
            elif message_type == "end":
                break
    except WebSocketDisconnect:
        pass
    except Exception as exc:
        logger.error("Voice stream error: %s", exc)
    finally:
        await voice.stop()
