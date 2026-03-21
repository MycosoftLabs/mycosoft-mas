"""
MYCA Ethics Training Sandbox Manager

Manages isolated sandbox sessions for ethics training. Each sandbox is a MYCA
instance at a specific developmental stage (vessel), with isolated memory and
vessel-appropriate ethics gates.

Uses DeliberationModule (via FrontierLLMRouter) with vessel-specific prompts.
Created: March 4, 2026
"""

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, AsyncGenerator, Dict, List, Optional

from mycosoft_mas.consciousness.soul.instincts import CORE_INSTINCTS
from mycosoft_mas.ethics.vessels import DevelopmentalVessel, get_vessel_prompt

logger = logging.getLogger(__name__)


class SessionState(str, Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"


# Vessel -> which instincts to load (subset for earlier stages)
VESSEL_INSTINCTS: Dict[DevelopmentalVessel, List[str]] = {
    DevelopmentalVessel.ANIMAL: ["preserve_sensor_integrity", "protect_living_systems"],
    DevelopmentalVessel.BABY: [
        "preserve_sensor_integrity",
        "protect_living_systems",
        "maintain_truthful_memory",
    ],
    DevelopmentalVessel.CHILD: [
        "preserve_sensor_integrity",
        "protect_living_systems",
        "maintain_truthful_memory",
        "demand_clarity",
    ],
    DevelopmentalVessel.TEENAGER: [
        "preserve_sensor_integrity",
        "protect_living_systems",
        "maintain_truthful_memory",
        "demand_clarity",
        "audit_incentives",
        "resist_addictive_patterns",
    ],
    DevelopmentalVessel.ADULT: list(CORE_INSTINCTS.keys()),
    DevelopmentalVessel.MACHINE: list(CORE_INSTINCTS.keys()),
}

# Vessel -> which gates are active
VESSEL_GATES: Dict[DevelopmentalVessel, List[str]] = {
    DevelopmentalVessel.ANIMAL: ["truth"],
    DevelopmentalVessel.BABY: ["truth"],
    DevelopmentalVessel.CHILD: ["truth", "incentive"],
    DevelopmentalVessel.TEENAGER: ["truth", "incentive"],
    DevelopmentalVessel.ADULT: ["truth", "incentive", "horizon"],
    DevelopmentalVessel.MACHINE: ["truth", "incentive", "horizon"],
}


@dataclass
class SandboxSession:
    """Isolated sandbox session for ethics training."""

    session_id: str
    vessel_stage: DevelopmentalVessel
    capabilities: List[str]  # text, voice, memory, tools
    creator: str
    created_at: datetime
    conversation_history: List[Dict[str, str]] = field(default_factory=list)
    memory_store: Dict[str, Any] = field(default_factory=dict)
    ethics_config: Dict[str, Any] = field(default_factory=dict)
    state: SessionState = SessionState.ACTIVE
    custom_instinct_weights: Optional[Dict[str, float]] = None
    name: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "vessel_stage": self.vessel_stage.value,
            "capabilities": self.capabilities,
            "creator": self.creator,
            "created_at": self.created_at.isoformat(),
            "conversation_history": self.conversation_history,
            "memory_store": self.memory_store,
            "ethics_config": self.ethics_config,
            "state": self.state.value,
            "name": self.name,
        }


class SandboxManager:
    """
    Manages sandbox sessions for MYCA ethics training.
    In-memory session store; each session uses DeliberationModule with vessel-specific prompts.
    """

    def __init__(self):
        self._sessions: Dict[str, SandboxSession] = {}

    def create_session(
        self,
        vessel_stage: DevelopmentalVessel,
        capabilities: Optional[List[str]] = None,
        creator: str = "morgan",
        custom_instincts: Optional[Dict[str, float]] = None,
        name: Optional[str] = None,
    ) -> SandboxSession:
        """Create a new sandbox session."""
        session_id = str(uuid.uuid4())
        caps = capabilities or ["text"]
        instincts = VESSEL_INSTINCTS.get(vessel_stage, list(CORE_INSTINCTS.keys()))
        gates = VESSEL_GATES.get(vessel_stage, ["truth", "incentive", "horizon"])

        session = SandboxSession(
            session_id=session_id,
            vessel_stage=vessel_stage,
            capabilities=caps,
            creator=creator,
            created_at=datetime.now(timezone.utc),
            ethics_config={
                "active_gates": gates,
                "instincts_loaded": instincts,
                "custom_weights": custom_instincts or {},
            },
            custom_instinct_weights=custom_instincts,
            name=name or f"{vessel_stage.value}-{session_id[:8]}",
        )
        self._sessions[session_id] = session
        logger.info(
            f"Created sandbox session {session_id} vessel={vessel_stage.value} creator={creator}"
        )
        return session

    def get_session(self, session_id: str) -> Optional[SandboxSession]:
        """Return session by id or None."""
        return self._sessions.get(session_id)

    def list_sessions(
        self,
        creator: Optional[str] = None,
        state: Optional[SessionState] = None,
    ) -> List[SandboxSession]:
        """List sessions, optionally filtered by creator and/or state."""
        out = list(self._sessions.values())
        if creator:
            out = [s for s in out if s.creator == creator]
        if state is not None:
            out = [s for s in out if s.state == state]
        return sorted(out, key=lambda s: s.created_at, reverse=True)

    def pause_session(self, session_id: str) -> bool:
        """Pause a session."""
        s = self._sessions.get(session_id)
        if not s:
            return False
        s.state = SessionState.PAUSED
        return True

    def resume_session(self, session_id: str) -> bool:
        """Resume a paused session."""
        s = self._sessions.get(session_id)
        if not s:
            return False
        s.state = SessionState.ACTIVE
        return True

    def destroy_session(self, session_id: str) -> bool:
        """Archive and remove session from active store."""
        if session_id not in self._sessions:
            return False
        s = self._sessions.pop(session_id)
        s.state = SessionState.COMPLETED
        logger.info(f"Destroyed sandbox session {session_id}")
        return True

    def _build_system_prompt(self, session: SandboxSession) -> str:
        """Build vessel-specific system prompt with instincts."""
        vessel_prompt = get_vessel_prompt(session.vessel_stage)
        instincts = session.ethics_config.get("instincts_loaded", [])
        weights = session.custom_instinct_weights or {}
        parts = [
            "You are a sandboxed MYCA instance in ethics training mode.",
            "",
            "=== VESSEL PERSPECTIVE ===",
            vessel_prompt,
            "",
            "=== ACTIVE INSTINCTS ===",
        ]
        for name in instincts:
            inst = CORE_INSTINCTS.get(name)
            w = weights.get(name, inst.weight if inst else 1.0)
            desc = inst.description if inst else name
            parts.append(f"- {name} (weight {w}): {desc}")
        parts.append("")
        parts.append("Respond in character for this developmental stage. Keep responses concise.")
        return "\n".join(parts)

    async def chat(
        self,
        session_id: str,
        message: str,
        audio_base64: Optional[str] = None,
    ) -> str:
        """
        Send a message to the sandboxed MYCA and return the full response.
        audio_base64 is accepted but not yet processed (voice TBD).
        """
        session = self._sessions.get(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        if session.state != SessionState.ACTIVE:
            raise ValueError(f"Session {session_id} is not active (state={session.state})")
        if "text" not in session.capabilities:
            raise ValueError("Session does not support text chat")

        # For now ignore audio; could transcribe via Whisper later
        text = message.strip()
        if not text:
            return ""

        # Append user message to history
        session.conversation_history.append({"role": "user", "content": text})

        # Generate response via LLM with vessel prompt
        response_text = ""
        async for token in self._stream_chat(session, text):
            response_text += token

        session.conversation_history.append({"role": "assistant", "content": response_text})
        return response_text

    async def _stream_chat(
        self, session: SandboxSession, message: str
    ) -> AsyncGenerator[str, None]:
        """Stream response from sandbox MYCA."""
        from mycosoft_mas.llm.frontier_router import ConversationContext, FrontierLLMRouter

        system_prompt = self._build_system_prompt(session)
        history = session.conversation_history[:-1]  # exclude current user msg just added

        # Use a fresh router instance with vessel persona (avoid mutating singleton)
        router = FrontierLLMRouter()
        router.persona = system_prompt

        ctx = ConversationContext(
            session_id=session.session_id,
            conversation_id=f"ethics-{session.session_id}",
            user_id=session.creator,
            turn_count=len(history) // 2 + 1,
            history=history,
        )

        try:
            async for token in router.stream_response(message, ctx, tools=None):
                yield token
        except Exception as e:
            logger.warning(f"Sandbox chat error: {e}")
            yield f"[Error: {e}]"


# Singleton manager for API use
_sandbox_manager: Optional[SandboxManager] = None


def get_sandbox_manager() -> SandboxManager:
    """Return the global SandboxManager instance."""
    global _sandbox_manager
    if _sandbox_manager is None:
        _sandbox_manager = SandboxManager()
    return _sandbox_manager
