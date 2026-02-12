"""
MYCA Voice Orchestrator API - February 5, 2026

Single decision point for all voice/chat interactions.

UPDATED: Integrated with MemoryCoordinator for:
- Loading conversation history from PostgreSQL
- Persisting turns via supabase_client
- Cross-session context restoration
- Redis memory restoration if expired

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
# Request/Response Models
# ============================================================================

class VoiceOrchestratorRequest(BaseModel):
    """Standard request to the MYCA voice orchestrator."""
    message: str = Field(..., description="User message/transcript")
    conversation_id: Optional[str] = Field(None, description="Conversation ID for context")
    session_id: Optional[str] = Field(None, description="Voice session ID")
    user_id: Optional[str] = Field(None, description="User ID for cross-session memory")
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
    history_loaded_from_db: bool = False


class ToolCallInfo(BaseModel):
    """Tool call information for frontend debug panels."""
    tool: str = Field(..., description="Tool name")
    query: Optional[str] = Field(None, description="Query passed to tool")
    status: str = Field("success", description="Tool call status")
    result: Optional[str] = Field(None, description="Tool result")
    duration: Optional[int] = Field(None, description="Duration in ms")
    inject_to_moshi: bool = Field(False, description="Whether to inject result to Moshi")


class AgentInvocation(BaseModel):
    """Agent invocation information for frontend debug panels."""
    id: str = Field(..., description="Agent ID")
    name: str = Field(..., description="Agent name")
    action: str = Field(..., description="Action performed")
    status: str = Field("completed", description="Agent status")
    feedback: Optional[str] = Field(None, description="Agent feedback")
    inject_to_moshi: bool = Field(False, description="Whether to inject feedback to Moshi")


class MemoryStats(BaseModel):
    """Memory statistics for frontend debug panels."""
    reads: int = Field(0, description="Number of memory reads")
    writes: int = Field(0, description="Number of memory writes")
    context_injected: bool = Field(False, description="Whether context was injected")
    turns_in_session: int = Field(0, description="Number of turns in session")


class InjectionInfo(BaseModel):
    """Injection info for frontend feedback system."""
    type: str = Field(..., description="Injection type: tool_result, agent_update, system_alert")
    content: str = Field(..., description="Content to inject")


class VoiceOrchestratorResponse(BaseModel):
    """Structured response from the MYCA voice orchestrator."""
    response_text: str = Field(..., description="MYCA's response text")
    response: str = Field(..., description="Alias for response_text")
    actions_taken: List[ActionTaken] = Field(default_factory=list, description="Actions performed")
    session_context: Optional[SessionContext] = None
    source: str = Field("myca-orchestrator", description="Response source")
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    # Frontend debug panel fields
    tool_calls: List[ToolCallInfo] = Field(default_factory=list, description="Tool calls for debug panel")
    agents_invoked: List[AgentInvocation] = Field(default_factory=list, description="Agent invocations for debug panel")
    memory_stats: Optional[MemoryStats] = Field(None, description="Memory statistics for debug panel")
    injection: Optional[InjectionInfo] = Field(None, description="Feedback injection info")


# ============================================================================
# Orchestrator Logic with Memory Integration
# ============================================================================

class MYCAOrchestrator:
    """
    MYCA Orchestrator - The Single Brain with Memory Integration
    
    ALL cognitive decisions happen here:
    - Analyzing user intent
    - Deciding tool usage
    - Managing memory
    - Routing to agents
    - Executing workflows
    
    PHASE 2: Now loads conversation history from PostgreSQL
    on first message with existing conversation_id.
    """
    
    def __init__(self):
        self._prompt_manager = None
        self._memory_manager = None
        self._n8n_client = None
        self._session_manager = None
        self._voice_store = None
        self._memory_coordinator = None
        
        # Conversation context cache
        self._conversations: Dict[str, Dict[str, Any]] = {}
        
        # Track which conversations have been loaded from DB
        self._loaded_from_db: set = set()
    
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
    
    async def _get_voice_store(self):
        """Lazy load voice session store."""
        if self._voice_store is None:
            try:
                from mycosoft_mas.voice.supabase_client import get_voice_store
                self._voice_store = get_voice_store()
                await self._voice_store.connect()
            except Exception as e:
                logger.warning(f"VoiceStore not available: {e}")
        return self._voice_store
    
    async def _get_memory_coordinator(self):
        """Lazy load memory coordinator."""
        if self._memory_coordinator is None:
            try:
                from mycosoft_mas.memory import get_memory_coordinator
                self._memory_coordinator = await get_memory_coordinator()
            except Exception as e:
                logger.warning(f"MemoryCoordinator not available: {e}")
        return self._memory_coordinator
    
    async def _load_conversation_from_db(
        self,
        conversation_id: str,
        actions_taken: List[ActionTaken]
    ) -> bool:
        """
        Load conversation history from PostgreSQL.
        
        Called on first message with an existing conversation_id
        to restore context from previous sessions.
        """
        if conversation_id in self._loaded_from_db:
            return False  # Already loaded
        
        voice_store = await self._get_voice_store()
        if not voice_store:
            return False
        
        try:
            # Load history from database
            history = await voice_store.load_conversation_history(
                conversation_id=conversation_id,
                limit=50
            )
            
            if history:
                # Initialize conversation context if not exists
                if conversation_id not in self._conversations:
                    self._conversations[conversation_id] = {
                        "turn_count": 0,
                        "history": [],
                        "active_agents": [],
                    }
                
                # Populate history from DB
                for turn in history:
                    self._conversations[conversation_id]["history"].append({
                        "role": turn["role"],
                        "content": turn["content"],
                        "timestamp": turn["timestamp"],
                    })
                
                self._conversations[conversation_id]["turn_count"] = len(history)
                self._loaded_from_db.add(conversation_id)
                
                actions_taken.append(ActionTaken(
                    type="memory_restore",
                    detail={
                        "source": "postgresql",
                        "turns_loaded": len(history),
                        "conversation_id": conversation_id
                    }
                ))
                
                logger.info(f"Loaded {len(history)} turns from DB for conversation {conversation_id[:8]}...")
                return True
                
        except Exception as e:
            logger.error(f"Failed to load conversation from DB: {e}")
        
        return False
    
    async def _persist_turn(
        self,
        session_id: str,
        speaker: str,
        text: str
    ) -> None:
        """Persist a turn to the database via supabase_client."""
        voice_store = await self._get_voice_store()
        if voice_store:
            try:
                await voice_store.add_turn(
                    session_id=session_id,
                    speaker=speaker,
                    text=text
                )
            except Exception as e:
                logger.warning(f"Failed to persist turn: {e}")
    
    async def process(self, request: VoiceOrchestratorRequest) -> VoiceOrchestratorResponse:
        """
        Process a voice/chat request.
        
        This is the SINGLE decision point for all interactions.
        Now with memory integration for context restoration.
        """
        actions_taken: List[ActionTaken] = []
        history_loaded_from_db = False
        
        # Normalize input
        message = request.message.strip()
        if not message:
            raise ValueError("Empty message")
        
        # Ensure conversation context
        conv_id = request.conversation_id or str(uuid4())
        session_id = request.session_id or str(uuid4())
        user_id = request.user_id or "morgan"
        
        # PHASE 2: Load history from DB if this is a new conversation context
        # but we have an existing conversation_id (resuming conversation)
        if request.conversation_id and conv_id not in self._conversations:
            history_loaded_from_db = await self._load_conversation_from_db(
                conv_id,
                actions_taken
            )
        
        # Initialize context if not loaded from DB
        if conv_id not in self._conversations:
            self._conversations[conv_id] = {
                "turn_count": 0,
                "history": [],
                "active_agents": [],
            }
        
        conv_context = self._conversations[conv_id]
        conv_context["turn_count"] += 1
        
        # Load user profile if user_id provided
        if request.user_id:
            coordinator = await self._get_memory_coordinator()
            if coordinator:
                try:
                    profile = await coordinator.get_user_profile(request.user_id)
                    if profile.preferences:
                        actions_taken.append(ActionTaken(
                            type="user_profile_loaded",
                            detail={"user_id": request.user_id, "preference_count": len(profile.preferences)}
                        ))
                except Exception as e:
                    logger.warning(f"Failed to load user profile: {e}")
        
        # Store user message in memory coordinator
        coordinator = await self._get_memory_coordinator()
        if coordinator:
            try:
                await coordinator.add_conversation_turn(
                    session_id=conv_id,
                    role="user",
                    content=message,
                    metadata={"modality": request.modality, "source": request.source}
                )
                actions_taken.append(ActionTaken(
                    type="memory_write",
                    detail={"scope": "conversation", "role": "user"}
                ))
            except Exception as e:
                logger.warning(f"Failed to write to memory coordinator: {e}")
        
        # Add to local history
        conv_context["history"].append({
            "role": "user",
            "content": message,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        
        # Persist turn to database
        await self._persist_turn(session_id, "user", message)
        
        # Analyze intent and decide actions
        intent = self._analyze_intent(message)
        
        # Get response (from n8n workflow, memory brain, or local generation)
        response_text = await self._generate_response(
            message=message,
            conv_id=conv_id,
            session_id=session_id,
            user_id=user_id,
            intent=intent,
            actions_taken=actions_taken,
        )
        
        # Store assistant response in memory coordinator
        if coordinator:
            try:
                await coordinator.add_conversation_turn(
                    session_id=conv_id,
                    role="assistant",
                    content=response_text
                )
            except Exception as e:
                logger.warning(f"Failed to write response to memory: {e}")
        
        # Add to local history
        conv_context["history"].append({
            "role": "assistant",
            "content": response_text,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        
        # Persist assistant turn
        await self._persist_turn(session_id, "myca", response_text)
        
        # Keep history bounded
        if len(conv_context["history"]) > 40:
            conv_context["history"] = conv_context["history"][-40:]
        
        # Build response
        session_context = SessionContext(
            conversation_id=conv_id,
            turn_count=conv_context["turn_count"],
            active_agents=conv_context["active_agents"],
            memory_namespace=f"conversation:{conv_id}",
            history_loaded_from_db=history_loaded_from_db,
        )
        
        # Build debug panel data from actions_taken
        tool_calls: List[ToolCallInfo] = []
        agents_invoked: List[AgentInvocation] = []
        memory_reads = 0
        memory_writes = 0
        context_injected = False
        
        for action in actions_taken:
            if action.type == "tool_called":
                tool_calls.append(ToolCallInfo(
                    tool=action.detail.get("tool_name", "unknown"),
                    query=action.detail.get("query"),
                    status=action.detail.get("status", "success"),
                    result=action.detail.get("result"),
                    duration=action.detail.get("duration_ms"),
                    inject_to_moshi=action.detail.get("inject_to_moshi", False),
                ))
            elif action.type == "agent_routed":
                agents_invoked.append(AgentInvocation(
                    id=action.detail.get("agent_id", "unknown"),
                    name=action.detail.get("agent_name", "unknown"),
                    action=action.detail.get("action", "invoked"),
                    status=action.detail.get("status", "completed"),
                    feedback=action.detail.get("feedback"),
                    inject_to_moshi=action.detail.get("inject_to_moshi", False),
                ))
            elif action.type == "memory_write":
                memory_writes += 1
            elif action.type in ("memory_restore", "memory_read", "user_profile_loaded"):
                memory_reads += 1
                if action.type == "memory_restore":
                    context_injected = True
        
        memory_stats = MemoryStats(
            reads=memory_reads,
            writes=memory_writes,
            context_injected=context_injected,
            turns_in_session=conv_context["turn_count"],
        )
        
        return VoiceOrchestratorResponse(
            response_text=response_text,
            response=response_text,
            actions_taken=actions_taken,
            session_context=session_context,
            tool_calls=tool_calls,
            agents_invoked=agents_invoked,
            memory_stats=memory_stats,
        )
    
    def _analyze_intent(self, message: str) -> Dict[str, Any]:
        """Analyze user intent."""
        message_lower = message.lower()
        
        action_keywords = ["start", "stop", "restart", "deploy", "rebuild", "delete", "remove", "shutdown"]
        query_keywords = ["status", "health", "check", "list", "show", "what", "how", "why"]
        dangerous_keywords = ["delete", "remove", "shutdown", "purge", "reset", "clear"]
        
        is_action = any(kw in message_lower for kw in action_keywords)
        is_query = any(kw in message_lower for kw in query_keywords)
        is_dangerous = any(kw in message_lower for kw in dangerous_keywords)
        
        return {
            "type": "action" if is_action else "query" if is_query else "conversation",
            "is_action": is_action,
            "is_query": is_query,
            "requires_confirmation": is_dangerous,
            "keywords": [kw for kw in action_keywords + query_keywords if kw in message_lower],
        }
    
    async def _generate_response(
        self,
        message: str,
        conv_id: str,
        session_id: str,
        user_id: str,
        intent: Dict[str, Any],
        actions_taken: List[ActionTaken]
    ) -> str:
        """Generate a response using available services with memory integration."""
        
        # Try n8n workflow first
        n8n = self._get_n8n_client()
        if n8n:
            try:
                conv_context = self._conversations.get(conv_id, {})
                history = conv_context.get("history", [])[-10:]
                
                result = await n8n.execute_workflow_async(
                    workflow_id="myca-brain-v2",
                    payload={
                        "message": message,
                        "conversation_id": conv_id,
                        "history": history,
                        "source": "voice-orchestrator",
                    }
                )
                
                if result and isinstance(result, dict) and result.get("response"):
                    actions_taken.append(ActionTaken(
                        type="workflow_executed",
                        detail={"workflow_id": "myca-brain-v2", "success": True}
                    ))
                    return result["response"]
                    
            except Exception as e:
                logger.warning(f"n8n workflow failed: {e}")
        
        # Try memory-integrated brain as second fallback
        try:
            from mycosoft_mas.llm.memory_brain import get_memory_brain
            brain = await get_memory_brain()
            
            conv_context = self._conversations.get(conv_id, {})
            history = conv_context.get("history", [])[-10:]
            
            # Convert history to role/content format
            formatted_history = [
                {"role": turn.get("role", "user"), "content": turn.get("content", "")}
                for turn in history
            ]
            
            response = await brain.get_response(
                message=message,
                session_id=session_id,
                conversation_id=conv_id,
                user_id=user_id,
                history=formatted_history,
                provider="auto"
            )
            
            if response and len(response) > 10:
                actions_taken.append(ActionTaken(
                    type="memory_brain_response",
                    detail={"provider": "auto", "memory_integrated": True}
                ))
                return response
                
        except Exception as e:
            logger.warning(f"Memory brain failed: {e}")
        
        # Final fallback to local responses
        return self._get_local_response(message, intent)
    
    def _get_local_response(self, message: str, intent: Dict[str, Any]) -> str:
        """Generate local response based on intent."""
        message_lower = message.lower()
        
        # Identity questions
        identity_patterns = ['who are you', 'your name', "what's your name", 'what are you', 'introduce yourself', 'tell me about yourself']
        if any(p in message_lower for p in identity_patterns):
            return "I'm MYCA, the Multi-Agent System Coordinator for Mycosoft. I was created by Morgan to orchestrate our AI agents and biological computing research. I'm speaking through PersonaPlex on our RTX 5090."
        
        # Creator questions
        creator_patterns = ['morgan', 'who created', 'founder', 'your creator', 'who made you']
        if any(p in message_lower for p in creator_patterns):
            return "Morgan is the founder of Mycosoft and my creator. His vision is to merge AI with the natural intelligence found in fungal networks."
        
        # Agents
        agent_patterns = ['agents', 'how many agents', 'agent system']
        if any(p in message_lower for p in agent_patterns):
            return "I coordinate 227 specialized AI agents across 14 categories including Core orchestration, Financial operations, Mycology research, and Scientific computing."
        
        # Voice system
        voice_patterns = ['personaplex', 'voice', 'moshi', 'how do you speak']
        if any(p in message_lower for p in voice_patterns):
            return "I'm speaking through PersonaPlex, powered by NVIDIA's Moshi 7B model running on our RTX 5090. It's a full-duplex voice system for natural conversation."
        
        # Memory
        memory_patterns = ['memory', 'remember', 'knowledge']
        if any(p in message_lower for p in memory_patterns):
            return "My memory system has multiple tiers: short-term in Redis, long-term in PostgreSQL, semantic embeddings in Qdrant, and the MINDEX knowledge graph. I can remember our conversations across sessions."
        
        # Capabilities
        capability_patterns = ['what can you', 'can you help', 'capabilities']
        if any(p in message_lower for p in capability_patterns):
            return "I can coordinate our 227+ agents, monitor infrastructure, execute n8n workflows, query databases, analyze biological signals, run simulations, and manage deployments. What would you like me to do?"
        
        # Status
        status_patterns = ['status', 'how are you', 'are you there']
        if any(p in message_lower for p in status_patterns):
            return "All systems operational. I'm running on the MAS VM at 192.168.0.188 with PersonaPlex voice. Ready for action."
        
        # Confirmation needed
        if intent["requires_confirmation"]:
            return f"I understand you want to {message.lower()}. This is a potentially impactful action. Please confirm by saying 'yes, proceed'."
        
        # Default
        return "I'm MYCA, the AI orchestrator for Mycosoft. I'm here to help with mycology research, infrastructure management, agent coordination, or just to chat. What's on your mind?"


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
    """Main MYCA voice/chat interface."""
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
        "version": "2.0.0-memory-integration",
        "active_conversations": len(orchestrator._conversations),
        "loaded_from_db": len(orchestrator._loaded_from_db),
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
                "loaded_from_db": conv_id in orchestrator._loaded_from_db,
            }
            for conv_id, ctx in orchestrator._conversations.items()
        ]
    }


@router.get("/conversation/{conversation_id}/history")
async def get_conversation_history(conversation_id: str, limit: int = 50):
    """Get conversation history from database."""
    try:
        from mycosoft_mas.voice.supabase_client import get_voice_store
        store = get_voice_store()
        await store.connect()
        history = await store.load_conversation_history(conversation_id, limit)
        return {"conversation_id": conversation_id, "history": history, "count": len(history)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/conversations/{conversation_id}")
async def clear_conversation(conversation_id: str):
    """Clear a conversation context."""
    orchestrator = get_orchestrator()
    if conversation_id in orchestrator._conversations:
        del orchestrator._conversations[conversation_id]
        orchestrator._loaded_from_db.discard(conversation_id)
        return {"status": "cleared", "conversation_id": conversation_id}
    raise HTTPException(status_code=404, detail="Conversation not found")



