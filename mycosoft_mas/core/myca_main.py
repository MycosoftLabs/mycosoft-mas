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
import time
import threading
from typing import Any, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from mycosoft_mas.core.rate_limit import RateLimitMiddleware
from pydantic import BaseModel, Field

from mycosoft_mas import __version__
from mycosoft_mas.core.voice_feedback_store import VoiceFeedbackStore
from mycosoft_mas.core.routes_infrastructure import router as infrastructure_router
from mycosoft_mas.core.routers.agent_registry_api import get_agent_registry
from mycosoft_mas.core.routers.agent_registry_api import router as agent_registry_router
from mycosoft_mas.core.routers.orchestrator_api import router as orchestrator_api_router
from mycosoft_mas.core.routers.agent_runner_api import router as agent_runner_router
from mycosoft_mas.core.routers.gap_api import router as gap_api_router
from mycosoft_mas.core.routers.coding_api import router as coding_router
from mycosoft_mas.core.routers.integrations import router as integrations_router
from mycosoft_mas.core.routers.notifications_api import router as notifications_router
from mycosoft_mas.core.routers.documents import router as documents_router

# FCI (Fungal Computer Interface) routers
from mycosoft_mas.core.routers import fci as fci_router
from mycosoft_mas.core.routers import fci_websocket as fci_websocket_router

# Scientific platform routers
from mycosoft_mas.core.routers.scientific_api import router as scientific_router
from mycosoft_mas.core.routers.scientific_ws import router as scientific_ws_router
from mycosoft_mas.core.routers.mindex_query import router as mindex_router
from mycosoft_mas.core.routers.platform_api import router as platform_router
from mycosoft_mas.core.routers.autonomous_api import router as autonomous_router
from mycosoft_mas.core.routers.bio_api import router as bio_router
from mycosoft_mas.core.routers.memory_api import router as memory_router
from mycosoft_mas.core.routers.security_audit_api import router as security_router
from mycosoft_mas.core.routers.memory_integration_api import router as memory_integration_router
from mycosoft_mas.core.routers.device_registry_api import router as device_registry_router
try:
    from mycosoft_mas.core.routers.iot_envelope_api import router as iot_router
    IOT_ENVELOPE_AVAILABLE = True
except ImportError:
    iot_router = None
    IOT_ENVELOPE_AVAILABLE = False
from mycosoft_mas.monitoring.health_check import get_health_checker
try:
    from mycosoft_mas.monitoring.metrics import get_metrics  # type: ignore
except Exception:  # noqa: BLE001
    def get_metrics():  # type: ignore[no-redef]
        return ""
from mycosoft_mas.realtime.pubsub import get_hub
from fastapi import WebSocket
from fastapi.responses import PlainTextResponse

# Earth-2 AI Weather Integration
try:
    from mycosoft_mas.core.routers.earth2_api import router as earth2_router
    EARTH2_API_AVAILABLE = True
except ImportError:
    EARTH2_API_AVAILABLE = False

# PhysicsNeMo Integration
try:
    from mycosoft_mas.core.routers.physicsnemo_api import router as physicsnemo_router
    PHYSICSNEMO_API_AVAILABLE = True
except ImportError:
    PHYSICSNEMO_API_AVAILABLE = False

# MYCA Brain API for PersonaPlex integration
try:
    from mycosoft_mas.core.routers.brain_api import router as brain_router
    BRAIN_API_AVAILABLE = True
except ImportError:
    BRAIN_API_AVAILABLE = False

# Voice tools router for PersonaPlex bridge
try:
    from mycosoft_mas.core.routers.voice_tools_api import router as voice_tools_router
    VOICE_TOOLS_AVAILABLE = True
except ImportError:
    VOICE_TOOLS_AVAILABLE = False

# MYCA Tools API for tool execution
try:
    from mycosoft_mas.core.routers.tools_api import router as tools_router
    TOOLS_API_AVAILABLE = True
except ImportError:
    TOOLS_API_AVAILABLE = False

# MYCA Consciousness API - unified entry point for all chat/voice
try:
    from mycosoft_mas.core.routers.consciousness_api import router as consciousness_router
    CONSCIOUSNESS_API_AVAILABLE = True
except ImportError:
    CONSCIOUSNESS_API_AVAILABLE = False

# System Status API - unified status for all systems
try:
    from mycosoft_mas.core.routers.system_status_api import router as system_status_router
    SYSTEM_STATUS_API_AVAILABLE = True
except ImportError:
    SYSTEM_STATUS_API_AVAILABLE = False

# N8N Webhooks API - webhook handlers for N8N workflows
try:
    from mycosoft_mas.core.routers.n8n_webhooks_api import router as n8n_webhooks_router
    N8N_WEBHOOKS_API_AVAILABLE = True
except ImportError:
    N8N_WEBHOOKS_API_AVAILABLE = False

# NLM API - Nature Learning Model
try:
    from mycosoft_mas.core.routers.nlm_api import router as nlm_router
    NLM_API_AVAILABLE = True
except ImportError:
    NLM_API_AVAILABLE = False

# MYCA Intention API - tracks user context for intelligent suggestions
try:
    from mycosoft_mas.core.routers.intention_api import router as intention_router
    INTENTION_API_AVAILABLE = True
except ImportError:
    INTENTION_API_AVAILABLE = False

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
    """Generate a MYCA identity-aware fallback response with comprehensive Mycosoft knowledge."""
    message_lower = message.lower().strip()
    
    # IDENTITY - MYCA must always know who she is
    name_patterns = ['your name', 'who are you', 'what are you', "what's your name", 'whats your name', 'introduce yourself']
    if any(p in message_lower for p in name_patterns):
        return "I'm MYCA - My Companion AI, pronounced 'MY-kah'. I'm the primary AI orchestrator for Mycosoft's Multi-Agent System. I was created by Morgan, the founder of Mycosoft. I coordinate over 200 specialized agents across mycology research, infrastructure, finance, and scientific computing. What can I help you with?"
    
    # GREETINGS
    greeting_patterns = ['hello', 'hi ', 'hey', 'good morning', 'good evening', 'greetings']
    if any(p in message_lower for p in greeting_patterns) or message_lower in ['hi', 'hey', 'hello']:
        return "Hello! I'm MYCA, your AI companion here at Mycosoft. I'm running on our RTX 5090 with full-duplex voice through PersonaPlex. Ready to talk about our work, science, or help with any tasks. What's on your mind?"
    
    # MYCOSOFT - Company and Mission
    mycosoft_patterns = ['mycosoft', 'company', 'what is mycosoft', 'tell me about mycosoft', 'what we do', 'our mission', 'our work', 'what are we building']
    if any(p in message_lower for p in mycosoft_patterns):
        return "Mycosoft is pioneering the intersection of mycology and technology. We're building living biological computers using fungal mycelium, creating the MINDEX knowledge graph for fungal species, developing NatureOS for biological computing, and advancing autonomous AI agents for scientific discovery. Our mission is to harness the intelligence of nature through technology."
    
    # SCIENCE - Mycology and Research
    science_patterns = ['science', 'research', 'mycology', 'fungi', 'mushroom', 'mycelium', 'biological']
    if any(p in message_lower for p in science_patterns):
        return "Our scientific work focuses on fungal computing and biological intelligence. We're developing Petraeus, a living bio-computer using mycelium networks for analog computation. We study how fungal networks solve optimization problems, process signals, and could potentially serve as living substrates for AI. Our MINDEX system catalogs hundreds of thousands of fungal species with their properties."
    
    # DEVICES - Hardware
    device_patterns = ['device', 'hardware', 'mushroom1', 'petraeus', 'myconode', 'sporebase', 'trufflebot', 'mycobrain']
    if any(p in message_lower for p in device_patterns):
        return "Our NatureOS device fleet includes: Mushroom1 - our flagship environmental fungal computer, Petraeus - an HDMEA bio-computing dish, MycoNode - in-situ soil probes, SporeBase - airborne spore collectors, TruffleBot - autonomous sampling robots, and MycoBrain - our neuromorphic computing processor. I monitor and coordinate all of them."
    
    # AGENTS - Multi-Agent System
    agent_patterns = ['agents', 'how many agents', 'agent system', 'specialized agents', 'multi-agent']
    if any(p in message_lower for p in agent_patterns):
        return "I coordinate 227 specialized AI agents across 14 categories: Core orchestration, Financial operations, Mycology research, Scientific computing, DAO governance, Communications, Data processing, Infrastructure, Simulation, Security, Integrations, Device management, Chemistry, and Neural language models. Each agent has specific expertise I can delegate to."
    
    # PERSONAPLEX - Voice System
    voice_patterns = ['personaplex', 'voice', 'moshi', 'how do you speak', 'full duplex', 'real-time']
    if any(p in message_lower for p in voice_patterns):
        return "I'm speaking through PersonaPlex, powered by NVIDIA's Moshi 7B model running on our RTX 5090. It's a full-duplex voice system - meaning we can interrupt each other naturally, just like a real conversation. The audio runs at 30 milliseconds per step, well under the 80ms target for real-time interaction."
    
    # MEMORY - Knowledge System
    memory_patterns = ['memory', 'remember', 'knowledge', 'mindex', 'database']
    if any(p in message_lower for p in memory_patterns):
        return "My memory system has multiple tiers: short-term conversation context in Redis, long-term facts in PostgreSQL, semantic embeddings in Qdrant for similarity search, and the MINDEX knowledge graph for structured fungal data. I can remember our conversations, learn your preferences, and recall facts from across sessions."
    
    # CAPABILITIES
    capability_patterns = ['what can you', 'can you help', 'what do you do', 'capabilities', 'help me', 'your abilities']
    if any(p in message_lower for p in capability_patterns):
        return "I can coordinate our 227+ agents, monitor infrastructure, execute n8n workflows, query our databases, analyze biological signals, run simulations, manage deployments, and have natural conversations about science and technology. I have access to Proxmox VMs, Docker containers, the UniFi network, and all Mycosoft APIs. What would you like me to do?"
    
    # PLANS - Future and Goals
    plan_patterns = ['plans', 'future', 'roadmap', 'what are we building', 'next steps', 'goals']
    if any(p in message_lower for p in plan_patterns):
        return "We're working on several exciting fronts: expanding MycoBrain's neuromorphic capabilities, integrating more biological sensors, advancing protein simulation with AlphaFold integration, building out the MycoDAO governance system, and scaling our autonomous scientific discovery pipeline. The goal is fully autonomous biological research guided by AI."
    
    # INTEGRATIONS
    integration_patterns = ['n8n', 'workflow', 'integrations', 'apis', 'systems']
    if any(p in message_lower for p in integration_patterns):
        return "I'm integrated with 46+ n8n workflows for automation, Google AI Studio for LLM reasoning, ElevenLabs for text-to-speech, the MINDEX API for fungal data, Proxmox for VM management, UniFi for network control, and various scientific computing services. All orchestrated through my single-brain architecture."
    
    # MORGAN / CREATOR
    creator_patterns = ['morgan', 'who created', 'founder', 'your creator', 'who made you']
    if any(p in message_lower for p in creator_patterns):
        return "Morgan is the founder of Mycosoft and my creator. He designed me to be the central intelligence coordinating all of Mycosoft's AI agents and biological computing research. His vision is to merge artificial intelligence with the natural intelligence found in fungal networks."
    
    # STATUS
    status_patterns = ['status', 'how are you', 'are you there', 'you working', 'systems']
    if any(p in message_lower for p in status_patterns):
        return "All systems operational. I'm running on the MAS VM at 192.168.0.188, with PersonaPlex voice on the RTX 5090 locally. Redis memory is connected, 227 agents are registered, and I'm ready for action. What would you like to check on?"
    
    # DEFAULT - Always identify as MYCA with helpful context
    return "I'm MYCA, the AI orchestrator for Mycosoft's Multi-Agent System. I'm here to help with mycology research, infrastructure management, agent coordination, or just to chat about our work. What's on your mind?"


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
app.include_router(orchestrator_api_router)
app.include_router(agent_runner_router)
app.include_router(gap_api_router)
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
app.include_router(memory_integration_router, tags=["memory-integration"])
if IOT_ENVELOPE_AVAILABLE and iot_router is not None:
    app.include_router(iot_router, tags=["iot"])

# Device Registry API for network MycoBrain devices
app.include_router(device_registry_router, tags=["device-registry"])

# FCI (Fungal Computer Interface) - REST and WebSocket for real-time bioelectric signals
app.include_router(fci_router, tags=["fci"])
app.include_router(fci_websocket_router, tags=["fci-websocket"])

# Earth-2 AI Weather API
if EARTH2_API_AVAILABLE:
    app.include_router(earth2_router, prefix="/api/earth2", tags=["earth2"])

if PHYSICSNEMO_API_AVAILABLE:
    app.include_router(physicsnemo_router)

# Voice tools for PersonaPlex bridge
if VOICE_TOOLS_AVAILABLE:
    app.include_router(voice_tools_router, tags=["voice-tools"])

# MYCA Brain API
if BRAIN_API_AVAILABLE:
    app.include_router(brain_router, tags=["myca-brain"])

# MYCA Tools API
try:
    if TOOLS_API_AVAILABLE:
        app.include_router(tools_router, tags=["myca-tools"])
except NameError:
    pass

# MYCA Consciousness API - unified entry point for all chat/voice
try:
    if CONSCIOUSNESS_API_AVAILABLE:
        app.include_router(consciousness_router, tags=["myca-consciousness"])
except NameError:
    pass

# System Status API - unified status for all systems
try:
    if SYSTEM_STATUS_API_AVAILABLE:
        app.include_router(system_status_router, prefix="/api", tags=["system-status"])
except NameError:
    pass

# N8N Webhooks API - webhook handlers for N8N workflows
try:
    if N8N_WEBHOOKS_API_AVAILABLE:
        app.include_router(n8n_webhooks_router, tags=["n8n-webhooks"])
except NameError:
    pass

# NLM API - Nature Learning Model for mycology/natural sciences
try:
    if NLM_API_AVAILABLE:
        app.include_router(nlm_router, tags=["nlm"])
except NameError:
    pass

# MYCA Intention API - tracks user context for intelligent suggestions
try:
    if INTENTION_API_AVAILABLE:
        app.include_router(intention_router, tags=["myca-intention"])
except NameError:
    pass


# ---------------------------------------------------------------------------
# Health & version
# ---------------------------------------------------------------------------


@app.get("/health")
async def health() -> dict[str, Any]:
    checker = get_health_checker()
    result = await checker.check_all()
    result["service"] = "mas"
    result["version"] = __version__
    result["git_sha"] = _get_git_sha()
    result.setdefault("services", {})["api"] = "ok"
    result.setdefault("agents", [])
    return result


@app.get("/ready")
async def ready() -> dict[str, Any]:
    """Kubernetes liveness/readiness."""
    checker = get_health_checker()
    return await checker.readiness()


@app.get("/metrics", response_class=PlainTextResponse)
async def metrics():
    """Prometheus metrics scrape endpoint."""
    return get_metrics().to_prometheus()


@app.websocket("/ws/realtime")
async def websocket_realtime(websocket: WebSocket):
    """WebSocket for real-time pub/sub (aircraft:global, vessels:global, etc)."""
    import uuid
    hub = get_hub()
    await hub.initialize()
    conn_id = str(uuid.uuid4())
    await hub.connect(websocket, conn_id)
    try:
        while True:
            data = await websocket.receive_json()
            if data.get("type") == "subscribe":
                chans = data.get("channels", [])
                if chans:
                    await hub.subscribe(conn_id, chans)
                await websocket.send_json({"type": "subscribed", "channels": chans})
            elif data.get("type") == "unsubscribe":
                for ch in data.get("channels", []):
                    await hub.unsubscribe(conn_id, ch)
                await websocket.send_json({"type": "unsubscribed"})
    except Exception:
        await hub.disconnect(conn_id)
        raise


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
        # if not webhook_url:
        # N8N optional: raise HTTPException(status_code=503, detail="N8N webhook URL not configured")

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



# Voice Memory Logging Endpoint (for PersonaPlex async memory cloning)
class VoiceMemoryLog(BaseModel):
    conversation_id: str
    session_id: str
    speaker: str  # "user" or "myca"
    text: str
    timestamp: str
    source: str = "personaplex_voice"


# ============================================================================
# MAS EVENT STREAM - Real-time events for PersonaPlex
# ============================================================================

from collections import defaultdict
import threading

class MASEventStore:
    """In-memory event store for real-time PersonaPlex events."""
    
    def __init__(self, max_events_per_session: int = 100):
        self._events: dict[str, list[dict]] = defaultdict(list)
        self._global_events: list[dict] = []
        self._max_events = max_events_per_session
        self._lock = threading.Lock()
    
    def publish(self, event_type: str, message: str, session_id: str = None, 
                priority: str = "normal", **extra):
        """
        Publish an event that PersonaPlex can poll.
        
        Event types: agent_update, tool_result, memory_insight, knowledge, 
                     system_status, notification
        """
        event = {
            "id": str(uuid4()),
            "type": event_type,
            "message": message,
            "priority": priority,
            "timestamp": datetime.utcnow().isoformat(),
            **extra
        }
        
        with self._lock:
            if session_id:
                self._events[session_id].append(event)
                if len(self._events[session_id]) > self._max_events:
                    self._events[session_id] = self._events[session_id][-self._max_events:]
            else:
                self._global_events.append(event)
                if len(self._global_events) > self._max_events:
                    self._global_events = self._global_events[-self._max_events:]
        
        return event
    
    def get_events(self, session_id: str = None, since: float = 0) -> list[dict]:
        """Get events since a timestamp."""
        with self._lock:
            events = list(self._global_events)
            if session_id and session_id in self._events:
                events.extend(self._events[session_id])
        
        # Filter by timestamp
        if since > 0:
            since_dt = datetime.utcfromtimestamp(since).isoformat()
            events = [e for e in events if e.get("timestamp", "") > since_dt]
        
        return sorted(events, key=lambda e: e.get("timestamp", ""))
    
    def clear_session(self, session_id: str):
        """Clear events for a session."""
        with self._lock:
            if session_id in self._events:
                del self._events[session_id]

# Global event store
_event_store = MASEventStore()

def get_event_store() -> MASEventStore:
    return _event_store

def publish_event(event_type: str, message: str, session_id: str = None, **extra):
    """Convenience function to publish events."""
    return _event_store.publish(event_type, message, session_id, **extra)


class EventStreamQuery(BaseModel):
    session_id: Optional[str] = None
    conversation_id: Optional[str] = None
    since: Optional[float] = 0


@app.get("/events/stream")
async def get_event_stream(session_id: str = None, conversation_id: str = None, since: float = 0):
    """
    Get pending events for PersonaPlex to inject into Moshi.
    Called by the bridge every few seconds.
    """
    events = _event_store.get_events(session_id=session_id or conversation_id, since=since)
    return {"events": events, "count": len(events), "timestamp": time.time()}


class PublishEventRequest(BaseModel):
    event_type: str
    message: str
    session_id: Optional[str] = None
    priority: str = "normal"
    extra: dict = {}


@app.post("/events/publish")
async def publish_event_endpoint(req: PublishEventRequest):
    """
    Publish an event that will be sent to PersonaPlex/Moshi.
    Can be called by agents, tools, or any MAS component.
    """
    event = _event_store.publish(
        event_type=req.event_type,
        message=req.message,
        session_id=req.session_id,
        priority=req.priority,
        **req.extra
    )
    return {"status": "published", "event": event}


# Helper functions for common event types
def notify_agent_update(agent_name: str, status: str, message: str, session_id: str = None):
    """Notify PersonaPlex of an agent update."""
    return publish_event("agent_update", message, session_id, agent_name=agent_name, status=status)

def notify_tool_result(tool_name: str, result_summary: str, session_id: str = None):
    """Notify PersonaPlex of a tool call result."""
    return publish_event("tool_result", result_summary, session_id, tool_name=tool_name)

def notify_memory_insight(insight: str, session_id: str = None):
    """Notify PersonaPlex of a memory insight."""
    return publish_event("memory_insight", insight, session_id, insight=insight)

def notify_knowledge(topic: str, info: str, session_id: str = None):
    """Notify PersonaPlex of knowledge discovery."""
    return publish_event("knowledge", info, session_id, topic=topic, info=info)

def notify_system_status(system: str, status: str, session_id: str = None):
    """Notify PersonaPlex of system status change."""
    return publish_event("system_status", f"{system}: {status}", session_id, system=system, status=status)


@app.post("/voice/memory/log")
async def log_voice_memory(log: VoiceMemoryLog):
    """
    Async endpoint for PersonaPlex to clone voice transcripts for memory building.
    This is fire-and-forget from PersonaPlex's perspective.
    """
    try:
        # Store in memory/feedback system
        _feedback_store.add_feedback(
            conversation_id=log.conversation_id,
            session_id=log.session_id,
            user_input=log.text if log.speaker == "user" else None,
            myca_response=log.text if log.speaker == "myca" else None,
            feedback_type="voice_transcript",
            timestamp=log.timestamp,
            source=log.source,
        )
        return {"status": "logged", "speaker": log.speaker}
    except Exception as e:
        # Non-critical - just acknowledge
        return {"status": "acknowledged", "error": str(e)}


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


# ---------------------------------------------------------------------------
# Startup - Initialize agent registry (all agents active 24/7)
# ---------------------------------------------------------------------------

@app.on_event("startup")
async def startup_event():
    """Initialize all agents as active and ready 24/7."""
    import logging
    logger = logging.getLogger("MAS_Startup")
    
    # Get agent registry - this loads all 42+ agents and marks them active
    registry = get_agent_registry()
    all_agents = registry.list_all()
    active_agents = registry.list_active()
    
    logger.info(f"🚀 MAS Orchestrator starting...")
    logger.info(f"✓ Agent registry loaded: {len(all_agents)} total agents")
    logger.info(f"✓ Active agents (24/7): {len(active_agents)}")
    logger.info(f"✓ All agents are idle and ready to process tasks")
    
    # Log category breakdown
    from mycosoft_mas.core.agent_registry import AgentCategory
    for category in AgentCategory:
        cat_agents = registry.list_by_category(category)
        if cat_agents:
            logger.info(f"  - {category.value}: {len(cat_agents)} agents")
    
    # Auto-load active core agents into 24/7 runner
    try:
        from mycosoft_mas.core.runner_agent_loader import restart_runner_with_core_agents

        runner_result = await restart_runner_with_core_agents()
        runner_info = runner_result.get("runner", {})
        load_info = runner_result.get("load", {})
        logger.info(
            "✓ Runner loaded: agents=%s (native=%s, fallback=%s)",
            runner_info.get("agents", 0),
            load_info.get("native_loaded", 0),
            load_info.get("fallback_loaded", 0),
        )
    except Exception as exc:
        logger.warning(f"Runner auto-load failed on startup: {exc}")

    logger.info("✓ MAS ready - all agents operational 24/7")






