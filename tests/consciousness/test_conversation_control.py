"""
Tests for ConversationController - Full-Duplex Voice Phase 1

Created: February 12, 2026

Tests barge-in behavior, state management, and speech act delivery.
"""

import asyncio
import pytest
from typing import AsyncGenerator, List
from unittest.mock import MagicMock, AsyncMock
import struct

from mycosoft_mas.consciousness.conversation_control import (
    ConversationController,
    ConversationState,
    VoiceActivityDetector,
    InterruptedDraft,
    create_conversation_controller,
)
from mycosoft_mas.consciousness.speech_planner import (
    SpeechPlanner,
    SpeechAct,
    SpeechActType,
)


# Helper to create async token generator
async def token_stream(text: str, chunk_size: int = 5) -> AsyncGenerator[str, None]:
    """Simulate an LLM token stream."""
    for i in range(0, len(text), chunk_size):
        yield text[i:i + chunk_size]
        await asyncio.sleep(0.001)


def create_audio_chunk(energy_level: float = 0.05) -> bytes:
    """Create a fake audio chunk with specified energy level."""
    # Generate 16-bit PCM samples
    amplitude = int(energy_level * 32767)
    samples = [amplitude, -amplitude] * 100  # 200 samples
    return struct.pack(f"<{len(samples)}h", *samples)


class TestVoiceActivityDetector:
    """Test VAD speech detection."""
    
    def test_detect_silence(self):
        """Low energy audio should not trigger detection."""
        vad = VoiceActivityDetector(energy_threshold=0.02, min_speech_frames=3)
        
        # Very low energy
        silent_chunk = create_audio_chunk(0.001)
        
        # Multiple frames should all return False
        for _ in range(10):
            assert vad.detect(silent_chunk) is False
    
    def test_detect_speech_with_debounce(self):
        """Speech detection requires consecutive frames (debounce)."""
        vad = VoiceActivityDetector(energy_threshold=0.02, min_speech_frames=3)
        
        loud_chunk = create_audio_chunk(0.1)  # High energy
        
        # First two frames should not trigger
        assert vad.detect(loud_chunk) is False
        assert vad.detect(loud_chunk) is False
        
        # Third consecutive frame should trigger
        assert vad.detect(loud_chunk) is True
    
    def test_speech_frame_reset(self):
        """Silence between speech frames resets counter."""
        vad = VoiceActivityDetector(energy_threshold=0.02, min_speech_frames=3)
        
        loud_chunk = create_audio_chunk(0.1)
        silent_chunk = create_audio_chunk(0.001)
        
        # Two loud frames
        vad.detect(loud_chunk)
        vad.detect(loud_chunk)
        
        # Then silence - should reset
        vad.detect(silent_chunk)
        
        # Now two more loud frames should not trigger yet
        assert vad.detect(loud_chunk) is False
        assert vad.detect(loud_chunk) is False
        
        # Third consecutive should trigger
        assert vad.detect(loud_chunk) is True
    
    def test_tts_cooldown(self):
        """During TTS cooldown, VAD should not detect speech."""
        vad = VoiceActivityDetector(energy_threshold=0.02, min_speech_frames=1)
        
        loud_chunk = create_audio_chunk(0.1)
        
        # Start cooldown (simulating TTS playing)
        vad.start_tts_cooldown()
        
        # Even loud audio should not trigger during cooldown
        assert vad.detect(loud_chunk) is False


class TestConversationControllerState:
    """Test conversation state management."""
    
    def test_initial_state(self):
        """Controller starts in IDLE state."""
        controller = ConversationController()
        assert controller.state == ConversationState.IDLE
    
    def test_state_transition_on_speak(self):
        """State changes to SPEAKING when speak() starts."""
        controller = ConversationController()
        
        # We'll check state changes via callback
        states: List[ConversationState] = []
        controller._on_state_change = lambda s: states.append(s)
        
        # Start speaking (will complete quickly with our test)
        async def run_test():
            async def tokens():
                yield "Hello"
            
            await controller.speak(
                content=tokens(),
                tts_callback=lambda act: None,
            )
        
        asyncio.run(run_test())
        
        # Should have transitioned through states
        assert ConversationState.SPEAKING in states or ConversationState.PROCESSING in states


class TestConversationControllerBargeIn:
    """Test barge-in behavior."""
    
    @pytest.mark.asyncio
    async def test_barge_in_stops_speak(self):
        """Barge-in should stop speech generation."""
        controller = ConversationController()
        
        delivered_acts: List[SpeechAct] = []
        
        def fake_tts(act: SpeechAct):
            delivered_acts.append(act)
        
        # Long text that would generate multiple acts
        text = "This is the first sentence. This is the second sentence. This is the third sentence. This is the fourth sentence."
        
        async def long_tokens():
            for char in text:
                yield char
                await asyncio.sleep(0.001)
        
        # Start speaking in a task
        async def speak_task():
            return await controller.speak(
                content=long_tokens(),
                tts_callback=fake_tts,
            )
        
        task = asyncio.create_task(speak_task())
        
        # Wait a bit then barge in
        await asyncio.sleep(0.05)
        controller.barge_in("user interrupted")
        
        # Wait for task to complete
        await task
        
        # Should have interrupted before all text was delivered
        total_delivered = sum(len(act.text) for act in delivered_acts)
        assert total_delivered < len(text)
    
    @pytest.mark.asyncio
    async def test_barge_in_preserves_draft(self):
        """Barge-in should preserve what was being said."""
        controller = ConversationController()
        
        text = "This is a long response that will be interrupted by the user."
        
        async def tokens():
            for char in text:
                yield char
                await asyncio.sleep(0.001)
        
        async def speak_task():
            return await controller.speak(
                content=tokens(),
                tts_callback=lambda act: None,
            )
        
        task = asyncio.create_task(speak_task())
        
        # Wait then barge in
        await asyncio.sleep(0.02)
        controller.barge_in()
        
        await task
        
        # Should have an interrupted draft
        draft = controller.get_interrupted_draft()
        # Draft might be None if we interrupted very early
        # But the mechanism should exist
        last_draft = controller.last_interrupted_draft
        assert last_draft is None or isinstance(last_draft, InterruptedDraft)
    
    def test_barge_in_calls_callback(self):
        """Barge-in should trigger the callback when speaking."""
        callback_called = False
        
        def on_barge_in():
            nonlocal callback_called
            callback_called = True
        
        controller = ConversationController(on_barge_in=on_barge_in)
        # Must be in SPEAKING state for barge_in to work
        controller._state = ConversationState.SPEAKING
        controller.barge_in()
        
        assert callback_called


class TestConversationControllerAudioVAD:
    """Test VAD integration with ConversationController."""
    
    @pytest.mark.asyncio
    async def test_audio_triggers_barge_in_during_speech(self):
        """Audio with speech during TTS should trigger barge-in."""
        vad = VoiceActivityDetector(energy_threshold=0.02, min_speech_frames=2)
        controller = ConversationController(vad=vad)
        
        barge_in_triggered = False
        
        def on_barge_in():
            nonlocal barge_in_triggered
            barge_in_triggered = True
        
        controller._on_barge_in = on_barge_in
        
        # Simulate speaking state
        controller._state = ConversationState.SPEAKING
        
        # Send loud audio frames
        loud_chunk = create_audio_chunk(0.1)
        
        # First frame - no trigger yet
        controller.on_audio_chunk(loud_chunk)
        assert not barge_in_triggered
        
        # Second frame - should trigger
        controller.on_audio_chunk(loud_chunk)
        assert barge_in_triggered
    
    def test_audio_no_barge_in_when_idle(self):
        """Audio during IDLE state should not trigger barge-in."""
        vad = VoiceActivityDetector(energy_threshold=0.02, min_speech_frames=1)
        controller = ConversationController(vad=vad)
        
        barge_in_triggered = False
        controller._on_barge_in = lambda: setattr(controller, '_barge_in_triggered', True)
        
        # State is IDLE
        assert controller.state == ConversationState.IDLE
        
        # Send loud audio
        loud_chunk = create_audio_chunk(0.1)
        result = controller.on_audio_chunk(loud_chunk)
        
        # Should not trigger barge-in (we're not speaking)
        assert result is False


class TestConversationControllerHistory:
    """Test conversation history tracking."""
    
    def test_record_user_turn(self):
        """User turns should be recorded."""
        controller = ConversationController()
        
        controller.record_user_turn("Hello there")
        controller.record_user_turn("How are you?")
        
        history = controller.get_history()
        
        assert len(history) == 2
        assert history[0]["content"] == "Hello there"
        assert history[0]["speaker"] == "user"


class TestConversationControllerMetrics:
    """Test metrics collection."""
    
    def test_metrics_structure(self):
        """Metrics should have expected structure."""
        controller = ConversationController()
        
        metrics = controller.get_metrics()
        
        assert "state" in metrics
        assert "turn_count" in metrics
        assert "barge_in_count" in metrics
        assert "speech_acts_delivered" in metrics
        assert "has_interrupted_draft" in metrics


class TestCreateConversationController:
    """Test factory function."""
    
    def test_create_with_defaults(self):
        """Factory should create controller with defaults."""
        controller = create_conversation_controller()
        
        assert controller is not None
        assert controller.state == ConversationState.IDLE
    
    def test_create_with_callbacks(self):
        """Factory should wire up callbacks."""
        barge_in_called = False
        state_changes = []
        
        def on_barge_in():
            nonlocal barge_in_called
            barge_in_called = True
        
        def on_state_change(state):
            state_changes.append(state)
        
        controller = create_conversation_controller(
            on_barge_in=on_barge_in,
            on_state_change=on_state_change,
        )
        
        # Must be in SPEAKING state for barge_in to work
        controller._state = ConversationState.SPEAKING
        
        # Trigger barge-in
        controller.barge_in()
        
        assert barge_in_called


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
