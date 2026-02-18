"""
Tests for SpeechPlanner - Full-Duplex Voice Phase 1

Created: February 12, 2026

Tests the speech act generation and boundary detection logic.
"""

import asyncio
import pytest
from typing import AsyncGenerator, List
from datetime import datetime

from mycosoft_mas.consciousness.speech_planner import (
    SpeechPlanner,
    SpeechAct,
    SpeechActType,
    get_speech_planner,
)


# Helper to create async token generator
async def token_stream(text: str, chunk_size: int = 5) -> AsyncGenerator[str, None]:
    """Simulate an LLM token stream."""
    for i in range(0, len(text), chunk_size):
        yield text[i:i + chunk_size]
        await asyncio.sleep(0.001)  # Simulate network latency


class TestSpeechPlannerBoundaries:
    """Test speech act boundary detection."""
    
    def test_min_chunk_size_enforced(self):
        """Ensure chunks are at least MIN_CHARS long."""
        planner = SpeechPlanner(min_chars=40)
        
        # A short sentence should NOT trigger a break
        text = "Hi."  # Only 3 chars
        break_point = planner._find_break_point(text)
        assert break_point is None
        
        # A sentence longer than min_chars should break
        text = "This is a sentence that is definitely longer than forty characters."
        break_point = planner._find_break_point(text)
        assert break_point is not None
        assert break_point > planner.min_chars
    
    def test_abbreviations_not_split(self):
        """Ensure abbreviations don't cause premature breaks."""
        planner = SpeechPlanner()
        
        # "Dr. Smith" should NOT split on the period after "Dr"
        text = "I consulted with Dr. Smith about the matter."
        
        # Check _is_abbreviation
        dr_period_idx = text.find("Dr.") + 2  # Index of period in "Dr."
        assert planner._is_abbreviation(text, dr_period_idx) is True
        
        # "Mr. Johnson" same thing
        text2 = "Mr. Johnson went to the store."
        mr_period_idx = text2.find("Mr.") + 2
        assert planner._is_abbreviation(text2, mr_period_idx) is True
    
    def test_numbers_not_split(self):
        """Ensure decimal numbers don't cause breaks (e.g., 3.14)."""
        planner = SpeechPlanner()
        
        text = "The value of pi is approximately 3.14159."
        
        # Find the period in "3.14159"
        decimal_idx = text.find("3.14159") + 1  # Index of period
        assert planner._is_abbreviation(text, decimal_idx) is True
    
    def test_double_newline_breaks(self):
        """Double newlines should trigger breaks (paragraph boundaries)."""
        planner = SpeechPlanner(min_chars=10)
        
        text = "First paragraph.\n\nSecond paragraph."
        break_point = planner._find_break_point(text)
        
        # Should break at the double newline
        assert break_point is not None
        assert text[:break_point].strip() == "First paragraph."
    
    def test_sentence_ending_breaks(self):
        """Sentence endings (. ! ?) should trigger breaks when long enough."""
        planner = SpeechPlanner(min_chars=10, target_chars=50)
        
        text = "This is a complete sentence. And here is another one."
        break_point = planner._find_break_point(text)
        
        # Should break after first sentence
        assert break_point is not None
        assert text[:break_point].strip().endswith(".")
    
    def test_max_chars_forces_break(self):
        """Very long text without punctuation should force a break at MAX_CHARS."""
        planner = SpeechPlanner(min_chars=20, max_chars=60)
        
        # Long text without punctuation
        text = "a" * 100  # 100 chars of 'a'
        break_point = planner._find_break_point(text)
        
        # Should force break at max_chars
        assert break_point is not None
        assert break_point <= planner.max_chars


class TestSpeechPlannerStreaming:
    """Test streaming speech act generation."""
    
    @pytest.mark.asyncio
    async def test_plan_generates_acts(self):
        """Test that plan() generates speech acts from token stream."""
        planner = SpeechPlanner(target_chars=40, min_chars=20)
        
        text = "This is a test. Here is another sentence. And a third one."
        tokens = token_stream(text, chunk_size=5)
        
        acts: List[SpeechAct] = []
        async for act in planner.plan(tokens):
            acts.append(act)
        
        # Should have generated at least one act
        assert len(acts) >= 1
        
        # All acts should have text
        for act in acts:
            assert act.text
        
        # Last act should be FINAL, others should be STATEMENT
        if len(acts) == 1:
            assert acts[0].type == SpeechActType.FINAL
        else:
            for act in acts[:-1]:
                assert act.type == SpeechActType.STATEMENT
            assert acts[-1].type == SpeechActType.FINAL
    
    @pytest.mark.asyncio
    async def test_plan_cancellation(self):
        """Test that plan() respects cancellation."""
        planner = SpeechPlanner()
        
        cancelled = False
        
        def check_cancel() -> bool:
            return cancelled
        
        # Long text
        text = "This is sentence one. This is sentence two. This is sentence three. This is sentence four."
        tokens = token_stream(text, chunk_size=3)
        
        acts: List[SpeechAct] = []
        async for act in planner.plan(tokens, on_cancel=check_cancel):
            acts.append(act)
            # Cancel after first act
            cancelled = True
        
        # Should have stopped after first act
        assert len(acts) == 1
    
    @pytest.mark.asyncio
    async def test_plan_final_act(self):
        """Test that the last act is marked as FINAL."""
        planner = SpeechPlanner(target_chars=1000)  # Large target to get single act
        
        text = "Short message."
        tokens = token_stream(text, chunk_size=5)
        
        acts: List[SpeechAct] = []
        async for act in planner.plan(tokens):
            acts.append(act)
        
        # Last act should be FINAL type
        assert len(acts) >= 1
        assert acts[-1].type == SpeechActType.FINAL


class TestSpeechPlannerHelpers:
    """Test helper methods."""
    
    def test_backchannel(self):
        """Test backchannel generation."""
        planner = SpeechPlanner()
        
        act = planner.backchannel()
        
        assert act.type == SpeechActType.BACKCHANNEL
        assert act.text in SpeechPlanner.BACKCHANNELS
    
    def test_status(self):
        """Test status message generation."""
        planner = SpeechPlanner()
        
        act = planner.status("lookup")
        
        assert act.type == SpeechActType.STATUS
        assert act.text  # Should have some text
    
    def test_correction(self):
        """Test correction generation."""
        planner = SpeechPlanner()
        
        act = planner.correction("the meeting is at 3pm, not 2pm")
        
        assert act.type == SpeechActType.CORRECTION
        assert "3pm" in act.text
    
    def test_estimate_duration(self):
        """Test speech duration estimation."""
        planner = SpeechPlanner()
        
        acts = [
            SpeechAct(text="Hello", type=SpeechActType.STATEMENT),
            SpeechAct(text="How are you doing today", type=SpeechActType.STATEMENT),
        ]
        
        duration = planner.estimate_duration(acts)
        
        # Should estimate some positive duration
        assert duration > 0
        
        # Longer text should have longer duration
        short_acts = [SpeechAct(text="Hi", type=SpeechActType.STATEMENT)]
        short_duration = planner.estimate_duration(short_acts)
        assert duration > short_duration


class TestSpeechPlannerWithStatus:
    """Test plan_with_status() which prefixes with status messages."""
    
    @pytest.mark.asyncio
    async def test_tool_status_prefix(self):
        """Test that plan_with_status adds status when tools are running."""
        planner = SpeechPlanner()
        
        text = "Here are the results of your query."
        tokens = token_stream(text, chunk_size=5)
        
        acts: List[SpeechAct] = []
        async for act in planner.plan_with_status(tokens, has_tools=True):
            acts.append(act)
        
        # First act should be a STATUS type
        assert len(acts) >= 1
        assert acts[0].type == SpeechActType.STATUS


class TestGetSpeechPlanner:
    """Test singleton factory."""
    
    def test_singleton(self):
        """Test that get_speech_planner returns the same instance."""
        planner1 = get_speech_planner()
        planner2 = get_speech_planner()
        
        assert planner1 is planner2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
