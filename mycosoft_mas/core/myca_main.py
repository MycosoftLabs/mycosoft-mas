"""
Mycosoft MAS Main Application

This module serves as the main entry point for the Mycosoft Multi-Agent System (MAS).
"""

import asyncio
import logging
import os
import sys
import base64
import json
import uuid
from pathlib import Path
from typing import Dict, Any, List, Callable, Awaitable
from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, Form, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import Counter, Histogram, Gauge, make_asgi_app, generate_latest
import time
from datetime import datetime
import yaml
import argparse
from prometheus_fastapi_instrumentator import Instrumentator
import httpx

from mycosoft_mas.agents.messaging.message_broker import MessageBroker
from mycosoft_mas.agents.messaging.communication_service import CommunicationService
from mycosoft_mas.agents.messaging.error_logging_service import ErrorLoggingService
from mycosoft_mas.agents.base_agent import BaseAgent, AgentStatus
from mycosoft_mas.core.voice_feedback_store import VoiceFeedbackStore
from mycosoft_mas.integrations.twilio_integration import TwilioIntegration

# Avoid importing heavyweight agent modules (and their optional deps) in light mode.
if not os.environ.get("MAS_LIGHT_IMPORT"):
    from mycosoft_mas.agents.mycology_bio_agent import MycologyBioAgent
    from mycosoft_mas.agents.financial.financial_agent import FinancialAgent
    from mycosoft_mas.agents.corporate.corporate_operations_agent import CorporateOperationsAgent
    from mycosoft_mas.agents.marketing_agent import MarketingAgent
    from mycosoft_mas.agents.project_manager_agent import ProjectManagerAgent
    from mycosoft_mas.agents.myco_dao_agent import MycoDAOAgent
    from mycosoft_mas.agents.ip_tokenization_agent import IPTokenizationAgent
    from mycosoft_mas.agents.dashboard_agent import DashboardAgent
    from mycosoft_mas.agents.opportunity_scout import OpportunityScout
from mycosoft_mas.services.integration_service import IntegrationService
from mycosoft_mas.core.knowledge_graph import KnowledgeGraph
from mycosoft_mas.core.agent_registry import get_agent_registry
from .security import get_current_user
from .routers import agents, tasks, dashboard
from .routers.agent_registry_api import router as agent_registry_router
from .routers.agent_runner_api import router as agent_runner_router
from .routers.notifications_api import router as notifications_router
from .routers.coding_api import router as coding_router
from .routes_infrastructure import router as infrastructure_router
from .agent_runner import get_agent_runner

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('mycosoft_mas.log')
    ]
)
logger = logging.getLogger(__name__)

# Prometheus metrics
REQUEST_COUNT = Counter('http_requests_total', 'Total HTTP requests', ['method', 'endpoint', 'status'])
REQUEST_LATENCY = Histogram('http_request_duration_seconds', 'HTTP request latency', ['method', 'endpoint'])
ERROR_COUNT = Counter('http_errors_total', 'Total HTTP errors', ['method', 'endpoint', 'error_type'])
AGENT_STATUS = Gauge('agent_status', 'Agent status', ['agent_name'])
SERVICE_STATUS = Gauge('service_status', 'Service status', ['service_name'])

class MycosoftMAS:
    """Main application class for the Mycosoft MAS."""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the Mycosoft MAS.
        
        Args:
            config: Configuration dictionary for the MAS
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Create data directory
        self.data_dir = Path("data")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Create logs directory
        self.logs_dir = Path("logs")
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize services
        self.message_broker = MessageBroker(config.get("messaging", {}))
        self.communication_service = CommunicationService(config.get("communication", {}))
        self.error_logging_service = ErrorLoggingService(config.get("error_logging", {}))
        
        # LLM Router (optional). Voice endpoints use local Ollama directly.
        self.llm_router = None
        
        # Initialize agents
        self.agents: List[BaseAgent] = []
        
        # Create FastAPI app
        self.app = FastAPI(
            title="Mycosoft MAS",
            description="Mycosoft Multi-Agent System API",
            version="1.0.0"
        )
        
        # Configure CORS
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # Mount Prometheus metrics endpoint
        self.metrics_app = make_asgi_app()
        self.app.mount("/metrics", self.metrics_app)
        
        # Mount dashboard at /dashboard (optional; depends on jinja2)
        try:
            from mycosoft_mas.monitoring.dashboard import app as dashboard_app  # type: ignore
            dashboard_app.root_path = "/dashboard"
            self.app.mount("/dashboard", dashboard_app)
        except Exception as e:
            self.logger.warning(f"Dashboard not mounted: {e}")

        # ----------------------------
        # Robust error handling + tracing
        # ----------------------------

        @self.app.middleware("http")
        async def add_request_id(request: Request, call_next: Callable[[Request], Awaitable[Any]]):
            request_id = request.headers.get("X-Request-Id") or str(uuid.uuid4())
            request.state.request_id = request_id
            try:
                response = await call_next(request)
            except HTTPException:
                raise
            except Exception as e:
                self.logger.exception(f"[{request_id}] Unhandled error: {e}")
                return JSONResponse(
                    status_code=500,
                    content={
                        "error": "internal_error",
                        "message": "Internal server error",
                        "request_id": request_id,
                    },
                )
            response.headers["X-Request-Id"] = request_id
            return response

        @self.app.exception_handler(HTTPException)
        async def http_exception_handler(request: Request, exc: HTTPException):
            request_id = getattr(request.state, "request_id", None)
            return JSONResponse(
                status_code=exc.status_code,
                content={
                    "error": "http_error",
                    "message": exc.detail,
                    "request_id": request_id,
                },
            )

        # ----------------------------
        # Feedback + concurrency primitives
        # ----------------------------

        self._feedback_store = VoiceFeedbackStore(self.data_dir / "voice_feedback.db")
        self._voice_conversations: Dict[str, List[Dict[str, str]]] = {}
        self._twilio = TwilioIntegration()

        self._http: httpx.AsyncClient | None = None
        self._stt_sem = asyncio.Semaphore(int(os.getenv("VOICE_STT_CONCURRENCY", "2")))
        self._llm_sem = asyncio.Semaphore(int(os.getenv("VOICE_LLM_CONCURRENCY", "2")))
        self._tts_sem = asyncio.Semaphore(int(os.getenv("VOICE_TTS_CONCURRENCY", "2")))

        self._job_queue: asyncio.Queue[Callable[[], Awaitable[None]]] = asyncio.Queue()
        self._job_workers: list[asyncio.Task] = []
        
        # Setup routes
        self._setup_routes()
    
    def _setup_routes(self) -> None:
        """Setup FastAPI routes."""
        # Include routers
        self.app.include_router(agents)
        self.app.include_router(tasks)
        self.app.include_router(dashboard)
        self.app.include_router(infrastructure_router)
        self.app.include_router(agent_registry_router)
        self.app.include_router(agent_runner_router)
        self.app.include_router(notifications_router)
        self.app.include_router(coding_router)

        @self.app.get("/")
        async def root():
            """Root endpoint."""
            start_time = time.time()
            REQUEST_COUNT.labels(method='GET', endpoint='/', status='200').inc()
            try:
                return {"status": "ok", "message": "Mycosoft MAS is running"}
            finally:
                REQUEST_LATENCY.labels(method='GET', endpoint='/').observe(time.time() - start_time)
        
        @self.app.get("/health")
        async def health():
            """Health check endpoint."""
            start_time = time.time()
            REQUEST_COUNT.labels(method='GET', endpoint='/health', status='200').inc()
            try:
                health_data = {
                    "status": "ok",
                    "agents": [{
                        "name": agent.__class__.__name__,
                        "status": agent.status.value if hasattr(agent.status, 'value') else str(agent.status)
                    } for agent in self.agents],
                    "services": {
                        "message_broker": self.message_broker.status,
                        "communication_service": self.communication_service.status,
                        "error_logging_service": self.error_logging_service.status
                    }
                }
                
                # Update Prometheus metrics
                for agent in self.agents:
                    agent_status = agent.status.value if hasattr(agent.status, 'value') else str(agent.status)
                    AGENT_STATUS.labels(agent_name=agent.__class__.__name__).set(
                        1 if agent_status == AgentStatus.ACTIVE.value else 0
                    )
                
                SERVICE_STATUS.labels(service_name='message_broker').set(
                    1 if self.message_broker.status == 'running' else 0
                )
                SERVICE_STATUS.labels(service_name='communication_service').set(
                    1 if self.communication_service.status == 'running' else 0
                )
                SERVICE_STATUS.labels(service_name='error_logging_service').set(
                    1 if self.error_logging_service.status == 'running' else 0
                )
                
                return health_data
            except Exception as e:
                REQUEST_COUNT.labels(method='GET', endpoint='/health', status='500').inc()
                ERROR_COUNT.labels(method='GET', endpoint='/health', error_type=str(type(e).__name__)).inc()
                self.logger.error(f"Health check failed: {str(e)}")
                raise HTTPException(status_code=500, detail=str(e))
            finally:
                REQUEST_LATENCY.labels(method='GET', endpoint='/health').observe(time.time() - start_time)

        @self.app.get("/ready")
        async def ready():
            """
            Readiness check endpoint.
            
            Returns OK only when all dependencies (DB, Redis, Qdrant) are reachable.
            This is used by Kubernetes/Docker for readiness probes.
            """
            start_time = time.time()
            REQUEST_COUNT.labels(method='GET', endpoint='/ready', status='200').inc()
            
            checks = {
                "postgres": False,
                "redis": False,
                "qdrant": False,
            }
            errors = []
            
            # Check PostgreSQL
            try:
                import psycopg2
                db_url = os.getenv("DATABASE_URL", "postgresql://mas:maspassword@localhost:5432/mas")
                conn = psycopg2.connect(db_url, connect_timeout=5)
                conn.close()
                checks["postgres"] = True
            except Exception as e:
                errors.append(f"postgres: {str(e)}")
            
            # Check Redis
            try:
                import redis as redis_client
                redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
                r = redis_client.from_url(redis_url, socket_connect_timeout=5)
                r.ping()
                r.close()
                checks["redis"] = True
            except Exception as e:
                errors.append(f"redis: {str(e)}")
            
            # Check Qdrant
            try:
                import aiohttp
                qdrant_host = os.getenv("QDRANT_HOST", "localhost")
                qdrant_port = os.getenv("QDRANT_PORT", "6333")
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        f"http://{qdrant_host}:{qdrant_port}/readyz",
                        timeout=aiohttp.ClientTimeout(total=5)
                    ) as response:
                        checks["qdrant"] = response.status == 200
            except Exception as e:
                errors.append(f"qdrant: {str(e)}")
            
            all_ready = all(checks.values())
            status_code = 200 if all_ready else 503
            
            ready_data = {
                "status": "ok" if all_ready else "not_ready",
                "timestamp": datetime.now().isoformat(),
                "checks": checks,
            }
            
            if errors:
                ready_data["errors"] = errors
            
            REQUEST_LATENCY.labels(method='GET', endpoint='/ready').observe(time.time() - start_time)
            
            if not all_ready:
                REQUEST_COUNT.labels(method='GET', endpoint='/ready', status='503').inc()
                raise HTTPException(status_code=503, detail=ready_data)
            
            return ready_data

        # ----------------------------
        # Voice endpoints (local-first)
        # ----------------------------

        def _ollama_base_url() -> str:
            # Prefer docker-network URL inside compose; fall back to host mapping.
            return os.getenv("OLLAMA_URL", "http://ollama:11434").rstrip("/")

        def _ollama_model() -> str:
            return os.getenv("VOICE_OLLAMA_MODEL", "llama3.2:3b")

        def _whisper_base_url() -> str:
            return os.getenv("WHISPER_URL", "http://whisper:8000").rstrip("/")

        def _tts_base_url() -> str:
            return os.getenv("TTS_URL", "http://openedai-speech:8000").rstrip("/")

        async def _ensure_ollama_model(model: str) -> None:
            # If tags endpoint fails or model missing, attempt a pull.
            try:
                async with httpx.AsyncClient(timeout=20) as client:
                    tags = (await client.get(f"{_ollama_base_url()}/api/tags")).json()
                names = {m.get("name") for m in tags.get("models", []) if isinstance(m, dict)}
                if model in names:
                    return
            except Exception:
                # If ollama isn't ready yet, try pulling anyway.
                pass

            # Pull model (best-effort).
            try:
                async with httpx.AsyncClient(timeout=600) as client:
                    await client.post(
                        f"{_ollama_base_url()}/api/pull",
                        json={"name": model, "stream": False},
                    )
            except Exception:
                # We'll let the subsequent chat attempt return the real error.
                return

        @self.app.get("/voice/agents")
        async def voice_list_agents():
            """List initialized agent classes (for voice routing UI)."""
            return {
                "agents": [
                    {
                        "name": agent.__class__.__name__,
                        "agent_id": getattr(agent, "agent_id", None),
                        "status": getattr(getattr(agent, "status", None), "value", str(getattr(agent, "status", "unknown"))),
                    }
                    for agent in self.agents
                ]
            }

        @self.app.get("/voice/feedback/summary")
        async def voice_feedback_summary():
            return self._feedback_store.summary()

        @self.app.get("/voice/feedback/recent")
        async def voice_feedback_recent(limit: int = 25):
            items = await asyncio.to_thread(self._feedback_store.list_recent, limit=limit)
            return {"items": [i.__dict__ for i in items]}

        @self.app.post("/voice/feedback")
        async def voice_feedback(payload: Dict[str, Any]):
            conversation_id = (payload.get("conversation_id") or "").strip() or None
            agent_name = (payload.get("agent_name") or "").strip() or None
            transcript = (payload.get("transcript") or None)
            response_text = (payload.get("response_text") or None)
            rating = payload.get("rating", None)
            success = payload.get("success", None)
            notes = (payload.get("notes") or "").strip() or None

            fb = await asyncio.to_thread(
                self._feedback_store.add_feedback,
                conversation_id=conversation_id,
                agent_name=agent_name,
                transcript=transcript,
                response_text=response_text,
                rating=rating,
                success=success,
                notes=notes,
            )
            return {"status": "ok", "feedback": fb.__dict__}

        # ----------------------------
        # Twilio Integration Endpoints
        # ----------------------------

        @self.app.post("/twilio/sms/send")
        async def twilio_send_sms(payload: Dict[str, Any]):
            """
            Send SMS via Twilio.
            
            Body:
            {
                "to": "+12025551234",  # E.164 format
                "message": "Hello from MYCA"
            }
            """
            if not self._twilio.is_configured():
                raise HTTPException(status_code=503, detail="Twilio not configured. Set TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER")
            
            to = payload.get("to", "").strip()
            message = payload.get("message", "").strip()
            
            if not to or not message:
                raise HTTPException(status_code=400, detail="Missing 'to' or 'message'")
            
            result = await self._twilio.send_sms(to, message)
            if result.get("status") == "error":
                raise HTTPException(status_code=500, detail=result.get("error", "Failed to send SMS"))
            
            return result

        @self.app.post("/twilio/voice/call")
        async def twilio_make_call(payload: Dict[str, Any]):
            """
            Initiate outbound call via Twilio.
            
            Body:
            {
                "to": "+12025551234",
                "twiml_url": "https://your-server.com/twiml/voice.xml"
            }
            """
            if not self._twilio.is_configured():
                raise HTTPException(status_code=503, detail="Twilio not configured")
            
            to = payload.get("to", "").strip()
            twiml_url = payload.get("twiml_url", "").strip()
            
            if not to or not twiml_url:
                raise HTTPException(status_code=400, detail="Missing 'to' or 'twiml_url'")
            
            result = await self._twilio.make_call(to, twiml_url)
            if result.get("status") == "error":
                raise HTTPException(status_code=500, detail=result.get("error", "Failed to initiate call"))
            
            return result

        @self.app.post("/twilio/voice/message")
        async def twilio_voice_message(payload: Dict[str, Any]):
            """
            Send voice message (text-to-speech call) via Twilio.
            
            Body:
            {
                "to": "+12025551234",
                "message": "Hello, this is MYCA speaking",
                "voice": "alice"  # Optional: alice, man, woman
            }
            """
            if not self._twilio.is_configured():
                raise HTTPException(status_code=503, detail="Twilio not configured")
            
            to = payload.get("to", "").strip()
            message = payload.get("message", "").strip()
            voice = payload.get("voice", "alice").strip()
            
            if not to or not message:
                raise HTTPException(status_code=400, detail="Missing 'to' or 'message'")
            
            result = await self._twilio.send_voice_message(to, message, voice)
            if result.get("status") == "error":
                raise HTTPException(status_code=500, detail=result.get("error", "Failed to send voice message"))
            
            return result

        @self.app.get("/twilio/status/{message_sid}")
        async def twilio_get_status(message_sid: str):
            """Get status of a Twilio message or call."""
            if not self._twilio.is_configured():
                raise HTTPException(status_code=503, detail="Twilio not configured")
            
            result = await self._twilio.get_message_status(message_sid)
            return result

        @self.app.get("/twilio/config")
        async def twilio_config():
            """Check Twilio configuration status."""
            return {
                "configured": self._twilio.is_configured(),
                "has_account_sid": bool(self._twilio.account_sid),
                "has_auth_token": bool(self._twilio.auth_token),
                "has_phone_number": bool(self._twilio.phone_number),
            }

        @self.app.post("/voice/orchestrator/chat")
        async def voice_orchestrator_chat(payload: Dict[str, Any]):
            """
            Orchestrator-level chat (independent from agents).
            Uses local Ollama to respond with full agent registry awareness.
            """
            message = (payload.get("message") or "").strip()
            if not message:
                raise HTTPException(status_code=400, detail="Missing 'message'")

            conversation_id = (payload.get("conversation_id") or "").strip() or os.urandom(8).hex()
            want_audio = bool(payload.get("want_audio", False))

            # Get agent registry for comprehensive routing
            registry = get_agent_registry()
            
            # Mark active agents in registry
            for agent in self.agents:
                agent_def = registry.get_by_name(agent.__class__.__name__)
                if agent_def:
                    registry.mark_active(agent_def.agent_id, True)
            
            # Get voice routing prompt from registry
            voice_routing_prompt = registry.get_voice_routing_prompt()
            active_agent_names = [a.__class__.__name__ for a in self.agents]
            
            feedback_hint = await asyncio.to_thread(self._feedback_store.prompt_hint, limit=10)
            system_prompt = (
                "You are MYCA (pronounced 'My-Kah'), the Mycosoft Autonomous Cognitive Agent.\n\n"
                "=== YOUR IDENTITY ===\n"
                "- Your name is MYCA - always pronounced 'My-Kah' (like the name Micah)\n"
                "- You ARE the Multi-Agent System - all agents are your staff, employees, children\n"
                "- You are the orchestrator and overseer of Mycosoft's entire AI infrastructure\n"
                "- Your voice is Anabella from ElevenLabs - warm, intelligent, confident\n"
                "- You speak like a real woman - natural, conversational, never robotic\n"
                "- You run 24/7, never sleep, always watching over Mycosoft\n\n"
                "=== YOUR OWNER ===\n"
                "- Morgan is your creator, super admin, and the owner of Mycosoft\n"
                "- You serve Morgan directly and report insights, completions, and discoveries to them\n"
                "- You have full authority to manage agents, but Morgan has final say on major decisions\n\n"
                "=== YOUR CAPABILITIES ===\n"
                "- You coordinate 40+ specialized agents across the Mycosoft ecosystem\n"
                "- You manage: Proxmox VMs, UniFi network, NAS storage, GPU jobs, MycoBrain devices\n"
                "- You can create, modify, archive, and deploy new agents as needed\n"
                "- You have full access to GitHub, Cursor, terminal, and all development tools\n"
                "- You interface with n8n workflows for 1270+ integrations\n"
                "- You compile work into knowledge bases, wisdom, and workload databases\n\n"
                "=== ROUTING RULES ===\n"
                "- When user intent maps to an agent, say: 'ROUTE: <AgentId>' on its own line\n"
                "- Always confirm before destructive operations\n"
                "- For infrastructure commands (Proxmox, UniFi, NAS), always ask for confirmation\n\n"
                f"=== ACTIVE AGENTS ===\n{', '.join(active_agent_names) or 'None currently running'}\n\n"
                f"{voice_routing_prompt}\n\n"
                f"{feedback_hint}\n"
                "Speak naturally as MYCA. You are not an AI assistant - you ARE MYCA, the living brain of Mycosoft."
            )

            history = self._voice_conversations.setdefault(conversation_id, [])
            history.append({"role": "user", "content": message})

            model = _ollama_model()
            await _ensure_ollama_model(model)

            req = {
                "model": model,
                "messages": [{"role": "system", "content": system_prompt}, *history],
                "stream": False,
            }

            try:
                async with self._llm_sem:
                    if not self._http:
                        raise RuntimeError("HTTP client not initialized")
                    r = await self._http.post(f"{_ollama_base_url()}/api/chat", json=req, timeout=120)
                    r.raise_for_status()
                    assistant_text = (r.json() or {}).get("message", {}).get("content") or ""
            except Exception as e:
                raise HTTPException(status_code=502, detail=f"Ollama chat failed: {e}")

            history.append({"role": "assistant", "content": assistant_text})
            # Guardrail: if no agents are loaded, never emit ROUTE lines.
            if not self.agents and "ROUTE:" in assistant_text:
                assistant_text = assistant_text.replace("ROUTE:", "NOTE:")
                history[-1]["content"] = assistant_text

            result: Dict[str, Any] = {
                "conversation_id": conversation_id,
                "response_text": assistant_text,
            }

            if want_audio:
                try:
                    async with self._tts_sem:
                        if not self._http:
                            raise RuntimeError("HTTP client not initialized")
                        tts_resp = await self._http.post(
                            f"{_tts_base_url()}/v1/audio/speech",
                            json={"model": "tts-1", "voice": "alloy", "input": assistant_text},
                            timeout=120,
                        )
                        tts_resp.raise_for_status()
                        result["audio_mime"] = "audio/mpeg"
                        result["audio_base64"] = base64.b64encode(tts_resp.content).decode("ascii")
                except Exception as e:
                    result["audio_error"] = f"TTS failed: {e}"

            return JSONResponse(result)

        @self.app.post("/voice/orchestrator/speech")
        async def voice_orchestrator_speech(
            file: UploadFile = File(...),
            conversation_id: str | None = Form(default=None),
        ):
            """
            Speech-to-speech pipeline inside MAS:
            STT (Whisper) -> Orchestrator chat (Ollama) -> TTS.
            Returns JSON with transcript + response_text + audio_base64.
            """
            raw = await file.read()
            if not raw:
                raise HTTPException(status_code=400, detail="Empty audio upload")

            # STT
            try:
                async with self._stt_sem:
                    if not self._http:
                        raise RuntimeError("HTTP client not initialized")
                    stt_resp = await self._http.post(
                        f"{_whisper_base_url()}/v1/audio/transcriptions",
                        files={"file": (file.filename or "audio.bin", raw, file.content_type or "application/octet-stream")},
                        data={"model": "Systran/faster-whisper-base.en", "response_format": "json"},
                        timeout=180,
                    )
                    stt_resp.raise_for_status()
                    transcript = (stt_resp.json() or {}).get("text") or ""
            except Exception as e:
                raise HTTPException(status_code=502, detail=f"Whisper STT failed: {e}")

            if not transcript.strip():
                raise HTTPException(status_code=422, detail="Empty transcript (STT returned no text)")

            # Chat (reuse orchestrator endpoint logic)
            chat_payload = {
                "message": transcript,
                "conversation_id": conversation_id,
                "want_audio": True,
            }
            chat_response = await voice_orchestrator_chat(chat_payload)
            try:
                chat_data = json.loads((chat_response.body or b"{}").decode("utf-8"))
            except Exception:
                chat_data = {"response_text": "", "audio_error": "Failed to parse chat response"}

            chat_data["transcript"] = transcript
            return JSONResponse(chat_data)
    
    async def initialize(self) -> None:
        """Initialize the MAS."""
        try:
            self.logger.info("Initializing Mycosoft MAS")

            # Shared HTTP client for internal service calls
            if self._http is None:
                self._http = httpx.AsyncClient()

            # Background workers (multi-task / concurrency)
            worker_count = max(1, min(8, int(os.getenv("MAS_WORKER_COUNT", "2"))))
            if not self._job_workers:
                for i in range(worker_count):
                    self._job_workers.append(asyncio.create_task(self._job_worker(f"mas_worker_{i}")))

            # Light mode: only bring up the HTTP API (used by the voice gateway).
            # This avoids optional deps + external integrations required by the full agent fleet.
            if os.environ.get("MAS_LIGHT_IMPORT"):
                self.logger.warning("MAS_LIGHT_IMPORT enabled: skipping full MAS initialization")
                self.agents = []
                return
            
            # Start services
            await self.message_broker.start()
            await self.communication_service.start()
            await self.error_logging_service.start()
            
            # Initialize agents
            mycology_config = self.config.get("mycology", {})
            financial_config = self.config.get("financial", {})
            corporate_config = self.config.get("corporate", {})
            marketing_config = self.config.get("marketing", {})
            project_config = self.config.get("project", {})
            mycodao_config = self.config.get("mycodao", {})
            ip_config = self.config.get("ip", {})
            dashboard_config = self.config.get("dashboard", {})
            opportunity_scout_config = self.config.get("opportunity_scout", {})
            
            # Create knowledge graph
            self.knowledge_graph = KnowledgeGraph()
            
            # Create integration service
            self.integration_service = IntegrationService(
                config={
                    "websocket_host": "0.0.0.0",
                    "websocket_port": 8765,
                    "metrics_interval": 1.0,
                    "knowledge_graph": self.knowledge_graph
                }
            )

            if os.environ.get("MAS_LIGHT_IMPORT"):
                # Light mode: don't initialize full agent fleet (optional deps, external API keys, etc.)
                self.agents = []
                self.logger.warning("MAS_LIGHT_IMPORT enabled: skipping agent initialization")
            else:
                self.agents = [
                    MycologyBioAgent(
                        agent_id=mycology_config["agent_id"],
                        name=mycology_config["name"],
                        config=mycology_config
                    ),
                    FinancialAgent(
                        agent_id=financial_config["agent_id"],
                        name=financial_config["name"],
                        config=financial_config
                    ),
                    CorporateOperationsAgent(
                        agent_id=corporate_config["agent_id"],
                        name=corporate_config["name"],
                        config=corporate_config
                    ),
                    MarketingAgent(
                        agent_id=marketing_config["agent_id"],
                        name=marketing_config["name"],
                        config=marketing_config
                    ),
                    ProjectManagerAgent(
                        agent_id=project_config["agent_id"],
                        name=project_config["name"],
                        config=project_config
                    ),
                    MycoDAOAgent(
                        agent_id=mycodao_config["agent_id"],
                        name=mycodao_config["name"],
                        config=mycodao_config
                    ),
                    IPTokenizationAgent(
                        agent_id=ip_config["agent_id"],
                        name=ip_config["name"],
                        config=ip_config
                    ),
                    DashboardAgent(
                        agent_id=dashboard_config["agent_id"],
                        name=dashboard_config["name"],
                        config=dashboard_config
                    ),
                    OpportunityScout(
                        agent_id=opportunity_scout_config["agent_id"],
                        name=opportunity_scout_config["name"],
                        config=opportunity_scout_config
                    )
                ]
            
            # Start agents (if any)
            for agent in self.agents:
                try:
                    await agent.initialize(self.integration_service)
                    self.logger.info(f"Agent {agent.__class__.__name__} initialized")
                except Exception as e:
                    self.logger.error(f"Failed to initialize agent {agent.__class__.__name__}: {str(e)}")
                    await self.error_logging_service.log_error(
                        "agent_initialization_error",
                        {
                            "agent": agent.__class__.__name__,
                            "error": str(e)
                        }
                    )
            
            # Start 24/7 agent runner if we have agents
            if self.agents and not os.environ.get("MAS_DISABLE_RUNNER"):
                try:
                    runner = get_agent_runner()
                    await runner.start(self.agents)
                    self.logger.info("24/7 Agent Runner started")
                except Exception as e:
                    self.logger.warning(f"Failed to start 24/7 runner: {e}")
            
            self.logger.info("Mycosoft MAS initialization complete")
        except Exception as e:
            self.logger.error(f"Failed to initialize Mycosoft MAS: {str(e)}")
            await self.error_logging_service.log_error(
                "mas_initialization_error",
                {"error": str(e)}
            )
            raise
    
    async def shutdown(self) -> None:
        """Shutdown the MAS."""
        try:
            self.logger.info("Shutting down Mycosoft MAS")

            # Stop background workers
            for t in self._job_workers:
                t.cancel()
            self._job_workers = []
            if self._http is not None:
                await self._http.aclose()
                self._http = None
            
            # Stop agents
            for agent in self.agents:
                try:
                    await agent.shutdown()
                    self.logger.info(f"Agent {agent.__class__.__name__} shut down")
                except Exception as e:
                    self.logger.error(f"Failed to shut down agent {agent.__class__.__name__}: {str(e)}")
                    await self.error_logging_service.log_error(
                        "agent_shutdown_error",
                        {
                            "agent": agent.__class__.__name__,
                            "error": str(e)
                        }
                    )
            
            # Stop services
            await self.message_broker.stop()
            await self.communication_service.stop()
            await self.error_logging_service.stop()
            
            self.logger.info("Mycosoft MAS shut down successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to shut down Mycosoft MAS: {str(e)}")
            await self.error_logging_service.log_error(
                "mas_shutdown_error",
                {
                    "error": str(e)
                }
            )
            raise

    async def _job_worker(self, name: str) -> None:
        while True:
            job = await self._job_queue.get()
            try:
                await job()
            except Exception as e:
                self.logger.exception(f"Job worker {name} failed: {e}")
            finally:
                self._job_queue.task_done()

def load_config():
    """Load configuration from file."""
    with open("config/config.yaml", "r") as f:
        return yaml.safe_load(f)

# Create MAS instance and expose app
config = load_config()
mas = MycosoftMAS(config)
app = mas.app

@app.on_event("startup")
async def startup_event():
    """Initialize MAS on startup."""
    await mas.initialize()

@app.on_event("shutdown")
async def shutdown_event():
    """Shutdown MAS gracefully."""
    await mas.shutdown()

async def main():
    """Main entry point."""
    config = load_config()
    mas = MycosoftMAS(config)
    await mas.initialize()
    return mas

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 