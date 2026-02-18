"""
Duplex Session - Runtime session object for full-duplex voice conversations.

Created: February 12, 2026

The DuplexSession holds all conversation components in one place:
- ConversationController (speech acts, barge-in)
- SpeechPlanner
- TaskRegistry (Phase 2)
- EventBus (Phase 5)

This prevents scattered globals and makes cancellation/barge-in clean.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, AsyncGenerator, Awaitable, Callable, Dict, List, Literal, Optional
from uuid import uuid4

from .conversation_control import (
    ConversationController,
    ConversationState,
    InterruptedDraft,
    VoiceActivityDetector,
)
from .cancellation import CancellationToken, TaskHandle, TaskRegistry
from .event_bus import AttentionEvent, AttentionEventBus
from .scheduler import DeadlineScheduler, SchedulerPriority
from .speech_planner import SpeechAct, SpeechActType, SpeechPlanner

logger = logging.getLogger(__name__)


ToolProgressState = Literal["starting", "working", "completed", "cancelled", "error"]


@dataclass
class ToolProgress:
    """
    Streaming status update for a tool/agent task.

    Phase 3 (minimal): this is converted into short status speech acts so the
    user hears progress while work continues in the background.
    """

    state: ToolProgressState
    tool_name: str
    message: Optional[str] = None
    result: Optional[Any] = None
    error: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class DuplexSessionConfig:
    """Configuration for a duplex session."""
    
    # Session identification
    session_id: str = field(default_factory=lambda: str(uuid4()))
    conversation_id: Optional[str] = None
    user_id: Optional[str] = None
    
    # VAD settings
    vad_energy_threshold: float = 0.02
    vad_min_speech_frames: int = 3
    
    # Speech settings
    target_speech_chars: int = 80
    min_speech_chars: int = 40
    
    # Barge-in settings
    barge_in_cooldown_ms: int = 500  # Minimum time between barge-ins


class DuplexSession:
    """
    Runtime session for full-duplex voice conversation.
    
    This is the central object that bridges the PersonaPlex/Moshi voice pipeline
    with the MYCA consciousness system. It holds:
    
    - ConversationController: manages turn-taking and barge-in
    - SpeechPlanner: converts LLM tokens into speech acts
    - TTS callbacks: for sending audio to Moshi
    - Cancellation state: for stopping everything on interrupt
    
    Usage in PersonaPlex bridge:
    
        session = DuplexSession(config)
        session.set_tts_callback(send_to_moshi)
        session.set_stop_tts_callback(stop_moshi_tts)
        
        # When generating response:
        async for act in session.speak(token_stream):
            # act is sent to TTS via callback
            pass
        
        # When audio comes in:
        session.on_audio(chunk)  # Triggers barge-in if speech detected
    """
    
    def __init__(
        self,
        config: Optional[DuplexSessionConfig] = None,
        on_barge_in: Optional[Callable[[], None]] = None,
        on_state_change: Optional[Callable[[ConversationState], None]] = None,
    ):
        """
        Initialize duplex session.
        
        Args:
            config: Session configuration
            on_barge_in: External callback when barge-in occurs
            on_state_change: External callback when state changes
        """
        self.config = config or DuplexSessionConfig()
        self._external_barge_in = on_barge_in
        self._external_state_change = on_state_change
        
        # Initialize components
        self.speech_planner = SpeechPlanner(
            target_chars=self.config.target_speech_chars,
            min_chars=self.config.min_speech_chars,
        )
        
        self.vad = VoiceActivityDetector(
            energy_threshold=self.config.vad_energy_threshold,
            min_speech_frames=self.config.vad_min_speech_frames,
        )
        
        self.conversation_controller = ConversationController(
            speech_planner=self.speech_planner,
            vad=self.vad,
            on_barge_in=self._handle_barge_in,
            on_state_change=self._handle_state_change,
        )
        
        # TTS callbacks (set by bridge)
        self._tts_callback: Optional[Callable[[SpeechAct], Any]] = None
        self._stop_tts_callback: Optional[Callable[[], Any]] = None
        self.task_registry = TaskRegistry()
        self.event_bus = AttentionEventBus(max_size=200)
        self.scheduler = DeadlineScheduler(max_workers=4)
        
        # State
        self._is_tts_playing = False
        self._last_barge_in: Optional[datetime] = None
        self._created_at = datetime.now()
        
        # Metrics
        self._total_speech_acts = 0
        self._total_barge_ins = 0
        
        logger.info(f"DuplexSession created: {self.config.session_id[:8]}")
    
    @property
    def session_id(self) -> str:
        return self.config.session_id
    
    @property
    def conversation_id(self) -> str:
        return self.config.conversation_id or self.config.session_id
    
    @property
    def is_speaking(self) -> bool:
        return self.conversation_controller.is_speaking
    
    @property
    def is_tts_playing(self) -> bool:
        return self._is_tts_playing
    
    @property
    def state(self) -> ConversationState:
        return self.conversation_controller.state
    
    def set_tts_callback(self, callback: Callable[[SpeechAct], Any]):
        """
        Set the callback for sending speech acts to TTS.
        
        The callback receives a SpeechAct and should send it to Moshi for TTS.
        Can be sync or async.
        """
        self._tts_callback = callback
    
    def set_stop_tts_callback(self, callback: Callable[[], Any]):
        """
        Set the callback for immediately stopping TTS playback.
        
        This is called on barge-in to stop Moshi's current audio output.
        """
        self._stop_tts_callback = callback
    
    def _handle_barge_in(self):
        """Internal barge-in handler."""
        now = datetime.now()
        
        # Check cooldown
        if self._last_barge_in:
            elapsed = (now - self._last_barge_in).total_seconds() * 1000
            if elapsed < self.config.barge_in_cooldown_ms:
                logger.debug(f"Barge-in ignored (cooldown: {elapsed:.0f}ms)")
                return
        
        self._last_barge_in = now
        self._total_barge_ins += 1
        self._is_tts_playing = False
        self.task_registry.cancel_all()
        self.scheduler.cancel_all()
        
        # Stop TTS immediately
        if self._stop_tts_callback:
            try:
                result = self._stop_tts_callback()
                if asyncio.iscoroutine(result):
                    asyncio.create_task(result)
            except Exception as e:
                logger.error(f"Stop TTS callback error: {e}")
        
        # Call external handler
        if self._external_barge_in:
            try:
                self._external_barge_in()
            except Exception as e:
                logger.error(f"External barge-in callback error: {e}")
        
        logger.info(f"Barge-in handled (total: {self._total_barge_ins})")
    
    def _handle_state_change(self, new_state: ConversationState):
        """Internal state change handler."""
        if new_state == ConversationState.SPEAKING:
            self._is_tts_playing = True
        elif new_state in (ConversationState.LISTENING, ConversationState.IDLE):
            self._is_tts_playing = False
        
        if self._external_state_change:
            try:
                self._external_state_change(new_state)
            except Exception as e:
                logger.error(f"External state change callback error: {e}")
    
    async def speak(
        self,
        content: AsyncGenerator[str, None],
        has_tools: bool = False,
    ) -> List[SpeechAct]:
        """
        Speak a response with full barge-in support.
        
        Args:
            content: Token stream from LLM
            has_tools: Whether tool calls are in progress (adds status prefix)
        
        Returns:
            List of speech acts that were delivered before any interruption
        """
        if not self._tts_callback:
            logger.warning("No TTS callback set, cannot speak")
            return []
        
        self._is_tts_playing = True
        
        try:
            delivered = await self.conversation_controller.speak(
                content=content,
                tts_callback=self._tts_callback,
                has_tools=has_tools,
            )
            self._total_speech_acts += len(delivered)
            return delivered
        finally:
            self._is_tts_playing = False

    async def stream_tool_progress(
        self,
        progress_stream: AsyncGenerator[ToolProgress, None],
        token: Optional[CancellationToken] = None,
    ) -> List[SpeechAct]:
        """
        Convert tool progress updates into status speech acts.

        Phase 3 (minimal):
        - starting -> quick status ("I'm looking that up...")
        - working  -> optional status if message provided
        - completed/error/cancelled -> short completion status

        Returns the list of emitted speech acts.
        """
        emitted: List[SpeechAct] = []
        if not self._tts_callback:
            return emitted

        cancelled = False
        try:
            async for progress in progress_stream:
                if token:
                    token.check()

                act = self._tool_progress_to_act(progress)
                if act is None:
                    continue

                result = self._tts_callback(act)
                if asyncio.iscoroutine(result):
                    await result
                emitted.append(act)
                self._total_speech_acts += 1
        except asyncio.CancelledError:
            cancelled = True
            raise
        finally:
            if (cancelled or (token and token.is_cancelled)) and hasattr(progress_stream, "aclose"):
                try:
                    await progress_stream.aclose()
                except Exception:
                    pass

        return emitted

    def _tool_progress_to_act(self, progress: ToolProgress) -> Optional[SpeechAct]:
        """Map tool progress updates to concise speech acts."""
        state = progress.state
        tool_name = progress.tool_name
        message = (progress.message or "").strip()

        if state == "starting":
            text = message or f"I'm looking up {tool_name} now."
            return SpeechAct(text=text, type=SpeechActType.STATUS)

        if state == "working":
            if not message:
                return None
            return SpeechAct(text=message, type=SpeechActType.STATUS)

        if state == "completed":
            text = message or f"Got it. {tool_name} is done."
            return SpeechAct(text=text, type=SpeechActType.STATUS)

        if state == "cancelled":
            text = message or f"Stopping {tool_name}."
            return SpeechAct(text=text, type=SpeechActType.STATUS)

        if state == "error":
            text = message or f"{tool_name} hit an error."
            return SpeechAct(text=text, type=SpeechActType.STATUS)

        return None

    async def drain_events_to_speech(self, max_items: int = 5) -> List[SpeechAct]:
        """
        Drain attention events and optionally speak selected ones.

        Subconscious loops never call TTS directly; this conscious method decides.
        """
        emitted: List[SpeechAct] = []
        if not self._tts_callback:
            return emitted
        for event in self.event_bus.drain(max_items=max_items):
            act = self._attention_event_to_act(event)
            if act is None:
                continue
            result = self._tts_callback(act)
            if asyncio.iscoroutine(result):
                await result
            emitted.append(act)
            self._total_speech_acts += 1
        return emitted

    def _attention_event_to_act(self, event: AttentionEvent) -> Optional[SpeechAct]:
        if event.type == "backpressure_rejection":
            return SpeechAct(
                text=event.data.get(
                    "message",
                    "I am already running several lookups. Want me to finish those first?",
                ),
                type=SpeechActType.STATUS,
            )
        if event.type == "world_update":
            return None
        if event.type == "pattern_detected":
            return SpeechAct(text="I noticed a new pattern in the background.", type=SpeechActType.STATUS)
        return None
    
    def on_audio(self, audio_chunk: bytes) -> bool:
        """
        Process incoming audio for VAD.
        
        Should be called for each audio frame from the user's microphone.
        Returns True if barge-in was triggered.
        
        Args:
            audio_chunk: Raw PCM audio bytes (16-bit signed, mono)
        
        Returns:
            True if barge-in triggered, False otherwise
        """
        return self.conversation_controller.on_audio_chunk(audio_chunk)
    
    def barge_in(self, user_input: Optional[str] = None):
        """
        Manually trigger barge-in.
        
        Use this if VAD detection happens elsewhere (e.g., in the browser).
        """
        self.conversation_controller.barge_in(user_input)
        self._handle_barge_in()
    
    def get_interrupted_draft(self) -> Optional[str]:
        """Get what MYCA was saying when interrupted."""
        return self.conversation_controller.get_interrupted_draft()
    
    def record_user_turn(self, content: str):
        """Record a user utterance for history."""
        self.conversation_controller.record_user_turn(content)
    
    def get_metrics(self) -> Dict:
        """Get session metrics."""
        return {
            "session_id": self.session_id,
            "conversation_id": self.conversation_id,
            "state": self.state.value,
            "is_tts_playing": self._is_tts_playing,
            "total_speech_acts": self._total_speech_acts,
            "total_barge_ins": self._total_barge_ins,
            "created_at": self._created_at.isoformat(),
            "active_task_count": len(self.task_registry.active()),
            "event_bus": self.event_bus.stats(),
            "scheduler": self.scheduler.stats(),
            "controller_metrics": self.conversation_controller.get_metrics(),
        }

    def create_tracked_task(
        self,
        coro: Any,
        category: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> TaskHandle:
        """
        Create and register a cancellable task.

        Phase 2 (minimal): call this for tool calls and delegated jobs so
        barge-in can cancel them through one path.
        """
        handle = self.task_registry.submit(category=category, coro=coro, metadata=metadata)
        if handle is None:
            asyncio.create_task(
                self.event_bus.publish(
                    AttentionEvent(
                        type="backpressure_rejection",
                        source="task_registry",
                        data={
                            "category": category,
                            "message": "I am already running several lookups. Want me to finish those first?",
                        },
                    )
                )
            )
            raise RuntimeError(f"Task rejected due to backpressure in category '{category}'")
        return handle

    def try_create_tracked_task(
        self,
        coro: Any,
        category: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[TaskHandle]:
        """Non-throwing submit for call-sites that prefer graceful fallback."""
        handle = self.task_registry.submit(category=category, coro=coro, metadata=metadata)
        if handle is None:
            asyncio.create_task(
                self.event_bus.publish(
                    AttentionEvent(
                        type="backpressure_rejection",
                        source="task_registry",
                        data={
                            "category": category,
                            "message": "I am already running several lookups. Want me to finish those first?",
                        },
                    )
                )
            )
        return handle

    def submit_scheduled_job(
        self,
        category: str,
        job_fn: Callable[[CancellationToken], Awaitable[Any]],
        priority: SchedulerPriority = SchedulerPriority.NORMAL,
        deadline_ms: int = 5000,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Submit a deadline-aware scheduled job (Phase 8)."""
        return self.scheduler.submit(
            category=category,
            job_fn=job_fn,
            priority=priority,
            deadline_ms=deadline_ms,
            metadata=metadata,
        )
    
    def reset(self):
        """Reset session state."""
        self.conversation_controller.reset()
        self._is_tts_playing = False
        self._last_barge_in = None
        self.task_registry.cancel_all()
        self.scheduler.cancel_all()
        logger.info(f"DuplexSession reset: {self.session_id[:8]}")


# Factory for easy creation
def create_duplex_session(
    session_id: Optional[str] = None,
    conversation_id: Optional[str] = None,
    user_id: Optional[str] = None,
    on_barge_in: Optional[Callable[[], None]] = None,
    on_state_change: Optional[Callable[[ConversationState], None]] = None,
) -> DuplexSession:
    """
    Create a DuplexSession for PersonaPlex bridge integration.
    
    Args:
        session_id: Unique session identifier
        conversation_id: Conversation to continue (for history)
        user_id: User identifier
        on_barge_in: Callback when user interrupts
        on_state_change: Callback when conversation state changes
    
    Returns:
        Configured DuplexSession ready for use
    """
    config = DuplexSessionConfig(
        session_id=session_id or str(uuid4()),
        conversation_id=conversation_id,
        user_id=user_id,
    )
    
    return DuplexSession(
        config=config,
        on_barge_in=on_barge_in,
        on_state_change=on_state_change,
    )
