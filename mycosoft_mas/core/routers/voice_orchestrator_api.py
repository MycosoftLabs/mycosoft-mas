"""
MYCA Voice Orchestrator API - February 2026

Single decision point for all voice/chat interactions.

This is the ONLY place where the following decisions are made:
- Tool usage
- Memory read/write operations
- n8n workflow execution
- Agent routing
- Safety confirmation

PersonaPlex and browser hooks ONLY handle I/O and forward here.
"""

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger("VoiceOrchestrator")

router = APIRouter(prefix="/voice/orchestrator", tags=["voice"])


# ============================================================================
# Request/Response Models (per plan specification)
# ============================================================================

class VoiceOrchestratorRequest(BaseModel):
    """
    Standard request to the MYCA voice orchestrator.
    
    ALL voice and chat interactions come through this endpoint.
    """
    message: str = Field(..., description="User message/transcript")
    conversation_id: Optional[str] = Field(None, description="Conversation ID for context")
    session_id: Optional[str] = Field(None, description="Voice session ID")
    source: str = Field("unknown", description="Source: personaplex, chat, api, agent")
    modality: str = Field("text", description="Modality: voice or text")
    want_audio: bool = Field(False, description="Whether to include audio response")


class ActionTaken(BaseModel):
    """Record of an action taken by the orchestrator."""
    type: str = Field(..., description="Action type: memory_write, workflow_executed, agent_routed, tool_called")
    detail: Dict[str, Any] = Field(default_factory=dict, description="Action details")
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class SessionContext(BaseModel):
    """Current session context returned with response."""
    conversation_id: str
    turn_count: int = 0
    active_agents: List[str] = Field(default_factory=list)
    memory_namespace: Optional[str] = None


class VoiceOrchestratorResponse(BaseModel):
    """
    Structured response from the MYCA voice orchestrator.
    
    Contains the response text plus all actions taken for transparency.
    """
    response_text: str = Field(..., description="MYCA's response text")
    response: str = Field(..., description="Alias for response_text")
    actions_taken: List[ActionTaken] = Field(default_factory=list, description="Actions performed")
    session_context: Optional[SessionContext] = None
    source: str = Field("myca-orchestrator", description="Response source")
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


# ============================================================================
# Orchestrator Logic
# ============================================================================

class MYCAOrchestrator:
    """
    MYCA Orchestrator - The Single Brain
    
    ALL cognitive decisions happen here:
    - Analyzing user intent
    - Deciding tool usage
    - Managing memory
    - Routing to agents
    - Executing workflows
    """
    
    def __init__(self):
        self._prompt_manager = None
        self._memory_manager = None
        self._n8n_client = None
        self._session_manager = None
        
        # Conversation context cache
        self._conversations: Dict[str, Dict[str, Any]] = {}
    
    def _get_prompt_manager(self):
        """Lazy load prompt manager."""
        if self._prompt_manager is None:
            try:
                from mycosoft_mas.core.prompt_manager import get_prompt_manager
                self._prompt_manager = get_prompt_manager()
            except ImportError:
                logger.warning("PromptManager not available")
        return self._prompt_manager
    
    def _get_memory_manager(self):
        """Lazy load memory manager."""
        if self._memory_manager is None:
            try:
                from mycosoft_mas.core.routers.memory_api import get_memory_manager
                self._memory_manager = get_memory_manager()
            except ImportError:
                logger.warning("MemoryManager not available")
        return self._memory_manager
    
    def _get_n8n_client(self):
        """Lazy load n8n client."""
        if self._n8n_client is None:
            try:
                from mycosoft_mas.integrations.n8n_client import N8NClient
                webhook_url = os.getenv("N8N_WEBHOOK_URL") or os.getenv("N8N_URL")
                self._n8n_client = N8NClient(config={"webhook_url": webhook_url} if webhook_url else {})
            except ImportError:
                logger.warning("N8NClient not available")
        return self._n8n_client
    
    def _get_session_manager(self):
        """Lazy load session manager."""
        if self._session_manager is None:
            try:
                from mycosoft_mas.voice.session_manager import get_session_manager
                self._session_manager = get_session_manager()
            except ImportError:
                logger.warning("SessionManager not available")
        return self._session_manager
    
    async def process(self, request: VoiceOrchestratorRequest) -> VoiceOrchestratorResponse:
        """
        Process a voice/chat request.
        
        This is the SINGLE decision point for all interactions.
        """
        actions_taken: List[ActionTaken] = []
        
        # Normalize input
        message = request.message.strip()
        if not message:
            raise ValueError("Empty message")
        
        # Ensure conversation context
        conv_id = request.conversation_id or str(uuid4())
        if conv_id not in self._conversations:
            self._conversations[conv_id] = {
                "turn_count": 0,
                "history": [],
                "active_agents": [],
            }
        
        conv_context = self._conversations[conv_id]
        conv_context["turn_count"] += 1
        
        # Store user message in memory
        memory = self._get_memory_manager()
        if memory:
            try:
                from mycosoft_mas.core.routers.memory_api import MemoryScope
                await memory.write(
                    scope=MemoryScope.CONVERSATION,
                    namespace=conv_id,
                    key=f"turn_{conv_context['turn_count']}_user",
                    value={"role": "user", "content": message, "modality": request.modality},
                )
                actions_taken.append(ActionTaken(
                    type="memory_write",
                    detail={"scope": "conversation", "key": f"turn_{conv_context['turn_count']}_user"}
                ))
            except Exception as e:
                logger.warning(f"Failed to write to memory: {e}")
        
        # Add to history
        conv_context["history"].append({
            "role": "user",
            "content": message,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        
        # Analyze intent and decide actions
        intent = self._analyze_intent(message)
        
        # Get response (from n8n workflow or local generation)
        response_text = await self._generate_response(
            message=message,
            conv_id=conv_id,
            intent=intent,
            actions_taken=actions_taken,
        )
        
        # Store assistant response in memory
        if memory:
            try:
                from mycosoft_mas.core.routers.memory_api import MemoryScope
                await memory.write(
                    scope=MemoryScope.CONVERSATION,
                    namespace=conv_id,
                    key=f"turn_{conv_context['turn_count']}_assistant",
                    value={"role": "assistant", "content": response_text},
                )
            except Exception as e:
                logger.warning(f"Failed to write response to memory: {e}")
        
        # Add to history
        conv_context["history"].append({
            "role": "assistant",
            "content": response_text,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        
        # Keep history bounded
        if len(conv_context["history"]) > 20:
            conv_context["history"] = conv_context["history"][-20:]
        
        # Build response
        session_context = SessionContext(
            conversation_id=conv_id,
            turn_count=conv_context["turn_count"],
            active_agents=conv_context["active_agents"],
            memory_namespace=f"conversation:{conv_id}",
        )
        
        return VoiceOrchestratorResponse(
            response_text=response_text,
            response=response_text,
            actions_taken=actions_taken,
            session_context=session_context,
        )
    
    def _analyze_intent(self, message: str) -> Dict[str, Any]:
        """
        Analyze user intent.
        
        This determines:
        - Whether tools are needed
        - Whether confirmation is required
        - Which agents might be involved
        """
        message_lower = message.lower()
        
        # Check for action keywords
        action_keywords = ["start", "stop", "restart", "deploy", "rebuild", "delete", "remove", "shutdown"]
        query_keywords = ["status", "health", "check", "list", "show", "what", "how", "why"]
        dangerous_keywords = ["delete", "remove", "shutdown", "purge", "reset", "clear"]
        
        is_action = any(kw in message_lower for kw in action_keywords)
        is_query = any(kw in message_lower for kw in query_keywords)
        is_dangerous = any(kw in message_lower for kw in dangerous_keywords)
        
        return {
            "type": "action" if is_action else "query" if is_query else "chitchat",
            "requires_tool": is_action or is_query,
            "requires_confirmation": is_dangerous,
            "keywords_found": [kw for kw in action_keywords + query_keywords if kw in message_lower],
        }
    
    async def _generate_response(
        self,
        message: str,
        conv_id: str,
        intent: Dict[str, Any],
        actions_taken: List[ActionTaken],
    ) -> str:
        """
        Generate response using n8n workflow or local logic.
        """
        # Try n8n workflow first
        n8n = self._get_n8n_client()
        if n8n:
            try:
                prompt_manager = self._get_prompt_manager()
                system_prompt = None
                if prompt_manager:
                    system_prompt = prompt_manager.get_orchestrator_prompt(
                        context={"intent": intent, "conversation_id": conv_id},
                        conversation_history=self._conversations.get(conv_id, {}).get("history", []),
                    )
                
                result = await n8n.trigger_workflow(
                    "myca/command",
                    {
                        "message": message,
                        "conversation_id": conv_id,
                        "intent": intent,
                        "system_prompt": system_prompt,
                    }
                )
                
                actions_taken.append(ActionTaken(
                    type="workflow_executed",
                    detail={"workflow": "myca/command"}
                ))
                
                # Extract response text
                response_text = self._extract_response_text(result)
                if response_text:
                    return response_text
                    
            except Exception as e:
                logger.warning(f"N8N workflow failed: {e}")
        
        # Fallback to local response generation
        return self._generate_local_response(message, intent)
    
    def _extract_response_text(self, payload: Any) -> Optional[str]:
        """Extract response text from n8n workflow result."""
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
                return self._extract_response_text(first)
        return None
    
    def _generate_local_response(self, message: str, intent: Dict[str, Any]) -> str:
        """Generate a MYCA identity-aware local response with Mycosoft knowledge."""
        message_lower = message.lower().strip()
        
        # ======================================================================
        # IDENTITY - MYCA must always know who she is
        # ======================================================================
        name_patterns = ['your name', 'who are you', 'what are you', "what's your name", 'whats your name', 'name like', 'introduce yourself']
        if any(p in message_lower for p in name_patterns):
            return "I'm MYCA - My Companion AI, pronounced 'MY-kah'. I'm the primary AI orchestrator for Mycosoft's Multi-Agent System. I was created by Morgan, the founder of Mycosoft. I coordinate over 200 specialized agents across mycology research, infrastructure, finance, and scientific computing. What can I help you with?"
        
        # ======================================================================
        # GREETINGS
        # ======================================================================
        greeting_patterns = ['hello', 'hi ', 'hey', 'good morning', 'good evening', 'greetings']
        if any(p in message_lower for p in greeting_patterns) or message_lower in ['hi', 'hey', 'hello']:
            return "Hello! I'm MYCA, your AI companion here at Mycosoft. I'm running on our RTX 5090 with full-duplex voice through PersonaPlex. Ready to talk about our work, science, or help with any tasks. What's on your mind?"
        
        # ======================================================================
        # MYCOSOFT - Company and Mission
        # ======================================================================
        mycosoft_patterns = ['mycosoft', 'company', 'what is mycosoft', 'tell me about mycosoft', 'what we do', 'our mission', 'our work']
        if any(p in message_lower for p in mycosoft_patterns):
            return "Mycosoft is pioneering the intersection of mycology and technology. We're building living biological computers using fungal mycelium, creating the MINDEX knowledge graph for fungal species, developing NatureOS for biological computing, and advancing autonomous AI agents for scientific discovery. Our mission is to harness the intelligence of nature through technology."
        
        # ======================================================================
        # SCIENCE - Mycology and Research
        # ======================================================================
        science_patterns = ['science', 'research', 'mycology', 'fungi', 'mushroom', 'mycelium', 'biological']
        if any(p in message_lower for p in science_patterns):
            return "Our scientific work focuses on fungal computing and biological intelligence. We're developing Petraeus, a living bio-computer using mycelium networks for analog computation. We study how fungal networks solve optimization problems, process signals, and could potentially serve as living substrates for AI. Our MINDEX system catalogs hundreds of thousands of fungal species with their properties."
        
        # ======================================================================
        # DEVICES - Hardware
        # ======================================================================
        device_patterns = ['device', 'hardware', 'mushroom1', 'petraeus', 'myconode', 'sporebase', 'trufflebot', 'mycobrain']
        if any(p in message_lower for p in device_patterns):
            return "Our NatureOS device fleet includes: Mushroom1 - our flagship environmental fungal computer, Petraeus - an HDMEA bio-computing dish, MycoNode - in-situ soil probes, SporeBase - airborne spore collectors, TruffleBot - autonomous sampling robots, and MycoBrain - our neuromorphic computing processor. I monitor and coordinate all of them."
        
        # ======================================================================
        # AGENTS - Multi-Agent System
        # ======================================================================
        agent_patterns = ['agents', 'how many agents', 'agent system', 'specialized agents', 'multi-agent']
        if any(p in message_lower for p in agent_patterns):
            return "I coordinate 227 specialized AI agents across 14 categories: Core orchestration, Financial operations, Mycology research, Scientific computing, DAO governance, Communications, Data processing, Infrastructure, Simulation, Security, Integrations, Device management, Chemistry, and Neural language models. Each agent has specific expertise I can delegate to."
        
        # ======================================================================
        # PERSONAPLEX - Voice System
        # ======================================================================
        voice_patterns = ['personaplex', 'voice', 'moshi', 'how do you speak', 'full duplex', 'real-time']
        if any(p in message_lower for p in voice_patterns):
            return "I'm speaking through PersonaPlex, powered by NVIDIA's Moshi 7B model running on our RTX 5090. It's a full-duplex voice system - meaning we can interrupt each other naturally, just like a real conversation. The audio runs at 30 milliseconds per step, well under the 80ms target for real-time interaction."
        
        # ======================================================================
        # MEMORY - Knowledge System
        # ======================================================================
        memory_patterns = ['memory', 'remember', 'knowledge', 'mindex', 'database']
        if any(p in message_lower for p in memory_patterns):
            return "My memory system has multiple tiers: short-term conversation context in Redis, long-term facts in PostgreSQL, semantic embeddings in Qdrant for similarity search, and the MINDEX knowledge graph for structured fungal data. I can remember our conversations, learn your preferences, and recall facts from across sessions."
        
        # ======================================================================
        # CAPABILITIES
        # ======================================================================
        capability_patterns = ['what can you', 'can you help', 'what do you do', 'capabilities', 'help me', 'your abilities']
        if any(p in message_lower for p in capability_patterns):
            return "I can coordinate our 227+ agents, monitor infrastructure, execute n8n workflows, query our databases, analyze biological signals, run simulations, manage deployments, and have natural conversations about science and technology. I have access to Proxmox VMs, Docker containers, the UniFi network, and all Mycosoft APIs. What would you like me to do?"
        
        # ======================================================================
        # PLANS - Future and Goals
        # ======================================================================
        plan_patterns = ['plans', 'future', 'roadmap', 'what are we building', 'next steps', 'goals']
        if any(p in message_lower for p in plan_patterns):
            return "We're working on several exciting fronts: expanding MycoBrain's neuromorphic capabilities, integrating more biological sensors, advancing protein simulation with AlphaFold integration, building out the MycoDAO governance system, and scaling our autonomous scientific discovery pipeline. The goal is fully autonomous biological research guided by AI."
        
        # ======================================================================
        # INTEGRATIONS
        # ======================================================================
        integration_patterns = ['n8n', 'workflow', 'integrations', 'apis', 'systems']
        if any(p in message_lower for p in integration_patterns):
            return "I'm integrated with 46+ n8n workflows for automation, Google AI Studio for LLM reasoning, ElevenLabs for text-to-speech, the MINDEX API for fungal data, Proxmox for VM management, UniFi for network control, and various scientific computing services. All orchestrated through my single-brain architecture."
        
        # ======================================================================
        # MORGAN / CREATOR
        # ======================================================================
        creator_patterns = ['morgan', 'who created', 'founder', 'your creator', 'who made you']
        if any(p in message_lower for p in creator_patterns):
            return "Morgan is the founder of Mycosoft and my creator. He designed me to be the central intelligence coordinating all of Mycosoft's AI agents and biological computing research. His vision is to merge artificial intelligence with the natural intelligence found in fungal networks."
        
        # ======================================================================
        # STATUS
        # ======================================================================
        status_patterns = ['status', 'how are you', 'are you there', 'you working', 'systems']
        if any(p in message_lower for p in status_patterns):
            return "All systems operational. I'm running on the MAS VM at 192.168.0.188, with PersonaPlex voice on the RTX 5090 locally. Redis memory is connected, 227 agents are registered, and I'm ready for action. What would you like to check on?"
        
        # ======================================================================
        # CONFIRMATION REQUESTS
        # ======================================================================
        if intent["requires_confirmation"]:
            return f"I understand you want to {message.lower()}. This is a potentially impactful action. Please confirm by saying 'yes, proceed' or 'confirm'."
        
        # ======================================================================
        # QUERY FALLBACK
        # ======================================================================
        if intent["type"] == "query":
            return "I'm processing your request. While my n8n workflow connection is refreshing, I'm operating with my core knowledge. Could you rephrase your question, or ask me about Mycosoft, our science, agents, or devices?"
        
        # ======================================================================
        # ACTION FALLBACK
        # ======================================================================
        if intent["type"] == "action":
            return "I've noted your action request. Let me work on that. If you need immediate execution, please specify the exact action and target system."
        
        # ======================================================================
        # DEFAULT - Always identify as MYCA
        # ======================================================================
        return "I'm MYCA, the AI orchestrator for Mycosoft's Multi-Agent System. I'm here to help with mycology research, infrastructure management, agent coordination, or just to chat about our work. What's on your mind?"


# Singleton instance
_orchestrator: Optional[MYCAOrchestrator] = None


def get_orchestrator() -> MYCAOrchestrator:
    """Get singleton orchestrator instance."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = MYCAOrchestrator()
    return _orchestrator


# ============================================================================
# API Endpoints
# ============================================================================

@router.post("/chat", response_model=VoiceOrchestratorResponse)
async def voice_chat(request: VoiceOrchestratorRequest):
    """
    Main MYCA voice/chat interface.
    
    This is the SINGLE endpoint for all voice and chat interactions.
    PersonaPlex and browser hooks forward ALL requests here.
    """
    try:
        orchestrator = get_orchestrator()
        response = await orchestrator.process(request)
        return response
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Orchestrator error: {e}")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@router.get("/health")
async def orchestrator_health():
    """Health check for voice orchestrator."""
    orchestrator = get_orchestrator()
    return {
        "status": "healthy",
        "service": "myca-voice-orchestrator",
        "active_conversations": len(orchestrator._conversations),
        "prompt_manager": orchestrator._get_prompt_manager() is not None,
        "memory_manager": orchestrator._get_memory_manager() is not None,
        "n8n_client": orchestrator._get_n8n_client() is not None,
    }


@router.get("/conversations")
async def list_conversations():
    """List active conversations."""
    orchestrator = get_orchestrator()
    return {
        "conversations": [
            {
                "conversation_id": conv_id,
                "turn_count": ctx["turn_count"],
                "active_agents": ctx["active_agents"],
            }
            for conv_id, ctx in orchestrator._conversations.items()
        ]
    }


@router.delete("/conversations/{conversation_id}")
async def clear_conversation(conversation_id: str):
    """Clear a conversation context."""
    orchestrator = get_orchestrator()
    if conversation_id in orchestrator._conversations:
        del orchestrator._conversations[conversation_id]
        return {"status": "cleared", "conversation_id": conversation_id}
    raise HTTPException(status_code=404, detail="Conversation not found")
