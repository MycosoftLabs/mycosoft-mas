"""
MYCA / MAS API entrypoint.

This module intentionally stays lightweight: it exposes health/version endpoints,
includes the core routers, and provides minimal voice endpoints used by the UI.
"""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
from uuid import uuid4
from pathlib import Path
import os
import subprocess
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from mycosoft_mas.core.rate_limit import RateLimitMiddleware
from pydantic import BaseModel, Field

from mycosoft_mas import __version__
from mycosoft_mas.core.voice_feedback_store import VoiceFeedbackStore
from mycosoft_mas.core.routes_infrastructure import router as infrastructure_router
from mycosoft_mas.core.routers.agent_registry_api import get_agent_registry
from mycosoft_mas.core.routers.agent_registry_api import router as agent_registry_router
from mycosoft_mas.core.routers.agent_runner_api import router as agent_runner_router
from mycosoft_mas.core.routers.coding_api import router as coding_router
from mycosoft_mas.core.routers.integrations import router as integrations_router
from mycosoft_mas.core.routers.notifications_api import router as notifications_router
from mycosoft_mas.core.routers.documents import router as documents_router

# Scientific platform routers
from mycosoft_mas.core.routers.scientific_api import router as scientific_router
from mycosoft_mas.core.routers.scientific_ws import router as scientific_ws_router
from mycosoft_mas.core.routers.mindex_query import router as mindex_router
from mycosoft_mas.core.routers.platform_api import router as platform_router
from mycosoft_mas.core.routers.autonomous_api import router as autonomous_router
from mycosoft_mas.core.routers.bio_api import router as bio_router
from mycosoft_mas.core.routers.memory_api import router as memory_router
from mycosoft_mas.core.routers.security_audit_api import router as security_router

# N8N Client - use mycosoft_mas path
try:
    from mycosoft_mas.integrations.n8n_client import N8NClient
except ImportError as e:
    import logging
    logging.warning(f"Could not import N8NClient: {e}")
    N8NClient = None


def load_config() -> dict[str, Any]:
    """Load config from env and (optionally) config.yaml. Kept minimal for now."""
    config: dict[str, Any] = {}
    config_path = Path(os.getenv("MAS_CONFIG_PATH", "config.yaml"))
    if config_path.exists():
        try:
            import yaml  # type: ignore

            with config_path.open("r", encoding="utf-8") as f:
                cfg = yaml.safe_load(f) or {}
            if isinstance(cfg, dict):
                config.update(cfg)
        except Exception:
            # Config should never block startup in local dev.
            pass

    config.update(
        {
            "mas_env": os.getenv("MAS_ENV", "development"),
            "log_level": os.getenv("LOG_LEVEL", "INFO"),
        }
    )
    return config


N8N_VOICE_WEBHOOK = os.getenv("N8N_VOICE_WEBHOOK", "myca/voice")

def resolve_n8n_webhook_url() -> str | None:
    base = os.getenv("N8N_WEBHOOK_URL") or os.getenv("N8N_URL")
    if not base:
        return None
    base = base.rstrip("/")
    # Don't modify base - n8n client handles webhook path
    return base

def extract_response_text(payload: object) -> str | None:
    if isinstance(payload, dict):
        for key in ("response_text", "response", "text", "message", "answer"):
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    if isinstance(payload, list) and payload:
        first = payload[0]
        if isinstance(first, str) and first.strip():
            return first.strip()
        if isinstance(first, dict):
            for key in ("response_text", "response", "text", "message", "answer"):
                value = first.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()
    return None



def generate_myca_fallback_response(message: str) -> str:
    """Generate a MYCA-aware fallback response when n8n is unavailable."""
    message_lower = message.lower().strip()
    
    # Handle name-related questions
    name_patterns = ['your name', 'who are you', 'what are you', "what's your name", 'whats your name']
    if any(p in message_lower for p in name_patterns):
        return "I'm MYCA - My Companion AI. I'm the orchestrator of Mycosoft's Multi-Agent System. I coordinate all the specialized agents here and help you interact with our infrastructure. What can I help you with?"
    
    # Handle greeting
    greeting_patterns = ['hello', 'hi ', 'hey', 'good morning', 'good evening', 'greetings']
    if any(p in message_lower for p in greeting_patterns) or message_lower in ['hi', 'hey']:
        return "Hello! I'm MYCA, your AI companion here at Mycosoft. I'm currently coordinating our agent network and ready to help you with whatever you need."
    
    # Handle capability questions
    capability_patterns = ['what can you', 'can you help', 'what do you do', 'capabilities']
    if any(p in message_lower for p in capability_patterns):
        return "I'm MYCA, the central orchestrator for Mycosoft's Multi-Agent System. I can coordinate specialized agents for research, code analysis, infrastructure monitoring, and more. I have access to our n8n workflows, MINDEX knowledge graph, and system APIs. How can I help you today?"
    
    # Handle status questions
    status_patterns = ['status', 'how are you', 'are you there', 'you working']
    if any(p in message_lower for p in status_patterns):
        return "I'm MYCA, and I'm fully operational. Currently running on our RTX 5090 infrastructure. All systems are responsive. What would you like me to look into?"
    
    # Default response with identity
    return "I'm MYCA, and I'm here to help. I'm currently operating in a limited mode as some backend services are being refreshed. Please try again in a moment, or let me know what you need and I'll do my best to assist."


_n8n_client: N8NClient | None = None

def get_n8n_client() -> N8NClient:
    global _n8n_client
    if _n8n_client is None:
        webhook_url = resolve_n8n_webhook_url()
        _n8n_client = N8NClient(config={"webhook_url": webhook_url} if webhook_url else {})
    return _n8n_client


class MycosoftMAS:
    """Small faÃ§ade object to keep compatibility with older imports."""

    def __init__(self) -> None:
        self.config = load_config()


def _get_git_sha() -> str | None:
    try:
        sha = (
            subprocess.check_output(["git", "rev-parse", "HEAD"], stderr=subprocess.DEVNULL)
            .decode("utf-8")
            .strip()
        )
        return sha or None
    except Exception:
        return None


app = FastAPI(
    title="Mycosoft MAS (MYCA)",
    version=__version__,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate limiting middleware
app.add_middleware(RateLimitMiddleware)

# ---------------------------------------------------------------------------
# Core routes
# ---------------------------------------------------------------------------

app.include_router(agent_registry_router)
app.include_router(agent_runner_router)
app.include_router(coding_router)
app.include_router(integrations_router)
app.include_router(notifications_router)
app.include_router(infrastructure_router)
app.include_router(documents_router)

# Scientific platform routers
app.include_router(scientific_router, prefix="/scientific", tags=["scientific"])
app.include_router(scientific_ws_router, tags=["websocket"])
app.include_router(mindex_router, prefix="/mindex", tags=["mindex"])
app.include_router(platform_router, prefix="/platform", tags=["platform"])
app.include_router(autonomous_router, prefix="/autonomous", tags=["autonomous"])
app.include_router(bio_router, prefix="/bio", tags=["bio-compute"])
app.include_router(memory_router, tags=["memory"])
app.include_router(security_router, tags=["security"])


# ---------------------------------------------------------------------------
# Health & version
# ---------------------------------------------------------------------------


@app.get("/health")
async def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "service": "mas",
        "version": __version__,
        "git_sha": _get_git_sha(),
        "services": {
            # Keep shape stable for UIs that expect a nested object.
            "api": "ok",
        },
        # Optional: can be populated later with real agent runner state.
        "agents": [],
    }


@app.get("/version")
async def version() -> dict[str, Any]:
    return {
        "service": "mas",
        "version": __version__,
        "git_sha": _get_git_sha(),
    }


# ---------------------------------------------------------------------------
# Voice + feedback (minimal, but real endpoints so the UI can connect)
# ---------------------------------------------------------------------------


_feedback_store = VoiceFeedbackStore(Path(os.getenv("VOICE_FEEDBACK_DB_PATH", "data/voice_feedback.db")))


class VoiceChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    actor: str = Field(default="morgan")
    conversation_id: str | None = None
    session_id: str | None = None


class VoiceChatResponse(BaseModel):
    conversation_id: str | None
    agent_name: str
    response_text: str
    matched_agents: list[dict[str, Any]] = Field(default_factory=list)


@app.post("/voice/orchestrator/chat", response_model=VoiceChatResponse)
async def voice_orchestrator_chat(payload: VoiceChatRequest) -> VoiceChatResponse:
    if not payload.message or not payload.message.strip():
        raise HTTPException(status_code=400, detail="Message is required")

    webhook_url = resolve_n8n_webhook_url()
    if not webhook_url:
        raise HTTPException(status_code=503, detail="N8N webhook URL not configured")

    registry = get_agent_registry()
    matches = registry.find_by_voice_trigger(payload.message)
    primary = None
    if matches:
        active_matches = [m for m in matches if m.is_active]
        primary = active_matches[0] if active_matches else matches[0]

    agent_name = primary.display_name if primary else "MYCA"
    conversation_id = payload.conversation_id or payload.session_id or str(uuid4())
    request_payload = {
        "message": payload.message,
        "actor": payload.actor,
        "conversation_id": conversation_id,
        "session_id": payload.session_id,
        "primary_agent": agent_name,
        "matched_agents": [
            {
                "agent_id": a.agent_id,
                "display_name": a.display_name,
                "category": a.category.value,
                "requires_confirmation": a.requires_confirmation,
                "is_active": a.is_active,
            }
            for a in matches[:5]
        ],
        "timestamp": datetime.utcnow().isoformat(),
    }

    response_text = None
    try:
        client = get_n8n_client()
        result = await client.trigger_workflow(N8N_VOICE_WEBHOOK, request_payload)
        response_text = extract_response_text(result)
    except Exception as exc:
        # Log but don't fail - use MYCA fallback
        import logging
        logging.warning(f"N8N workflow failed, using MYCA fallback: {exc}")
    
    # Use MYCA identity-aware fallback if n8n failed or returned nothing
    if not response_text:
        response_text = generate_myca_fallback_response(payload.message)

    try:
        _feedback_store.add_feedback(
            conversation_id=conversation_id,
            agent_name=agent_name,
            transcript=payload.message,
            response_text=response_text,
            rating=None,
            success=True,
            notes=None,
        )
    except Exception:
        # Don't block chat on feedback persistence.
        pass

    return VoiceChatResponse(
        conversation_id=conversation_id,
        agent_name=agent_name,
        response_text=response_text,
        matched_agents=[
            {
                "agent_id": a.agent_id,
                "display_name": a.display_name,
                "category": a.category.value,
                "requires_confirmation": a.requires_confirmation,
                "is_active": a.is_active,
            }
            for a in matches[:5]
        ],
    )


class VoiceFeedbackRequest(BaseModel):
    conversation_id: str | None = None
    agent_name: str | None = None
    transcript: str | None = None
    response_text: str | None = None
    rating: int | None = Field(default=None, ge=1, le=5)
    success: bool | None = None
    notes: str | None = None


@app.post("/voice/feedback")
async def create_voice_feedback(payload: VoiceFeedbackRequest) -> dict[str, Any]:
    item = _feedback_store.add_feedback(
        conversation_id=payload.conversation_id,
        agent_name=payload.agent_name,
        transcript=payload.transcript,
        response_text=payload.response_text,
        rating=payload.rating,
        success=payload.success,
        notes=payload.notes,
    )
    return {"status": "ok", "item": asdict(item)}


@app.get("/voice/feedback/recent")
async def voice_feedback_recent(limit: int = 20) -> dict[str, Any]:
    items = _feedback_store.list_recent(limit=limit)
    return {
        "status": "ok",
        "items": [asdict(i) for i in items],
    }


@app.get("/voice/feedback/summary")
async def voice_feedback_summary() -> dict[str, Any]:
    return {"status": "ok", "summary": _feedback_store.summary()}


