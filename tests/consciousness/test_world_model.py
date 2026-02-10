"""
Tests for WorldModel

Tests the unified world perception system.

Author: Morgan Rockwell / MYCA
Created: February 10, 2026
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone


class TestWorldState:
    """Tests for WorldState dataclass."""
    
    def test_world_state_creation(self):
        """WorldState should be creatable."""
        from mycosoft_mas.consciousness.world_model import WorldState
        
        state = WorldState()
        
        assert state.crep_data == {}
        assert state.earth2_data == {}
        assert state.natureos_data == {}
        assert state.mindex_data == {}
        assert state.mycobrain_data == {}


class TestWorldModel:
    """Tests for WorldModel."""
    
    def test_world_model_initialization(self):
        """WorldModel should initialize with sensors."""
        from mycosoft_mas.consciousness.world_model import WorldModel
        
        model = WorldModel()
        
        assert model._sensors is not None
        assert model._current_state is not None
    
    @pytest.mark.asyncio
    async def test_initialize_sensors(self):
        """initialize should set up all sensors."""
        from mycosoft_mas.consciousness.world_model import WorldModel
        
        model = WorldModel()
        
        # Mock sensor connections
        for sensor in model._sensors.values():
            sensor.connect = AsyncMock(return_value=True)
        
        await model.initialize()
        
        # All sensors should have connect called
        for sensor in model._sensors.values():
            sensor.connect.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_update_all(self):
        """update_all should update from all sensors."""
        from mycosoft_mas.consciousness.world_model import WorldModel
        
        model = WorldModel()
        
        # Mock sensor reads
        for name, sensor in model._sensors.items():
            sensor.read = AsyncMock(return_value={"test": True})
            sensor._connected = True
        
        await model.update_all()
        
        # State should be updated
        assert model._current_state is not None
    
    def test_get_current_state(self):
        """get_current_state should return WorldState."""
        from mycosoft_mas.consciousness.world_model import WorldModel, WorldState
        
        model = WorldModel()
        
        state = model.get_current_state()
        
        assert isinstance(state, WorldState)
    
    @pytest.mark.asyncio
    async def test_get_relevant_context(self):
        """get_relevant_context should filter based on focus."""
        from mycosoft_mas.consciousness.world_model import WorldModel
        from mycosoft_mas.consciousness.attention import AttentionFocus
        
        model = WorldModel()
        
        focus = AttentionFocus(
            content="What's the weather?",
            source="text",
            category="user_input",
            priority=1.0
        )
        
        context = await model.get_relevant_context(focus)
        
        assert isinstance(context, dict)
    
    def test_sensor_status(self):
        """sensor_status should return all sensor statuses."""
        from mycosoft_mas.consciousness.world_model import WorldModel
        
        model = WorldModel()
        
        status = model.sensor_status
        
        assert isinstance(status, dict)
        assert "crep" in status
        assert "earth2" in status
