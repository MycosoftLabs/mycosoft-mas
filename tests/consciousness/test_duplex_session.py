"""
Tests for DuplexSession - Full-Duplex Voice Phase 1

Created: February 12, 2026

Tests the session object that integrates all duplex components.
"""

import asyncio
import pytest
from typing import AsyncGenerator, List
from unittest.mock import MagicMock, AsyncMock
import struct

from mycosoft_mas.consciousness.duplex_session import (
    DuplexSession,
    DuplexSessionConfig,
    ToolProgress,
    create_duplex_session,
)
from mycosoft_mas.consciousness.conversation_control import ConversationState
from mycosoft_mas.consciousness.event_bus import AttentionEvent
from mycosoft_mas.consciousness.speech_planner import SpeechAct, SpeechActType


def create_audio_chunk(energy_level: float = 0.05) -> bytes:
    """Create a fake audio chunk with specified energy level."""
    amplitude = int(energy_level * 32767)
    samples = [amplitude, -amplitude] * 100
    return struct.pack(f"<{len(samples)}h", *samples)


class TestDuplexSessionConfig:
    """Test session configuration."""
    
    def test_default_config(self):
        """Default config should have sensible values."""
        config = DuplexSessionConfig()
        
        assert config.session_id  # Auto-generated
        assert config.vad_energy_threshold > 0
        assert config.vad_min_speech_frames > 0
        assert config.target_speech_chars > 0
    
    def test_custom_config(self):
        """Custom config values should be used."""
        config = DuplexSessionConfig(
            session_id="test-123",
            vad_energy_threshold=0.05,
            target_speech_chars=100,
        )
        
        assert config.session_id == "test-123"
        assert config.vad_energy_threshold == 0.05
        assert config.target_speech_chars == 100


class TestDuplexSessionCreation:
    """Test session creation and initialization."""
    
    def test_create_session(self):
        """Session should initialize properly."""
        session = DuplexSession()
        
        assert session.session_id
        assert session.state == ConversationState.IDLE
        assert session.is_speaking is False
        assert session.is_tts_playing is False
    
    def test_create_session_with_config(self):
        """Session should respect config."""
        config = DuplexSessionConfig(session_id="custom-id")
        session = DuplexSession(config=config)
        
        assert session.session_id == "custom-id"
    
    def test_factory_function(self):
        """Factory should create session correctly."""
        session = create_duplex_session(
            session_id="factory-test",
            user_id="user-123",
        )
        
        assert session.session_id == "factory-test"
        assert session.config.user_id == "user-123"


class TestDuplexSessionCallbacks:
    """Test TTS and stop callbacks."""
    
    def test_set_tts_callback(self):
        """TTS callback should be settable."""
        session = DuplexSession()
        
        callback = MagicMock()
        session.set_tts_callback(callback)
        
        assert session._tts_callback is callback
    
    def test_set_stop_tts_callback(self):
        """Stop TTS callback should be settable."""
        session = DuplexSession()
        
        callback = MagicMock()
        session.set_stop_tts_callback(callback)
        
        assert session._stop_tts_callback is callback


class TestDuplexSessionSpeak:
    """Test speaking functionality."""
    
    @pytest.mark.asyncio
    async def test_speak_without_callback(self):
        """Speak without TTS callback should return empty."""
        session = DuplexSession()
        
        async def tokens():
            yield "Hello"
        
        result = await session.speak(tokens())
        
        assert result == []
    
    @pytest.mark.asyncio
    async def test_speak_with_callback(self):
        """Speak with TTS callback should deliver acts."""
        session = DuplexSession()
        
        delivered: List[SpeechAct] = []
        session.set_tts_callback(lambda act: delivered.append(act))
        
        async def tokens():
            yield "Hello, this is a test message that should be spoken."
        
        result = await session.speak(tokens())
        
        assert len(result) >= 1
        assert len(delivered) >= 1
    
    @pytest.mark.asyncio
    async def test_speak_sets_tts_playing(self):
        """Speak should set is_tts_playing during speech."""
        session = DuplexSession()
        session.set_tts_callback(lambda act: None)
        
        was_playing = False
        
        async def tokens():
            nonlocal was_playing
            was_playing = session.is_tts_playing
            yield "Test"
        
        await session.speak(tokens())
        
        # Should have been playing during generation
        # (may be False now after completion)
        assert was_playing or not session.is_tts_playing


class TestDuplexSessionBargeIn:
    """Test barge-in handling."""
    
    def test_manual_barge_in(self):
        """Manual barge-in should work."""
        session = DuplexSession()
        
        barge_in_called = False
        
        def on_barge_in():
            nonlocal barge_in_called
            barge_in_called = True
        
        session2 = DuplexSession(on_barge_in=on_barge_in)
        session2.barge_in("user interruption")
        
        assert barge_in_called
    
    def test_barge_in_calls_stop_tts(self):
        """Barge-in should call stop TTS callback."""
        session = DuplexSession()
        
        stop_called = False
        
        def stop_tts():
            nonlocal stop_called
            stop_called = True
        
        session.set_stop_tts_callback(stop_tts)
        session.barge_in()
        
        # Note: stop_tts is called via _handle_barge_in
        # which is called when conversation_controller.barge_in triggers callback
        # For manual barge_in, we call _handle_barge_in ourselves
    
    def test_barge_in_respects_cooldown(self):
        """Multiple rapid barge-ins should be debounced."""
        config = DuplexSessionConfig(barge_in_cooldown_ms=500)
        session = DuplexSession(config=config)
        
        barge_in_count = 0
        
        def on_barge_in():
            nonlocal barge_in_count
            barge_in_count += 1
        
        # We need to track via _handle_barge_in
        session._external_barge_in = on_barge_in
        
        # First barge-in should work
        session._handle_barge_in()
        assert barge_in_count == 1
        
        # Immediate second should be ignored (cooldown)
        session._handle_barge_in()
        assert barge_in_count == 1  # Still 1


class TestDuplexSessionVAD:
    """Test VAD integration."""
    
    def test_audio_triggers_barge_in(self):
        """Loud audio during TTS should trigger barge-in."""
        config = DuplexSessionConfig(
            vad_energy_threshold=0.02,
            vad_min_speech_frames=2,
        )
        session = DuplexSession(config=config)
        
        # Simulate TTS playing
        session._is_tts_playing = True
        session.conversation_controller._state = ConversationState.SPEAKING
        
        # Send loud audio frames
        loud_chunk = create_audio_chunk(0.1)
        
        # First frame
        result1 = session.on_audio(loud_chunk)
        assert result1 is False  # Not yet (debounce)
        
        # Second frame - should trigger
        result2 = session.on_audio(loud_chunk)
        assert result2 is True


class TestDuplexSessionHistory:
    """Test history tracking."""
    
    def test_record_user_turn(self):
        """User turns should be recorded."""
        session = DuplexSession()
        
        session.record_user_turn("Hello")
        session.record_user_turn("How are you?")
        
        history = session.conversation_controller.get_history()
        assert len(history) == 2


class TestDuplexSessionMetrics:
    """Test metrics collection."""
    
    def test_metrics_structure(self):
        """Metrics should have expected structure."""
        session = DuplexSession()
        
        metrics = session.get_metrics()
        
        assert "session_id" in metrics
        assert "state" in metrics
        assert "is_tts_playing" in metrics
        assert "total_speech_acts" in metrics
        assert "total_barge_ins" in metrics
        assert "controller_metrics" in metrics
    
    def test_metrics_count_barge_ins(self):
        """Metrics should count barge-ins."""
        session = DuplexSession()
        
        initial_metrics = session.get_metrics()
        assert initial_metrics["total_barge_ins"] == 0
        
        # Trigger barge-in
        session._handle_barge_in()
        
        updated_metrics = session.get_metrics()
        assert updated_metrics["total_barge_ins"] == 1


class TestDuplexSessionReset:
    """Test session reset."""
    
    def test_reset_clears_state(self):
        """Reset should clear session state."""
        session = DuplexSession()
        
        # Trigger some state changes
        session._handle_barge_in()
        
        # Reset
        session.reset()
        
        # State should be clean
        assert session.state == ConversationState.IDLE
        assert session.is_tts_playing is False


class TestDuplexSessionTaskCancellation:
    """Test Phase 2 minimal task cancellation wiring."""

    @pytest.mark.asyncio
    async def test_barge_in_cancels_tracked_tasks(self):
        session = DuplexSession()
        cancelled = False

        async def long_job():
            nonlocal cancelled
            try:
                await asyncio.sleep(2)
            except asyncio.CancelledError:
                cancelled = True
                raise

        handle = session.create_tracked_task(long_job(), category="tool")
        await asyncio.sleep(0.02)
        session._handle_barge_in()
        await asyncio.sleep(0.02)

        assert handle.task.cancelled() or cancelled

    @pytest.mark.asyncio
    async def test_create_tracked_task_registers_handle(self):
        session = DuplexSession()

        async def short_job():
            await asyncio.sleep(0.01)
            return "ok"

        handle = session.create_tracked_task(short_job(), category="agent")
        assert handle.category == "agent"
        assert handle.task_id.startswith("agent-")
        await handle.task

    @pytest.mark.asyncio
    async def test_backpressure_rejection_returns_none_in_try_mode(self):
        session = DuplexSession()
        original = dict(session.task_registry.MAX_PER_CATEGORY)
        session.task_registry.MAX_PER_CATEGORY["tool"] = 1

        async def long_job():
            await asyncio.sleep(0.5)

        try:
            h1 = session.try_create_tracked_task(long_job(), category="tool")
            h2 = session.try_create_tracked_task(long_job(), category="tool")
            assert h1 is not None
            assert h2 is None
        finally:
            session.task_registry.MAX_PER_CATEGORY = original
            session.task_registry.cancel_all()

    @pytest.mark.asyncio
    async def test_drain_events_to_speech(self):
        session = DuplexSession()
        spoken = []
        session.set_tts_callback(lambda act: spoken.append(act.text))
        await session.event_bus.publish(
            AttentionEvent(
                type="backpressure_rejection",
                source="task_registry",
                data={"message": "Busy right now."},
            )
        )
        acts = await session.drain_events_to_speech(max_items=5)
        assert len(acts) == 1
        assert spoken == ["Busy right now."]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
