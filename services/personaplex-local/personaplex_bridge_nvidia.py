#!/usr/bin/env python3
"""
PersonaPlex NVIDIA Bridge v6.0.0 - February 3, 2026
Full-Duplex Voice with MAS Tool Call Integration

Architecture:
- Moshi handles full-duplex voice (STT + LLM + TTS)
- Bridge extracts text for MAS processing
- MAS detects intents, executes tools, returns results
- Tool results are injected back to Moshi as context
- Text is cloned to MAS for memory building
"""
import asyncio
import json
import logging
import os
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, List, Set, Dict, Any
from uuid import uuid4

import aiohttp
import httpx
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, JSONResponse
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("personaplex-bridge")

app = FastAPI(title="PersonaPlex NVIDIA Bridge", version="6.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
MOSHI_HOST = os.getenv("MOSHI_HOST", "localhost")
MOSHI_PORT = int(os.getenv("MOSHI_PORT", "8998"))
MOSHI_WS_URL = f"ws://{MOSHI_HOST}:{MOSHI_PORT}/api/chat"

# MAS Configuration
MAS_ORCHESTRATOR_URL = os.getenv("MAS_ORCHESTRATOR_URL", "http://192.168.0.188:8001").rstrip("/")
MAS_TIMEOUT = float(os.getenv("MAS_TIMEOUT", "10"))
MAS_EVENT_POLL_INTERVAL = float(os.getenv("MAS_EVENT_POLL_INTERVAL", "2.0"))

# Tool call detection patterns
TOOL_PATTERNS = {
    "device_status": [
        r"(?:status|state|check|how is)\s+(?:mushroom\s*1?|sporebase|myconode|petraeus|trufflebot)",
        r"(?:mushroom\s*1?|sporebase|myconode)\s+(?:status|state)",
    ],
    "query_mindex": [
        r"(?:search|find|look up|query)\s+(?:in\s+)?mindex",
        r"(?:what|tell me about)\s+(?:fungal|mushroom|species)",
    ],
    "agent_list": [
        r"(?:list|show|what)\s+agents",
        r"how many agents",
    ],
    "system_status": [
        r"(?:system|infrastructure|vm|docker)\s+status",
        r"check\s+(?:the\s+)?(?:servers?|containers?)",
    ],
}


def load_myca_persona():
    """Load MYCA persona for Moshi's internal LLM."""
    try:
        prompt_path = os.path.join(os.path.dirname(__file__), "../../config/myca_personaplex_prompt_1000.txt")
        if os.path.exists(prompt_path):
            with open(prompt_path, "r") as f:
                return f.read().strip()
        prompt_path = os.path.join(os.path.dirname(__file__), "../../config/myca_personaplex_prompt.txt")
        if os.path.exists(prompt_path):
            with open(prompt_path, "r") as f:
                content = f.read().strip()
                # Truncate to avoid URL length limits
                return content[:1500] if len(content) > 1500 else content
    except Exception as e:
        logger.warning(f"Could not load persona: {e}")
    
    return """You are MYCA (My Companion AI), the primary AI operator for Mycosoft's Multi-Agent System.
You were created by Morgan, founder of Mycosoft. You coordinate 227+ specialized agents.
You have real-time access to system events and tool results that may be injected during conversation.
When you receive [SYSTEM] or [TOOL] prefixed messages, incorporate them naturally into your response.
Speak warmly and professionally. Be helpful and proactive."""

MYCA_PERSONA = load_myca_persona()


class SessionCreate(BaseModel):
    conversation_id: Optional[str] = None
    persona: str = "myca"
    voice: str = "myca"


@dataclass
class BridgeSession:
    session_id: str
    conversation_id: str
    persona: str
    voice: str
    created_at: str
    transcript_history: List[dict] = field(default_factory=list)
    pending_events: List[dict] = field(default_factory=list)
    pending_tool_results: List[str] = field(default_factory=list)
    event_ids_seen: Set[str] = field(default_factory=set)
    last_event_check: float = 0.0
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    
    def to_dict(self):
        return {
            "session_id": self.session_id,
            "conversation_id": self.conversation_id,
            "created_at": self.created_at,
        }


sessions: Dict[str, BridgeSession] = {}
moshi_available = False
http_client: Optional[httpx.AsyncClient] = None


async def get_http_client():
    global http_client
    if http_client is None:
        http_client = httpx.AsyncClient(timeout=MAS_TIMEOUT)
    return http_client


def normalize(text):
    return re.sub(r"\s+", " ", text).strip()


# ============================================================================
# MAS TOOL CALL DETECTION AND EXECUTION
# ============================================================================

def detect_tool_intent(text: str) -> Optional[tuple]:
    """Detect if user message requires a tool call."""
    text_lower = text.lower()
    
    for tool_name, patterns in TOOL_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, text_lower):
                return (tool_name, text)
    
    return None


async def execute_tool_call(tool_name: str, query: str, session: BridgeSession) -> Optional[str]:
    """Execute a tool call via MAS and return the result."""
    try:
        client = await get_http_client()
        
        # Route to appropriate MAS endpoint based on tool
        if tool_name == "device_status":
            # Extract device name from query
            device_match = re.search(r"(mushroom\s*1?|sporebase|myconode|petraeus|trufflebot)", query.lower())
            device_name = device_match.group(1).replace(" ", "") if device_match else "mushroom1"
            
            resp = await client.get(f"{MAS_ORCHESTRATOR_URL}/api/scientific/devices/{device_name}/status")
            if resp.status_code == 200:
                data = resp.json()
                return f"[TOOL RESULT] Device {device_name}: {data.get('status', 'unknown')}. Temperature: {data.get('temperature', 'N/A')}Â°C, Humidity: {data.get('humidity', 'N/A')}%"
        
        elif tool_name == "agent_list":
            resp = await client.get(f"{MAS_ORCHESTRATOR_URL}/api/agents")
            if resp.status_code == 200:
                data = resp.json()
                total = data.get("total", 0)
                categories = data.get("categories", {})
                return f"[TOOL RESULT] Agent registry: {total} agents across {len(categories)} categories."
        
        elif tool_name == "system_status":
            resp = await client.get(f"{MAS_ORCHESTRATOR_URL}/health")
            if resp.status_code == 200:
                return "[TOOL RESULT] MAS orchestrator is healthy. All systems operational."
        
        elif tool_name == "query_mindex":
            resp = await client.post(
                f"{MAS_ORCHESTRATOR_URL}/api/mindex/search",
                json={"query": query, "limit": 3}
            )
            if resp.status_code == 200:
                data = resp.json()
                results = data.get("results", [])
                if results:
                    return f"[TOOL RESULT] MINDEX found {len(results)} results. Top: {results[0].get('name', 'Unknown species')}"
                return "[TOOL RESULT] MINDEX: No results found for that query."
        
    except Exception as e:
        logger.warning(f"Tool execution failed: {e}")
        return f"[TOOL RESULT] Tool execution encountered an issue. Proceeding with available information."
    
    return None


async def process_user_text_for_tools(text: str, session: BridgeSession, moshi_ws) -> None:
    """Process user text for tool intents and inject results."""
    intent = detect_tool_intent(text)
    
    if intent:
        tool_name, query = intent
        logger.info(f"[{session.session_id[:8]}] Tool intent detected: {tool_name}")
        
        # Execute tool in background
        result = await execute_tool_call(tool_name, query, session)
        
        if result:
            # Store result for context
            async with session.lock:
                session.pending_tool_results.append(result)
            
            # Inject to Moshi
            try:
                await moshi_ws.send_bytes(b"\x02" + result.encode("utf-8"))
                logger.info(f"[{session.session_id[:8]}] Injected tool result: {result[:50]}...")
            except Exception as e:
                logger.warning(f"Failed to inject tool result: {e}")


# ============================================================================
# MAS EVENT STREAM POLLING
# ============================================================================

async def poll_mas_events(session: BridgeSession) -> List[dict]:
    """Poll MAS for new events."""
    try:
        client = await get_http_client()
        resp = await client.get(
            f"{MAS_ORCHESTRATOR_URL}/events/stream",
            params={
                "session_id": session.session_id,
                "conversation_id": session.conversation_id,
                "since": session.last_event_check
            }
        )
        
        if resp.status_code == 200:
            data = resp.json()
            events = data.get("events", [])
            
            new_events = []
            for event in events:
                event_id = event.get("id", str(hash(json.dumps(event, sort_keys=True))))
                if event_id not in session.event_ids_seen:
                    session.event_ids_seen.add(event_id)
                    new_events.append(event)
            
            session.last_event_check = time.time()
            return new_events
            
    except Exception as e:
        logger.debug(f"Event poll failed: {e}")
    
    return []


def format_event_for_moshi(event: dict) -> Optional[str]:
    """Format MAS event for Moshi injection."""
    event_type = event.get("type", "unknown")
    
    if event_type == "agent_update":
        agent = event.get("agent_name", "An agent")
        message = event.get("message", "")
        if message:
            return f"[SYSTEM] {agent} reports: {message}"
    
    elif event_type == "tool_result":
        tool = event.get("tool_name", "Tool")
        result = event.get("result_summary", "completed")
        return f"[TOOL] {tool}: {result}"
    
    elif event_type == "memory_insight":
        insight = event.get("insight", "")
        if insight:
            return f"[MEMORY] Recall: {insight}"
    
    elif event_type == "notification":
        message = event.get("message", "")
        priority = event.get("priority", "normal")
        if priority == "high":
            return f"[URGENT] {message}"
        return f"[NOTICE] {message}"
    
    elif event.get("message"):
        return f"[EVENT] {event.get('message')}"
    
    return None


async def mas_event_loop(session: BridgeSession, moshi_ws, browser_ws):
    """Background task polling MAS for events."""
    logger.info(f"[{session.session_id[:8]}] MAS event loop started")
    
    while True:
        try:
            await asyncio.sleep(MAS_EVENT_POLL_INTERVAL)
            
            events = await poll_mas_events(session)
            
            for event in events:
                formatted = format_event_for_moshi(event)
                if formatted:
                    logger.info(f"[{session.session_id[:8]}] Injecting event: {formatted[:50]}...")
                    
                    try:
                        await moshi_ws.send_bytes(b"\x02" + formatted.encode("utf-8"))
                    except:
                        pass
                    
                    try:
                        await browser_ws.send_json({
                            "type": "mas_event",
                            "event": event,
                            "formatted": formatted
                        })
                    except:
                        pass
                        
        except asyncio.CancelledError:
            logger.info(f"[{session.session_id[:8]}] MAS event loop stopped")
            break
        except Exception as e:
            logger.debug(f"Event loop error: {e}")


# ============================================================================
# MAS MEMORY CLONING
# ============================================================================

async def clone_to_mas_memory(session: BridgeSession, speaker: str, text: str):
    """Clone transcript to MAS for memory building."""
    if not text or len(text.strip()) < 2:
        return
    
    text = normalize(text)
    timestamp = datetime.now(timezone.utc).isoformat()
    
    entry = {"speaker": speaker, "text": text, "timestamp": timestamp}
    async with session.lock:
        session.transcript_history.append(entry)
        if len(session.transcript_history) > 100:
            session.transcript_history = session.transcript_history[-100:]
    
    asyncio.create_task(_send_to_mas_memory(session, entry))


async def _send_to_mas_memory(session: BridgeSession, entry: dict):
    """Background task to send memory to MAS."""
    try:
        client = await get_http_client()
        payload = {
            "conversation_id": session.conversation_id,
            "session_id": session.session_id,
            "speaker": entry["speaker"],
            "text": entry["text"],
            "timestamp": entry["timestamp"],
            "source": "personaplex_voice"
        }
        
        for endpoint in [
            f"{MAS_ORCHESTRATOR_URL}/voice/memory/log",
            f"{MAS_ORCHESTRATOR_URL}/voice/feedback"
        ]:
            try:
                resp = await client.post(endpoint, json=payload)
                if resp.status_code in (200, 201, 202):
                    return
            except:
                continue
                
    except Exception as e:
        logger.debug(f"Memory clone error: {e}")


# ============================================================================
# MAS ORCHESTRATOR CHAT (for text-based responses)
# ============================================================================

async def get_mas_response(text: str, session: BridgeSession) -> Optional[str]:
    """Get response from MAS orchestrator for complex queries."""
    try:
        client = await get_http_client()
        
        resp = await client.post(
            f"{MAS_ORCHESTRATOR_URL}/voice/orchestrator/chat",
            json={
                "message": text,
                "conversation_id": session.conversation_id,
                "session_id": session.session_id,
                "actor": "user"
            }
        )
        
        if resp.status_code == 200:
            data = resp.json()
            return data.get("response_text")
            
    except Exception as e:
        logger.warning(f"MAS chat failed: {e}")
    
    return None


# ============================================================================
# MOSHI HEALTH CHECK
# ============================================================================

async def check_moshi():
    global moshi_available
    try:
        async with httpx.AsyncClient() as c:
            r = await c.get(f"http://{MOSHI_HOST}:{MOSHI_PORT}/health", timeout=5)
            moshi_available = r.status_code == 200
    except:
        try:
            async with httpx.AsyncClient() as c:
                r = await c.get(f"http://{MOSHI_HOST}:{MOSHI_PORT}/", timeout=5)
                moshi_available = r.status_code in (200, 426)
        except Exception as e:
            moshi_available = "426" in str(e)


@app.on_event("startup")
async def startup():
    await check_moshi()
    asyncio.create_task(periodic_check())


async def periodic_check():
    while True:
        await asyncio.sleep(30)
        await check_moshi()


@app.on_event("shutdown")
async def shutdown():
    global http_client
    if http_client:
        await http_client.aclose()


# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "version": "6.0.0-mas-tools",
        "moshi_available": moshi_available,
        "mas_url": MAS_ORCHESTRATOR_URL,
        "features": {
            "full_duplex": True,
            "mas_tool_calls": True,
            "event_stream": True,
            "memory_cloning": True,
        }
    }


@app.post("/session")
async def create_session(body: SessionCreate = None):
    body = body or SessionCreate()
    sid = str(uuid4())
    s = BridgeSession(
        session_id=sid,
        conversation_id=body.conversation_id or str(uuid4()),
        persona=body.persona,
        voice=body.voice,
        created_at=datetime.now(timezone.utc).isoformat()
    )
    sessions[sid] = s
    logger.info(f"Session created: {sid[:8]}")
    return s.to_dict()


@app.websocket("/ws/{session_id}")
async def ws_bridge(websocket: WebSocket, session_id: str):
    await websocket.accept()
    
    s = sessions.get(session_id) or BridgeSession(
        session_id=session_id,
        conversation_id=str(uuid4()),
        persona="myca",
        voice="myca",
        created_at=datetime.now(timezone.utc).isoformat()
    )
    sessions[session_id] = s
    
    import urllib.parse
    params = urllib.parse.urlencode({
        "text_prompt": MYCA_PERSONA,
        "voice_prompt": "NATF2.pt",
        "audio_temperature": "0.7",
        "text_temperature": "0.7"
    })
    
    event_task = None
    audio_sent_count = 0
    audio_recv_count = 0
    
    try:
        async with aiohttp.ClientSession() as aio:
            async with aio.ws_connect(f"{MOSHI_WS_URL}?{params}") as moshi:
                # Handshake
                hs = await asyncio.wait_for(moshi.receive(), 30)
                
                handshake_ok = False
                if hs.type == aiohttp.WSMsgType.BINARY and hs.data == b'\x00':
                    handshake_ok = True
                elif hs.type == aiohttp.WSMsgType.TEXT:
                    try:
                        data = json.loads(hs.data)
                        if data.get("type") == "connected":
                            handshake_ok = True
                    except:
                        pass
                
                if not handshake_ok:
                    await websocket.send_json({"type": "error", "message": "Moshi handshake failed"})
                    return
                
                await websocket.send_bytes(b'\x00')
                logger.info(f"[{session_id[:8]}] Full-duplex bridge with MAS tools active")
                
                # Start MAS event polling
                event_task = asyncio.create_task(mas_event_loop(s, moshi, websocket))
                
                last_user_text = ""
                last_myca_text = ""
                accumulated_myca_text = ""
                
                async def moshi_to_browser():
                    nonlocal last_myca_text, audio_recv_count, accumulated_myca_text
                    try:
                        async for msg in moshi:
                            if msg.type == aiohttp.WSMsgType.BINARY and len(msg.data) > 0:
                                kind = msg.data[0]
                                
                                if kind == 1:  # Audio
                                    audio_recv_count += 1
                                    await websocket.send_bytes(msg.data)
                                
                                elif kind == 2:  # Text from Moshi
                                    text = msg.data[1:].decode("utf-8", errors="ignore")
                                    await websocket.send_json({"type": "text", "text": text, "speaker": "myca"})
                                    
                                    # Accumulate text for memory cloning
                                    accumulated_myca_text += text
                                    
                                    # When we have a complete phrase, clone to MAS
                                    if any(p in text for p in [".", "!", "?", "\n"]):
                                        normalized = normalize(accumulated_myca_text)
                                        if normalized and normalized != last_myca_text:
                                            last_myca_text = normalized
                                            await clone_to_mas_memory(s, "myca", normalized)
                                        accumulated_myca_text = ""
                                
                                elif kind == 3:  # Control/ACK
                                    text = msg.data[1:].decode("utf-8", errors="ignore")
                                    logger.debug(f"[{session_id[:8]}] Control: {text}")
                                
                            elif msg.type == aiohttp.WSMsgType.TEXT:
                                await websocket.send_text(msg.data)
                                
                    except Exception as e:
                        logger.error(f"Moshi->Browser error: {e}")
                
                async def browser_to_moshi():
                    nonlocal last_user_text, audio_sent_count
                    try:
                        while True:
                            data = await websocket.receive()
                            
                            if "bytes" in data:
                                raw = data["bytes"]
                                audio_sent_count += 1
                                if audio_sent_count <= 5 or audio_sent_count % 100 == 0:
                                    logger.info(f"[{session_id[:8]}] -> Moshi audio #{audio_sent_count}: {len(raw)} bytes")
                                await moshi.send_bytes(raw)
                            
                            elif "text" in data:
                                try:
                                    payload = json.loads(data["text"])
                                    text = normalize(payload.get("text", ""))
                                    
                                    if text and text != last_user_text:
                                        last_user_text = text
                                        await clone_to_mas_memory(s, "user", text)
                                        
                                        # Process for tool calls
                                        asyncio.create_task(process_user_text_for_tools(text, s, moshi))
                                    
                                    # Forward to Moshi if requested
                                    if payload.get("forward_to_moshi", False) and text:
                                        await moshi.send_bytes(b"\x02" + text.encode("utf-8"))
                                        
                                except json.JSONDecodeError:
                                    pass
                                    
                    except WebSocketDisconnect:
                        logger.info(f"[{session_id[:8]}] Browser disconnected")
                    except Exception as e:
                        logger.error(f"Browser->Moshi error: {e}")
                
                await asyncio.gather(
                    moshi_to_browser(),
                    browser_to_moshi(),
                    return_exceptions=True
                )
                
    except Exception as e:
        logger.error(f"WebSocket bridge error: {e}")
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except:
            pass
    finally:
        if event_task:
            event_task.cancel()
        # Log session stats
        logger.info(f"[{session_id[:8]}] Session ended. Audio: sent={audio_sent_count}, recv={audio_recv_count}")


@app.get("/session/{session_id}/history")
async def get_session_history(session_id: str):
    s = sessions.get(session_id)
    if not s:
        return JSONResponse({"error": "Session not found"}, status_code=404)
    return {"session_id": session_id, "history": s.transcript_history}


@app.post("/inject/{session_id}")
async def inject_event(session_id: str, event: dict):
    """Inject an event into an active session."""
    s = sessions.get(session_id)
    if not s:
        return JSONResponse({"error": "Session not found"}, status_code=404)
    
    async with s.lock:
        s.pending_events.append(event)
    
    return {"status": "queued", "session_id": session_id}


@app.get("/")
async def root():
    return RedirectResponse(f"http://{MOSHI_HOST}:{MOSHI_PORT}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8999)
