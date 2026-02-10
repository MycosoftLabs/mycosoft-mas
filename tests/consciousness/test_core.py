"""
Tests for MYCAConsciousness Core

Tests the main consciousness class including:
- Singleton pattern
- Awaken/hibernate lifecycle
- Input processing pipeline
- Background task management

Author: Morgan Rockwell / MYCA
Created: February 10, 2026
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

# Module under test - we'll mock dependencies
import sys
sys.modules['mycosoft_mas.memory'] = MagicMock()
sys.modules['mycosoft_mas.memory.memory_coordinator'] = MagicMock()
sys.modules['mycosoft_mas.core.orchestrator_service'] = MagicMock()
sys.modules['mycosoft_mas.core.registry'] = MagicMock()


class TestMYCAConsciousnessSingleton:
    """Tests for singleton pattern."""
    
    def test_get_consciousness_returns_singleton(self):
        """get_consciousness should always return the same instance."""
        from mycosoft_mas.consciousness.core import get_consciousness, _consciousness_instance
        
        # Reset singleton for test
        import mycosoft_mas.consciousness.core as core_module
        core_module._consciousness_instance = None
        
        c1 = get_consciousness()
        c2 = get_consciousness()
        
        assert c1 is c2
    
    def test_consciousness_initial_state(self):
        """New consciousness should be in sleeping state."""
        from mycosoft_mas.consciousness.core import MYCAConsciousness
        
        consciousness = MYCAConsciousness()
        
        assert consciousness.is_conscious is False
        assert consciousness._awake is False


class TestConsciousnessLifecycle:
    """Tests for awaken/hibernate lifecycle."""
    
    @pytest.mark.asyncio
    async def test_awaken_sets_conscious_state(self):
        """awaken() should set consciousness to awake state."""
        from mycosoft_mas.consciousness.core import MYCAConsciousness
        
        consciousness = MYCAConsciousness()
        
        # Mock component initialization
        with patch.object(consciousness, '_initialize_components', new_callable=AsyncMock):
            with patch.object(consciousness, '_load_soul', new_callable=AsyncMock):
                with patch.object(consciousness, '_start_background_tasks', new_callable=AsyncMock):
                    await consciousness.awaken()
        
        assert consciousness.is_conscious is True
    
    @pytest.mark.asyncio
    async def test_hibernate_sets_sleeping_state(self):
        """hibernate() should set consciousness to sleeping state."""
        from mycosoft_mas.consciousness.core import MYCAConsciousness
        
        consciousness = MYCAConsciousness()
        consciousness._awake = True
        
        # Mock component initialization
        with patch.object(consciousness, '_stop_background_tasks', new_callable=AsyncMock):
            with patch.object(consciousness, '_save_state', new_callable=AsyncMock):
                await consciousness.hibernate()
        
        assert consciousness.is_conscious is False
    
    @pytest.mark.asyncio
    async def test_awaken_is_idempotent(self):
        """Calling awaken() multiple times should not cause issues."""
        from mycosoft_mas.consciousness.core import MYCAConsciousness
        
        consciousness = MYCAConsciousness()
        consciousness._awake = True
        
        # Should return early if already awake
        await consciousness.awaken()
        
        assert consciousness.is_conscious is True


class TestConsciousnessMetrics:
    """Tests for metrics tracking."""
    
    def test_metrics_initial_state(self):
        """Metrics should be zero initially."""
        from mycosoft_mas.consciousness.core import MYCAConsciousness
        
        consciousness = MYCAConsciousness()
        
        assert consciousness.metrics.thoughts_processed == 0
        assert consciousness.metrics.memories_recalled == 0
        assert consciousness.metrics.agents_delegated == 0


class TestConsciousnessProperties:
    """Tests for consciousness properties."""
    
    def test_is_conscious_property(self):
        """is_conscious should reflect _awake state."""
        from mycosoft_mas.consciousness.core import MYCAConsciousness
        
        consciousness = MYCAConsciousness()
        
        assert consciousness.is_conscious is False
        
        consciousness._awake = True
        assert consciousness.is_conscious is True
    
    def test_status_property(self):
        """status should return appropriate state string."""
        from mycosoft_mas.consciousness.core import MYCAConsciousness
        
        consciousness = MYCAConsciousness()
        
        assert consciousness.status == "sleeping"
        
        consciousness._awake = True
        # Status depends on various conditions
        assert consciousness.status in ["awake", "dreaming", "focused"]
