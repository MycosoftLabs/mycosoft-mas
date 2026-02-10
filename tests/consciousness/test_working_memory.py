"""
Tests for WorkingMemory

Tests the short-term memory system including:
- Capacity limits (7±2 items)
- Item decay
- Context retrieval

Author: Morgan Rockwell / MYCA
Created: February 10, 2026
"""

import pytest
from datetime import datetime, timezone


class TestWorkingMemoryItem:
    """Tests for WorkingMemoryItem dataclass."""
    
    def test_item_creation(self):
        """WorkingMemoryItem should be creatable."""
        from mycosoft_mas.consciousness.working_memory import WorkingMemoryItem
        
        item = WorkingMemoryItem(
            id="test_1",
            content="Test content",
            type="input",
            relevance=1.0
        )
        
        assert item.id == "test_1"
        assert item.content == "Test content"
        assert item.relevance == 1.0
    
    def test_item_has_timestamp(self):
        """Items should have creation timestamp."""
        from mycosoft_mas.consciousness.working_memory import WorkingMemoryItem
        
        item = WorkingMemoryItem(
            id="test",
            content="test",
            type="input",
            relevance=0.5
        )
        
        assert item.created_at is not None


class TestWorkingMemory:
    """Tests for WorkingMemory."""
    
    def test_initialization(self):
        """WorkingMemory should initialize empty."""
        from mycosoft_mas.consciousness.working_memory import WorkingMemory
        
        memory = WorkingMemory()
        
        assert len(memory._items) == 0
        assert memory.capacity == 7  # Default capacity
    
    @pytest.mark.asyncio
    async def test_add_item(self):
        """Items should be addable."""
        from mycosoft_mas.consciousness.working_memory import WorkingMemory
        
        memory = WorkingMemory()
        
        await memory.add("Test content", "input", relevance=0.8)
        
        assert len(memory._items) == 1
    
    @pytest.mark.asyncio
    async def test_capacity_limit(self):
        """Memory should not exceed capacity."""
        from mycosoft_mas.consciousness.working_memory import WorkingMemory
        
        memory = WorkingMemory(capacity=3)
        
        # Add more items than capacity
        for i in range(5):
            await memory.add(f"Item {i}", "input", relevance=0.5)
        
        # Should only keep 3 most relevant
        assert len(memory._items) <= 3
    
    @pytest.mark.asyncio
    async def test_eviction_by_relevance(self):
        """Least relevant items should be evicted first."""
        from mycosoft_mas.consciousness.working_memory import WorkingMemory
        
        memory = WorkingMemory(capacity=2)
        
        await memory.add("Low relevance", "input", relevance=0.1)
        await memory.add("High relevance", "input", relevance=0.9)
        await memory.add("Medium relevance", "input", relevance=0.5)
        
        # Low relevance should be evicted
        contents = [item.content for item in memory._items]
        assert "Low relevance" not in contents
        assert "High relevance" in contents
    
    @pytest.mark.asyncio
    async def test_decay_relevance(self):
        """Item relevance should decay over time."""
        from mycosoft_mas.consciousness.working_memory import WorkingMemory
        
        memory = WorkingMemory()
        
        await memory.add("Test", "input", relevance=1.0)
        initial_relevance = memory._items[0].relevance
        
        # Apply decay
        await memory.decay()
        
        assert memory._items[0].relevance < initial_relevance
    
    @pytest.mark.asyncio
    async def test_get_context(self):
        """get_context should return relevant items."""
        from mycosoft_mas.consciousness.working_memory import WorkingMemory
        
        memory = WorkingMemory()
        
        await memory.add("Item 1", "input", relevance=0.8)
        await memory.add("Item 2", "context", relevance=0.6)
        
        context = await memory.get_context()
        
        assert len(context) > 0
        assert all(isinstance(item, dict) for item in context)
    
    def test_clear(self):
        """clear should remove all items."""
        from mycosoft_mas.consciousness.working_memory import WorkingMemory
        
        memory = WorkingMemory()
        memory._items = [object(), object()]  # Add mock items
        
        memory.clear()
        
        assert len(memory._items) == 0
    
    @pytest.mark.asyncio
    async def test_conversation_buffer(self):
        """Conversation buffer should track recent exchanges."""
        from mycosoft_mas.consciousness.working_memory import WorkingMemory
        
        memory = WorkingMemory()
        
        memory.add_to_conversation("user", "Hello")
        memory.add_to_conversation("assistant", "Hi there!")
        
        buffer = memory.get_conversation_buffer()
        
        assert len(buffer) == 2
        assert buffer[0]["role"] == "user"
        assert buffer[1]["role"] == "assistant"
