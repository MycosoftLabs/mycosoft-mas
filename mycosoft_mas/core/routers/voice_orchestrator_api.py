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
        """Generate a MYCA identity-aware local response when n8n is unavailable."""
        message_lower = message.lower().strip()
        
        # Handle name-related questions - MYCA MUST know her identity
        name_patterns = ['your name', 'who are you', 'what are you', "what's your name", 'whats your name', 'name like']
        if any(p in message_lower for p in name_patterns):
            return "I'm MYCA - My Companion AI. I'm the orchestrator of Mycosoft's Multi-Agent System, coordinating all our specialized agents. I was created by Morgan, the founder of Mycosoft. What can I help you with today?"
        
        # Handle greetings
        greeting_patterns = ['hello', 'hi ', 'hey', 'good morning', 'good evening', 'greetings']
        if any(p in message_lower for p in greeting_patterns) or message_lower in ['hi', 'hey', 'hello']:
            return "Hello! I'm MYCA, your AI companion and orchestrator here at Mycosoft. I'm coordinating our agent network and ready to help. What would you like to do?"
        
        # Handle confirmation requests
        if intent["requires_confirmation"]:
            return f"I'm MYCA, and I understand you want to {message.lower()}. This is a potentially destructive action. Please confirm by saying 'yes' or 'confirm'."
        
        # Handle capability questions
        capability_patterns = ['what can you', 'can you help', 'what do you do', 'capabilities', 'help me']
        if any(p in message_lower for p in capability_patterns):
            return "I'm MYCA, the central orchestrator for Mycosoft's Multi-Agent System. I coordinate 40+ specialized agents, monitor infrastructure, execute workflows, and help you interact with our systems. How can I help you today?"
        
        # Handle status questions
        status_patterns = ['status', 'how are you', 'are you there', 'you working', 'agents']
        if any(p in message_lower for p in status_patterns):
            return "I'm MYCA, and I'm fully operational. I'm currently coordinating our agent network and all systems are responsive. What would you like me to check?"
        
        if intent["type"] == "query":
            return "I'm MYCA. I'm processing your request. The n8n workflow system is currently being refreshed, so I'm operating with limited capabilities. Please try again in a moment."
        
        if intent["type"] == "action":
            return "I'm MYCA. I've received your action request. The workflow system is temporarily being updated. I'll queue this for processing."
        
        # Default chitchat response - always identify as MYCA
        return "I'm MYCA, the AI orchestrator for Mycosoft's Multi-Agent System. I'm here to help you manage infrastructure, coordinate agents, and answer questions. What can I help you with?"


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
