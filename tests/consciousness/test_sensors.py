"""
Tests for World Sensors

Tests all sensor implementations.

Author: Morgan Rockwell / MYCA
Created: February 10, 2026
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestBaseSensor:
    """Tests for BaseSensor abstract class."""
    
    def test_base_sensor_is_abstract(self):
        """BaseSensor should not be directly instantiable."""
        from mycosoft_mas.consciousness.sensors.base_sensor import BaseSensor
        
        with pytest.raises(TypeError):
            BaseSensor()


class TestCREPSensor:
    """Tests for CREPSensor."""
    
    def test_crep_sensor_initialization(self):
        """CREPSensor should initialize."""
        from mycosoft_mas.consciousness.sensors.crep_sensor import CREPSensor
        
        sensor = CREPSensor()
        
        assert sensor.name == "crep"
        assert sensor.status == "disconnected"
    
    @pytest.mark.asyncio
    async def test_crep_connect_failure_graceful(self):
        """CREPSensor should handle connection failure gracefully."""
        from mycosoft_mas.consciousness.sensors.crep_sensor import CREPSensor
        
        sensor = CREPSensor()
        
        # Mock HTTP client to fail
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.get.side_effect = Exception("Connection failed")
            
            result = await sensor.connect()
        
        # Should return False on failure, not raise
        assert result is False or sensor.status == "error"
    
    def test_crep_sensor_endpoints(self):
        """CREPSensor should have valid endpoints defined."""
        from mycosoft_mas.consciousness.sensors.crep_sensor import CREPSensor
        
        sensor = CREPSensor()
        
        assert hasattr(sensor, 'MAS_API') or hasattr(sensor, 'CREP_API')


class TestEarth2Sensor:
    """Tests for Earth2Sensor."""
    
    def test_earth2_sensor_initialization(self):
        """Earth2Sensor should initialize."""
        from mycosoft_mas.consciousness.sensors.earth2_sensor import Earth2Sensor
        
        sensor = Earth2Sensor()
        
        assert sensor.name == "earth2"
    
    @pytest.mark.asyncio
    async def test_earth2_read_empty_on_disconnect(self):
        """Earth2Sensor should return empty dict when disconnected."""
        from mycosoft_mas.consciousness.sensors.earth2_sensor import Earth2Sensor
        
        sensor = Earth2Sensor()
        sensor._connected = False
        
        data = await sensor.read()
        
        assert data == {} or data is None


class TestNatureOSSensor:
    """Tests for NatureOSSensor."""
    
    def test_natureos_sensor_initialization(self):
        """NatureOSSensor should initialize."""
        from mycosoft_mas.consciousness.sensors.natureos_sensor import NatureOSSensor
        
        sensor = NatureOSSensor()
        
        assert sensor.name == "natureos"


class TestMINDEXSensor:
    """Tests for MINDEXSensor."""
    
    def test_mindex_sensor_initialization(self):
        """MINDEXSensor should initialize."""
        from mycosoft_mas.consciousness.sensors.mindex_sensor import MINDEXSensor
        
        sensor = MINDEXSensor()
        
        assert sensor.name == "mindex"
    
    @pytest.mark.asyncio
    async def test_mindex_search(self):
        """MINDEXSensor should have search method."""
        from mycosoft_mas.consciousness.sensors.mindex_sensor import MINDEXSensor
        
        sensor = MINDEXSensor()
        
        assert hasattr(sensor, 'search')


class TestMycoBrainSensor:
    """Tests for MycoBrainSensor."""
    
    def test_mycobrain_sensor_initialization(self):
        """MycoBrainSensor should initialize."""
        from mycosoft_mas.consciousness.sensors.mycobrain_sensor import MycoBrainSensor
        
        sensor = MycoBrainSensor()
        
        assert sensor.name == "mycobrain"
