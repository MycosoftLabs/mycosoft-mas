"""
Conversation memory API for website MYCA integration.

Exposes /memory/conversations, /memory/store, /memory/clear so the website
/api/mas/memory can use MAS for conversation persistence instead of only Supabase.

Created: March 2026
"""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/memory", tags=["memory", "myca-conversations"])

# In-memory store: user_id -> list of conversations; each conversation has session_id and messages.
# In production this could use Redis or the existing memory_api with scope=conversation.
_conversations: Dict[str, List[Dict[str, Any]]] = defaultdict(list)


class StoreRequest(BaseModel):
    """Body for POST /memory/store."""
    session_id: Optional[str] = None
    user_id: Optional[str] = "default"
    message: str = Field(..., description="Message content")
    role: str = Field(..., description="user | assistant | system")
    agent: Optional[str] = None
    context: Optional[Dict[str, Any]] = None
    timestamp: Optional[str] = None


@router.get("/conversations")
async def get_conversations(
    user_id: str = Query("default", alias="user_id"),
    session_id: Optional[str] = Query(None, alias="session_id"),
    limit: int = Query(50, ge=1, le=200),
) -> Dict[str, Any]:
    """
    List conversations for a user. Website GET /api/mas/memory calls this.
    Returns conversations with messages; if session_id given, filter to that session.
    """
    user_convos = _conversations.get(user_id, [])
    if session_id:
        user_convos = [c for c in user_convos if c.get("session_id") == session_id]
    # Return last N conversations (by updated_at)
    sorted_convos = sorted(
        user_convos,
        key=lambda c: c.get("updated_at", ""),
        reverse=True,
    )[:limit]
    return {
        "conversations": sorted_convos,
        "source": "mas",
    }


@router.post("/store")
async def store_message(body: StoreRequest) -> Dict[str, Any]:
    """
    Append a message to a conversation. Website POST /api/mas/memory calls this.
    """
    user_id = body.user_id or "default"
    session_id = body.session_id or f"session-{datetime.now(timezone.utc).timestamp()}"
    ts = body.timestamp or datetime.now(timezone.utc).isoformat()

    user_convos = _conversations[user_id]
    convo = next((c for c in user_convos if c.get("session_id") == session_id), None)
    if not convo:
        convo = {
            "id": session_id,
            "user_id": user_id,
            "session_id": session_id,
            "messages": [],
            "context": {"topics": [], "entities": [], "intent_history": []},
            "created_at": ts,
            "updated_at": ts,
        }
        user_convos.append(convo)

    convo["messages"].append({
        "role": body.role,
        "content": body.message,
        "timestamp": ts,
        "agent": body.agent,
    })
    convo["updated_at"] = ts
    if body.context:
        for k, v in (body.context or {}).items():
            if k in convo["context"] and isinstance(convo["context"][k], list) and isinstance(v, list):
                convo["context"][k] = list(set(convo["context"][k]) | set(v))
            elif isinstance(v, list):
                convo["context"][k] = v

    return {"stored": True, "source": "mas", "session_id": session_id}


@router.delete("/clear")
async def clear_memory(
    user_id: str = Query("default", alias="user_id"),
    session_id: Optional[str] = Query(None, alias="session_id"),
) -> Dict[str, Any]:
    """
    Clear conversation memory for a user/session. Website DELETE /api/mas/memory calls this.
    """
    if user_id not in _conversations:
        return {"cleared": True, "source": "mas"}
    if session_id:
        _conversations[user_id] = [c for c in _conversations[user_id] if c.get("session_id") != session_id]
    else:
        _conversations[user_id] = []
    return {"cleared": True, "source": "mas"}
