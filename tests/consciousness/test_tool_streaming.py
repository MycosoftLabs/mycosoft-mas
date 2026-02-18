"""
Tests for tool streaming speech acts - Full-Duplex Voice Phase 3 (minimal).

Created: February 12, 2026
"""

import asyncio
from typing import AsyncGenerator, List

import pytest

from mycosoft_mas.consciousness.cancellation import CancellationToken
from mycosoft_mas.consciousness.duplex_session import DuplexSession, ToolProgress
from mycosoft_mas.consciousness.speech_planner import SpeechActType


async def progress_stream() -> AsyncGenerator[ToolProgress, None]:
    yield ToolProgress(state="starting", tool_name="taxonomy_lookup", message="I'm looking that up...")
    await asyncio.sleep(0.001)
    yield ToolProgress(state="working", tool_name="taxonomy_lookup", message="Still checking records...")
    await asyncio.sleep(0.001)
    yield ToolProgress(state="completed", tool_name="taxonomy_lookup", message="Found it.")


class TestToolStreaming:
    @pytest.mark.asyncio
    async def test_stream_tool_progress_emits_status_acts(self):
        session = DuplexSession()
        emitted: List[str] = []
        session.set_tts_callback(lambda act: emitted.append(act.text))

        acts = await session.stream_tool_progress(progress_stream())

        assert len(acts) == 3
        assert all(act.type == SpeechActType.STATUS for act in acts)
        assert emitted[0] == "I'm looking that up..."
        assert emitted[-1] == "Found it."

    @pytest.mark.asyncio
    async def test_stream_tool_progress_honors_cancellation_token(self):
        session = DuplexSession()
        emitted: List[str] = []
        session.set_tts_callback(lambda act: emitted.append(act.text))
        token = CancellationToken()

        async def cancellable_stream() -> AsyncGenerator[ToolProgress, None]:
            yield ToolProgress(state="starting", tool_name="lookup", message="Starting lookup.")
            token.cancel()
            yield ToolProgress(state="working", tool_name="lookup", message="Should never be spoken")

        with pytest.raises(asyncio.CancelledError):
            await session.stream_tool_progress(cancellable_stream(), token=token)

        assert emitted == ["Starting lookup."]

