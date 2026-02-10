"""
Tests for AttentionController

Tests the attention management system including:
- Focus prioritization
- Input categorization
- Focus stack management

Author: Morgan Rockwell / MYCA
Created: February 10, 2026
"""

import pytest
from datetime import datetime, timezone


class TestAttentionFocus:
    """Tests for AttentionFocus dataclass."""
    
    def test_attention_focus_creation(self):
        """AttentionFocus should be creatable with required fields."""
        from mycosoft_mas.consciousness.attention import AttentionFocus
        
        focus = AttentionFocus(
            content="Hello MYCA",
            source="text",
            category="user_input",
            priority=1.0
        )
        
        assert focus.content == "Hello MYCA"
        assert focus.source == "text"
        assert focus.category == "user_input"
        assert focus.priority == 1.0
    
    def test_attention_focus_default_timestamp(self):
        """AttentionFocus should have a timestamp."""
        from mycosoft_mas.consciousness.attention import AttentionFocus
        
        focus = AttentionFocus(
            content="test",
            source="text",
            category="user_input",
            priority=0.5
        )
        
        assert focus.timestamp is not None
        assert isinstance(focus.timestamp, datetime)


class TestAttentionController:
    """Tests for AttentionController."""
    
    def test_controller_initialization(self):
        """AttentionController should initialize correctly."""
        from mycosoft_mas.consciousness.attention import AttentionController
        
        controller = AttentionController()
        
        assert controller._current_focus is None
        assert len(controller._focus_stack) == 0
    
    @pytest.mark.asyncio
    async def test_focus_on_creates_focus(self):
        """focus_on should create and set current focus."""
        from mycosoft_mas.consciousness.attention import AttentionController
        
        controller = AttentionController()
        
        focus = await controller.focus_on(
            content="Hello",
            source="text",
            context={"user_id": "test"}
        )
        
        assert focus is not None
        assert focus.content == "Hello"
        assert controller._current_focus == focus
    
    @pytest.mark.asyncio
    async def test_focus_prioritization(self):
        """Higher priority should interrupt lower priority."""
        from mycosoft_mas.consciousness.attention import AttentionController
        
        controller = AttentionController()
        
        # Set low priority focus
        low = await controller.focus_on(
            content="Low priority",
            source="text",
            context={"urgency": "low"}
        )
        
        # High priority should interrupt
        high = await controller.focus_on(
            content="High priority",
            source="voice",
            context={"urgency": "high"}
        )
        
        assert controller._current_focus.content == "High priority"
    
    def test_categorize_input(self):
        """Inputs should be categorized correctly."""
        from mycosoft_mas.consciousness.attention import AttentionController
        
        controller = AttentionController()
        
        assert controller._categorize_input("Hello", "text", {}) == "user_input"
        assert controller._categorize_input("test", "voice", {}) == "user_input"
        assert controller._categorize_input("alert", "system", {}) == "system_alert"
    
    def test_calculate_priority(self):
        """Priority should be calculated based on source and context."""
        from mycosoft_mas.consciousness.attention import AttentionController
        
        controller = AttentionController()
        
        # Voice should have higher base priority
        voice_priority = controller._calculate_priority("test", "voice", {})
        text_priority = controller._calculate_priority("test", "text", {})
        
        assert voice_priority >= text_priority
        
        # Urgency should increase priority
        urgent_priority = controller._calculate_priority("test", "text", {"urgency": "high"})
        assert urgent_priority > text_priority
    
    @pytest.mark.asyncio
    async def test_pop_focus(self):
        """pop_focus should restore previous focus from stack."""
        from mycosoft_mas.consciousness.attention import AttentionController
        
        controller = AttentionController()
        
        # Set initial focus
        first = await controller.focus_on("First", "text", {})
        
        # Push to stack and set new focus
        controller._focus_stack.append(first)
        second = await controller.focus_on("Second", "text", {})
        
        # Pop should restore first
        await controller.pop_focus()
        
        # Stack should now be empty, current focus removed
        assert len(controller._focus_stack) == 0
