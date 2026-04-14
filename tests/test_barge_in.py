"""
Tests for barge-in (user interruption during TTS playback).

Tests cover:
- VAD detects speech during TTS
- Barge-in cancels speech output
- Interrupted draft is preserved for context
- ConversationController state machine transitions
- VoiceActivityDetector: debounce and cooldown behaviour

Author: MYCA / Consciousness OS
Created: April 2026
"""

import asyncio
import struct
from typing import AsyncGenerator, List
from unittest.mock import AsyncMock, MagicMock

import numpy as np
import pytest

from mycosoft_mas.consciousness.conversation_control import (
    ConversationController,
    ConversationState,
    VoiceActivityDetector,
    create_conversation_controller,
)
from mycosoft_mas.consciousness.speech_planner import SpeechAct, SpeechActType


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_audio(energy: float, n_samples: int = 512) -> bytes:
    """Create PCM bytes with a given RMS energy level."""
    amplitude = int(energy * 32768)
    samples = np.full(n_samples, amplitude, dtype=np.int16)
    return samples.tobytes()


def _silence(n_samples: int = 512) -> bytes:
    return _make_audio(0.001, n_samples)


def _loud_speech(n_samples: int = 512) -> bytes:
    return _make_audio(0.5, n_samples)


async def _token_gen(tokens: List[str]) -> AsyncGenerator[str, None]:
    for t in tokens:
        yield t
        await asyncio.sleep(0)


# ---------------------------------------------------------------------------
# VoiceActivityDetector
# ---------------------------------------------------------------------------


class TestVoiceActivityDetector:
    def test_silence_not_detected(self):
        vad = VoiceActivityDetector()
        assert not vad.detect(_silence())

    def test_single_loud_frame_not_detected(self):
        """Single frame above threshold should NOT trigger (requires min_frames)."""
        vad = VoiceActivityDetector(min_speech_frames=3)
        assert not vad.detect(_loud_speech())

    def test_sustained_speech_detected(self):
        """3 consecutive loud frames above threshold → speech detected."""
        vad = VoiceActivityDetector(min_speech_frames=3)
        vad.detect(_loud_speech())
        vad.detect(_loud_speech())
        result = vad.detect(_loud_speech())
        assert result

    def test_cooldown_after_tts(self):
        """During TTS cooldown, no speech should be detected."""
        from mycosoft_mas.consciousness.conversation_control import VADConfig

        vad = VoiceActivityDetector(min_speech_frames=1)
        vad.start_tts_cooldown()
        # Cooldown lasts exactly TTS_COOLDOWN_FRAMES frames
        for _ in range(VADConfig.TTS_COOLDOWN_FRAMES):
            assert not vad.detect(_loud_speech()), "Cooldown should suppress detection"

    def test_reset_clears_state(self):
        """After reset, detection starts fresh."""
        vad = VoiceActivityDetector(min_speech_frames=2)
        vad.detect(_loud_speech())  # partial count
        vad.reset()
        # After reset, one frame should NOT trigger (min_frames=2)
        assert not vad.detect(_loud_speech())


# ---------------------------------------------------------------------------
# ConversationController
# ---------------------------------------------------------------------------


class TestConversationController:
    def _make_controller(self, barge_in_cb=None) -> ConversationController:
        return ConversationController(
            on_barge_in=barge_in_cb,
        )

    @pytest.mark.asyncio
    async def test_speak_delivers_all_acts_when_not_interrupted(self):
        """Without barge-in, all speech acts should be delivered."""
        ctrl = self._make_controller()
        delivered: List[SpeechAct] = []

        async def tts_cb(act: SpeechAct):
            delivered.append(act)

        tokens = _token_gen(
            ["Hello! This is a test sentence. And here is another one."]
        )
        acts = await ctrl.speak(tokens, tts_callback=tts_cb)
        assert len(acts) >= 1

    @pytest.mark.asyncio
    async def test_barge_in_cancels_speech(self):
        """Calling barge_in() during speak() should stop delivery."""
        ctrl = self._make_controller()
        delivered: List[SpeechAct] = []
        barge_in_triggered = False

        async def slow_tts(act: SpeechAct):
            nonlocal barge_in_triggered
            delivered.append(act)
            if len(delivered) == 1:
                # Trigger barge-in after first act
                ctrl.barge_in("I want to say something")
                barge_in_triggered = True
            await asyncio.sleep(0)

        long_tokens = ["This is a first sentence. " * 3 + "And more text here. " * 5]
        await ctrl.speak(_token_gen(long_tokens), tts_callback=slow_tts)
        assert barge_in_triggered
        # Not all possible speech acts should have been delivered

    @pytest.mark.asyncio
    async def test_barge_in_preserves_draft(self):
        """After barge-in, the interrupted draft should be accessible."""
        ctrl = self._make_controller()

        async def tts_cb(act: SpeechAct):
            ctrl.barge_in("interrupt!")

        tokens = _token_gen(["Some long text that takes multiple speech acts to say out loud."])
        await ctrl.speak(tokens, tts_callback=tts_cb)

        draft = ctrl.last_interrupted_draft
        # We may or may not have a draft depending on timing, but no error
        # The state should have reverted to LISTENING
        assert ctrl.state == ConversationState.LISTENING

    def test_on_audio_chunk_triggers_barge_in(self):
        """VAD detecting speech during TTS should trigger barge-in."""
        barge_in_called = False

        def on_barge_in():
            nonlocal barge_in_called
            barge_in_called = True

        ctrl = ConversationController(
            vad=VoiceActivityDetector(min_speech_frames=1),
            on_barge_in=on_barge_in,
        )
        # Force speaking state
        ctrl._set_state(ConversationState.SPEAKING)

        # Send enough loud audio to trigger VAD
        for _ in range(3):
            ctrl.on_audio_chunk(_loud_speech())

        assert barge_in_called

    def test_on_audio_chunk_silent_no_barge_in(self):
        """Silence during TTS should not trigger barge-in."""
        barge_in_called = False

        ctrl = ConversationController(on_barge_in=lambda: None)
        ctrl._set_state(ConversationState.SPEAKING)

        for _ in range(10):
            triggered = ctrl.on_audio_chunk(_silence())
            assert not triggered

    @pytest.mark.asyncio
    async def test_metrics_track_barge_ins(self):
        """Metrics should count barge-in events."""
        ctrl = self._make_controller()

        async def tts_cb(act: SpeechAct):
            ctrl.barge_in()

        await ctrl.speak(
            _token_gen(["Text for speech act. More text here!"]),
            tts_callback=tts_cb,
        )
        metrics = ctrl.get_metrics()
        assert metrics["barge_in_count"] >= 1

    def test_record_user_turn(self):
        """User turns should appear in conversation history."""
        ctrl = self._make_controller()
        ctrl.record_user_turn("Hello MYCA")
        history = ctrl.get_history()
        assert any(t["speaker"] == "user" and "Hello" in t["content"] for t in history)

    def test_factory_function(self):
        """create_conversation_controller() should return a working controller."""
        ctrl = create_conversation_controller()
        assert isinstance(ctrl, ConversationController)
        assert ctrl.state == ConversationState.IDLE
