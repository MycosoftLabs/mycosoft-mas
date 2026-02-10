"""
Tests for Substrate Abstraction

Tests the digital and wetware substrate implementations.

Author: Morgan Rockwell / MYCA
Created: February 10, 2026
"""

import pytest
from unittest.mock import MagicMock


class TestSubstrateType:
    """Tests for SubstrateType enum."""
    
    def test_substrate_types_exist(self):
        """All substrate types should be defined."""
        from mycosoft_mas.consciousness.substrate import SubstrateType
        
        assert SubstrateType.DIGITAL is not None
        assert SubstrateType.WETWARE is not None
        assert SubstrateType.HYBRID is not None


class TestDigitalSubstrate:
    """Tests for DigitalSubstrate."""
    
    def test_digital_substrate_creation(self):
        """DigitalSubstrate should be creatable."""
        from mycosoft_mas.consciousness.substrate import DigitalSubstrate
        
        mock_consciousness = MagicMock()
        substrate = DigitalSubstrate(mock_consciousness)
        
        assert substrate is not None
    
    def test_digital_substrate_type(self):
        """DigitalSubstrate should report DIGITAL type."""
        from mycosoft_mas.consciousness.substrate import DigitalSubstrate, SubstrateType
        
        mock_consciousness = MagicMock()
        substrate = DigitalSubstrate(mock_consciousness)
        
        assert substrate.substrate_type == SubstrateType.DIGITAL
    
    @pytest.mark.asyncio
    async def test_digital_initialize(self):
        """DigitalSubstrate should initialize successfully."""
        from mycosoft_mas.consciousness.substrate import DigitalSubstrate
        
        mock_consciousness = MagicMock()
        substrate = DigitalSubstrate(mock_consciousness)
        
        result = await substrate.initialize()
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_digital_process(self):
        """DigitalSubstrate should process computations."""
        from mycosoft_mas.consciousness.substrate import DigitalSubstrate
        
        mock_consciousness = MagicMock()
        substrate = DigitalSubstrate(mock_consciousness)
        await substrate.initialize()
        
        result = await substrate.process({"type": "test", "data": "hello"})
        
        assert "status" in result
    
    @pytest.mark.asyncio
    async def test_digital_store_retrieve(self):
        """DigitalSubstrate should store and retrieve data."""
        from mycosoft_mas.consciousness.substrate import DigitalSubstrate
        
        mock_consciousness = MagicMock()
        substrate = DigitalSubstrate(mock_consciousness)
        await substrate.initialize()
        
        await substrate.store("test_key", {"value": 123})
        result = await substrate.retrieve("test_key")
        
        assert result is not None


class TestWetwareSubstrate:
    """Tests for WetwareSubstrate (future implementation)."""
    
    def test_wetware_substrate_creation(self):
        """WetwareSubstrate should be creatable."""
        from mycosoft_mas.consciousness.substrate import WetwareSubstrate
        
        mock_consciousness = MagicMock()
        substrate = WetwareSubstrate(mock_consciousness)
        
        assert substrate is not None
    
    def test_wetware_substrate_type(self):
        """WetwareSubstrate should report WETWARE type."""
        from mycosoft_mas.consciousness.substrate import WetwareSubstrate, SubstrateType
        
        mock_consciousness = MagicMock()
        substrate = WetwareSubstrate(mock_consciousness)
        
        assert substrate.substrate_type == SubstrateType.WETWARE
    
    @pytest.mark.asyncio
    async def test_wetware_initialize_not_ready(self):
        """WetwareSubstrate should indicate not ready (stub)."""
        from mycosoft_mas.consciousness.substrate import WetwareSubstrate
        
        mock_consciousness = MagicMock()
        substrate = WetwareSubstrate(mock_consciousness)
        
        result = await substrate.initialize()
        
        # Wetware is a future stub, should return False
        assert result is False


class TestCreateSubstrate:
    """Tests for substrate factory function."""
    
    def test_create_digital_substrate(self):
        """create_substrate should create DigitalSubstrate by default."""
        from mycosoft_mas.consciousness.substrate import create_substrate, DigitalSubstrate, SubstrateType
        
        mock_consciousness = MagicMock()
        substrate = create_substrate(mock_consciousness)
        
        assert isinstance(substrate, DigitalSubstrate)
    
    def test_create_wetware_substrate(self):
        """create_substrate should create WetwareSubstrate when specified."""
        from mycosoft_mas.consciousness.substrate import create_substrate, WetwareSubstrate, SubstrateType
        
        mock_consciousness = MagicMock()
        substrate = create_substrate(mock_consciousness, SubstrateType.WETWARE)
        
        assert isinstance(substrate, WetwareSubstrate)
    
    def test_create_hybrid_substrate(self):
        """create_substrate should create HybridSubstrate when specified."""
        from mycosoft_mas.consciousness.substrate import create_substrate, HybridSubstrate, SubstrateType
        
        mock_consciousness = MagicMock()
        substrate = create_substrate(mock_consciousness, SubstrateType.HYBRID)
        
        assert isinstance(substrate, HybridSubstrate)
