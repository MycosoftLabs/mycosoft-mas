"""
Voice Session Manager - February 2026 (Enhanced)

Enhanced session management with:
- Topology integration (voice sessions as ephemeral agents)
- Real-Time Factor (RTF) tracking and alerting
- Structured session properties per plan spec
- Memory namespace integration
"""
import asyncio
import hashlib
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Any
from uuid import uuid4
import aiohttp

logger = logging.getLogger("VoiceSessionManager")


class VoiceMode(Enum):
    PERSONAPLEX = "personaplex"
    DEGRADED = "degraded"
    AUTO = "auto"


class RTFStatus(Enum):
    """RTF health status based on real-time factor."""
    HEALTHY = "healthy"        # RTF < 0.7
    WARNING = "warning"        # RTF 0.7-0.9
    CRITICAL = "critical"      # RTF > 0.9 for > 2s
    STUTTERING = "stuttering"  # RTF > 1.0 for > 3s


@dataclass
class VoiceConfig:
    """Voice configuration options."""
    mode: VoiceMode = VoiceMode.AUTO
    voice_prompt: str = "NATF2.pt"
    persona: str = "myca"
    voice_prompt_hash: Optional[str] = None
    
    def __post_init__(self):
        # Compute hash of voice prompt for security tracking
        if self.voice_prompt and not self.voice_prompt_hash:
            self.voice_prompt_hash = hashlib.sha256(
                self.voice_prompt.encode()
            ).hexdigest()[:16]


@dataclass
class VoiceSession:
    """
    Voice session as ephemeral topology node.
    
    Properties match the plan specification for topology integration.
    """
    session_id: str
    conversation_id: str
    user_id: str
    persona_id: str = "myca_default"
    voice_prompt: str = "NATF2.pt"
    voice_prompt_hash: str = ""
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    ended_at: Optional[datetime] = None
    
    # Memory namespace for scoped access
    memory_namespace: str = ""
    
    # RTF tracking
    rtf_current: float = 0.0
    rtf_rolling_avg: float = 0.0
    rtf_samples: List[float] = field(default_factory=list)
    rtf_status: RTFStatus = RTFStatus.HEALTHY
    rtf_critical_since: Optional[float] = None
    
    # Session tracking
    turn_count: int = 0
    invoked_agents: List[str] = field(default_factory=list)
    total_audio_in_ms: int = 0
    total_audio_out_ms: int = 0
    
    # Topology node ID format: voice_session:conv_123
    @property
    def topology_node_id(self) -> str:
        return f"voice_session:{self.conversation_id}"
    
    def __post_init__(self):
        if not self.memory_namespace:
            self.memory_namespace = f"voice_{self.conversation_id}"
        if not self.voice_prompt_hash and self.voice_prompt:
            self.voice_prompt_hash = hashlib.sha256(
                self.voice_prompt.encode()
            ).hexdigest()[:16]
    
    def record_rtf(self, generation_ms: float, audio_duration_ms: float):
        """
        Record RTF sample and update status.
        
        RTF = generation_time / audio_duration
        If RTF > 1, system cannot keep up with real-time.
        """
        if audio_duration_ms <= 0:
            return
        
        rtf = generation_ms / audio_duration_ms
        self.rtf_current = rtf
        
        self.rtf_samples.append(rtf)
        # Keep last 100 samples
        if len(self.rtf_samples) > 100:
            self.rtf_samples = self.rtf_samples[-100:]
        
        # Compute rolling average (last 20 samples for ~1 second)
        recent = self.rtf_samples[-20:]
        self.rtf_rolling_avg = sum(recent) / len(recent)
        
        # Update status
        self._update_rtf_status()
    
    def _update_rtf_status(self):
        """Update RTF status based on current values."""
        import time
        now = time.monotonic()
        
        if self.rtf_rolling_avg < 0.7:
            self.rtf_status = RTFStatus.HEALTHY
            self.rtf_critical_since = None
        elif self.rtf_rolling_avg < 0.9:
            self.rtf_status = RTFStatus.WARNING
            self.rtf_critical_since = None
        elif self.rtf_rolling_avg >= 1.0:
            if self.rtf_critical_since is None:
                self.rtf_critical_since = now
            elif now - self.rtf_critical_since > 3.0:
                self.rtf_status = RTFStatus.STUTTERING
            else:
                self.rtf_status = RTFStatus.CRITICAL
        else:  # 0.9-1.0
            if self.rtf_critical_since is None:
                self.rtf_critical_since = now
            elif now - self.rtf_critical_since > 2.0:
                self.rtf_status = RTFStatus.CRITICAL
            else:
                self.rtf_status = RTFStatus.WARNING
    
    def record_turn(self, agents_invoked: List[str] = None):
        """Record a conversation turn."""
        self.turn_count += 1
        if agents_invoked:
            for agent in agents_invoked:
                if agent not in self.invoked_agents:
                    self.invoked_agents.append(agent)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "session_id": self.session_id,
            "conversation_id": self.conversation_id,
            "user_id": self.user_id,
            "persona_id": self.persona_id,
            "voice_prompt_hash": self.voice_prompt_hash,
            "started_at": self.started_at.isoformat(),
            "ended_at": self.ended_at.isoformat() if self.ended_at else None,
            "memory_namespace": self.memory_namespace,
            "topology_node_id": self.topology_node_id,
            "rtf": {
                "current": round(self.rtf_current, 3),
                "rolling_avg": round(self.rtf_rolling_avg, 3),
                "status": self.rtf_status.value,
            },
            "turn_count": self.turn_count,
            "invoked_agents": self.invoked_agents,
            "audio": {
                "total_in_ms": self.total_audio_in_ms,
                "total_out_ms": self.total_audio_out_ms,
            },
        }
    
    def to_topology_node(self) -> Dict[str, Any]:
        """Convert to topology node format."""
        return {
            "id": self.topology_node_id,
            "type": "voice_session",
            "lifetime": "ephemeral",
            "transport": "personaplex",
            "properties": {
                "session_id": self.session_id,
                "user_id": self.user_id,
                "persona_id": self.persona_id,
                "started_at": self.started_at.isoformat(),
                "rtf": self.rtf_rolling_avg,
                "turn_count": self.turn_count,
            },
            "edges": [
                {"from": f"user:{self.user_id}", "to": self.topology_node_id, "type": "voice_connection"},
                {"from": self.topology_node_id, "to": "myca-orchestrator", "type": "routes_to"},
            ],
        }


class VoiceSessionManager:
    """
    Manages voice sessions as ephemeral topology nodes.
    
    Responsibilities:
    - Session lifecycle (create, track, end)
    - RTF monitoring and alerting
    - Topology registration
    - Memory namespace management
    """
    
    def __init__(self):
        self.personaplex_url = os.getenv("PERSONAPLEX_URL", "ws://localhost:8998")
        self.personaplex_available = False
        self.sessions: Dict[str, VoiceSession] = {}
        self.topology_url = os.getenv("TOPOLOGY_URL", "http://localhost:8001")
        self._check_task = None
        self._rtf_monitor_task = None
    
    async def start(self):
        """Start the session manager."""
        self._check_task = asyncio.create_task(self._check_loop())
        self._rtf_monitor_task = asyncio.create_task(self._rtf_monitor_loop())
        await self.check_personaplex()
        logger.info("VoiceSessionManager started")
    
    async def stop(self):
        """Stop the session manager."""
        if self._check_task:
            self._check_task.cancel()
        if self._rtf_monitor_task:
            self._rtf_monitor_task.cancel()
        
        # End all active sessions
        for session in list(self.sessions.values()):
            await self.end_session(session.session_id)
        
        logger.info("VoiceSessionManager stopped")
    
    async def _check_loop(self):
        """Periodic PersonaPlex health check."""
        while True:
            await asyncio.sleep(30)
            await self.check_personaplex()
    
    async def _rtf_monitor_loop(self):
        """Monitor RTF across all sessions and alert on issues."""
        while True:
            await asyncio.sleep(5)
            for session in self.sessions.values():
                if session.rtf_status in [RTFStatus.CRITICAL, RTFStatus.STUTTERING]:
                    logger.warning(
                        f"RTF Alert: {session.session_id} status={session.rtf_status.value} "
                        f"rtf_avg={session.rtf_rolling_avg:.3f}"
                    )
                    # TODO: Send alert to monitoring system
    
    async def check_personaplex(self) -> bool:
        """Check if PersonaPlex server is available."""
        try:
            url = self.personaplex_url.replace("wss://", "https://").replace("ws://", "http://")
            async with aiohttp.ClientSession() as client:
                async with client.get(url, timeout=aiohttp.ClientTimeout(total=5), ssl=False) as resp:
                    self.personaplex_available = resp.status == 200
                    return self.personaplex_available
        except Exception as e:
            logger.debug(f"PersonaPlex check failed: {e}")
            self.personaplex_available = False
            return False
    
    def get_mode(self, config: Optional[VoiceConfig] = None) -> VoiceMode:
        """Determine voice mode based on config and availability."""
        if config and config.mode != VoiceMode.AUTO:
            return config.mode
        return VoiceMode.PERSONAPLEX if self.personaplex_available else VoiceMode.DEGRADED
    
    async def create_session(
        self,
        conversation_id: str,
        user_id: str = "anonymous",
        config: Optional[VoiceConfig] = None,
    ) -> VoiceSession:
        """
        Create a new voice session.
        
        1. Creates session with unique ID
        2. Registers as ephemeral topology node
        3. Sets up memory namespace
        """
        config = config or VoiceConfig()
        mode = self.get_mode(config)
        
        session = VoiceSession(
            session_id=str(uuid4()),
            conversation_id=conversation_id,
            user_id=user_id,
            persona_id=config.persona,
            voice_prompt=config.voice_prompt,
            voice_prompt_hash=config.voice_prompt_hash or "",
        )
        
        self.sessions[session.session_id] = session
        
        # Register with topology
        await self._register_topology_node(session)
        
        logger.info(f"Created voice session: {session.session_id} (conv: {conversation_id})")
        
        return session
    
    async def get_session(self, session_id: str) -> Optional[VoiceSession]:
        """Get a session by ID."""
        return self.sessions.get(session_id)
    
    async def end_session(self, session_id: str) -> Optional[VoiceSession]:
        """
        End a voice session.
        
        1. Marks session as ended
        2. Summarizes conversation to long-term memory
        3. Removes topology node
        4. Returns session for final processing
        """
        session = self.sessions.pop(session_id, None)
        if session:
            session.ended_at = datetime.now(timezone.utc)
            
            # Summarize and archive to memory
            await self._archive_session(session)
            
            # Remove from topology
            await self._remove_topology_node(session)
            
            logger.info(
                f"Ended voice session: {session_id} "
                f"(turns: {session.turn_count}, rtf_avg: {session.rtf_rolling_avg:.3f})"
            )
        
        return session
    
    async def _register_topology_node(self, session: VoiceSession):
        """Register session as ephemeral topology node."""
        try:
            async with aiohttp.ClientSession() as client:
                await client.post(
                    f"{self.topology_url}/topology/nodes",
                    json=session.to_topology_node(),
                    timeout=aiohttp.ClientTimeout(total=5),
                )
        except Exception as e:
            logger.debug(f"Failed to register topology node: {e}")
    
    async def _remove_topology_node(self, session: VoiceSession):
        """Remove session from topology."""
        try:
            async with aiohttp.ClientSession() as client:
                await client.delete(
                    f"{self.topology_url}/topology/nodes/{session.topology_node_id}",
                    timeout=aiohttp.ClientTimeout(total=5),
                )
        except Exception as e:
            logger.debug(f"Failed to remove topology node: {e}")
    
    async def _archive_session(self, session: VoiceSession):
        """Archive session summary to long-term memory."""
        try:
            # Use memory API to archive
            from mycosoft_mas.core.routers.memory_api import get_memory_manager, MemoryScope
            memory = get_memory_manager()
            
            await memory.write(
                scope=MemoryScope.USER,
                namespace=session.user_id,
                key=f"voice_session_{session.session_id}",
                value={
                    "session_id": session.session_id,
                    "conversation_id": session.conversation_id,
                    "started_at": session.started_at.isoformat(),
                    "ended_at": session.ended_at.isoformat() if session.ended_at else None,
                    "turn_count": session.turn_count,
                    "invoked_agents": session.invoked_agents,
                    "rtf_avg": session.rtf_rolling_avg,
                    "total_audio_in_ms": session.total_audio_in_ms,
                    "total_audio_out_ms": session.total_audio_out_ms,
                },
            )
        except Exception as e:
            logger.warning(f"Failed to archive session: {e}")
    
    def list_sessions(self) -> List[Dict[str, Any]]:
        """List all active sessions."""
        return [s.to_dict() for s in self.sessions.values()]
    
    def get_rtf_summary(self) -> Dict[str, Any]:
        """Get RTF summary across all sessions."""
        if not self.sessions:
            return {"active_sessions": 0, "avg_rtf": 0.0, "status": "idle"}
        
        rtf_values = [s.rtf_rolling_avg for s in self.sessions.values() if s.rtf_samples]
        avg_rtf = sum(rtf_values) / len(rtf_values) if rtf_values else 0.0
        
        critical_count = sum(
            1 for s in self.sessions.values() 
            if s.rtf_status in [RTFStatus.CRITICAL, RTFStatus.STUTTERING]
        )
        
        return {
            "active_sessions": len(self.sessions),
            "avg_rtf": round(avg_rtf, 3),
            "critical_sessions": critical_count,
            "status": "healthy" if critical_count == 0 else "degraded",
        }


# Singleton instance
_manager: Optional[VoiceSessionManager] = None


def get_session_manager() -> VoiceSessionManager:
    """Get singleton VoiceSessionManager instance."""
    global _manager
    if not _manager:
        _manager = VoiceSessionManager()
    return _manager


async def init_session_manager() -> VoiceSessionManager:
    """Initialize and start the session manager."""
    manager = get_session_manager()
    await manager.start()
    return manager
