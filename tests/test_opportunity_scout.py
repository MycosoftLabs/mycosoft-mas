"""
Tests for the OpportunityScout agent.
"""

import asyncio
import json
import os
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from mycosoft_mas.agents.opportunity_scout import OpportunityScout

@pytest.fixture
def mock_config():
    """Create a mock configuration for testing."""
    return {
        "agent_id": "opportunity_scout",
        "name": "Opportunity Scout Agent",
        "data_dir": "test_data/opportunities",
        "output_dir": "test_output/opportunities",
        "data_sources": [
            {
                "name": "SAM.gov",
                "url": "https://sam.gov/api/prod/sgs/v1/search/",
                "refresh_rate": "1h"
            }
        ],
        "keywords": {
            "primary": ["installation resilience", "mesh sensor"],
            "secondary": ["sensor network", "force health"]
        },
        "notifications": {
            "slack": {
                "channel": "#test-capture",
                "threshold": "high_priority"
            }
        }
    }

@pytest.fixture
def mock_opportunity_data():
    """Create mock opportunity data for testing."""
    return {
        "opportunities": [
            {
                "title": "Installation Resilience Sensor Network",
                "description": "Seeking innovative solutions for mesh sensor networks to enhance installation resilience and force health monitoring.",
                "url": "https://example.com/opportunity/1"
            },
            {
                "title": "Environmental Monitoring System",
                "description": "Standard environmental monitoring system procurement.",
                "url": "https://example.com/opportunity/2"
            }
        ]
    }

@pytest.mark.asyncio
async def test_opportunity_scout_initialization(mock_config):
    """Test agent initialization."""
    agent = OpportunityScout(mock_config)
    await agent.initialize()
    
    assert agent.status.value == "running"
    assert Path(mock_config["data_dir"]).exists()
    assert len(agent.primary_keywords) == 2
    assert len(agent.secondary_keywords) == 2

@pytest.mark.asyncio
async def test_filter_opportunities(mock_config, mock_opportunity_data):
    """Test opportunity filtering logic."""
    agent = OpportunityScout(mock_config)
    await agent.initialize()
    
    filtered = agent.filter_opportunities(mock_opportunity_data)
    assert len(filtered) == 1
    assert filtered[0]["title"] == "Installation Resilience Sensor Network"

@pytest.mark.asyncio
async def test_high_priority_detection(mock_config):
    """Test high priority opportunity detection."""
    agent = OpportunityScout(mock_config)
    await agent.initialize()
    
    high_priority_opp = {
        "title": "Installation Resilience Mesh Sensor Network",
        "description": "Critical need for mesh sensor network to enhance installation resilience and force health monitoring."
    }
    
    low_priority_opp = {
        "title": "Standard Sensor Network",
        "description": "Basic sensor network procurement."
    }
    
    assert agent.is_high_priority(high_priority_opp) is True
    assert agent.is_high_priority(low_priority_opp) is False

@pytest.mark.asyncio
async def test_process_opportunities(mock_config, mock_opportunity_data):
    """Test opportunity processing and storage."""
    agent = OpportunityScout(mock_config)
    await agent.initialize()
    
    # Mock message broker
    agent.message_broker.send_message = AsyncMock()
    
    await agent.process_opportunities(
        mock_opportunity_data["opportunities"],
        "SAM.gov"
    )
    
    # Check if file was created
    output_files = list(Path(mock_config["data_dir"]).glob("SAM.gov_*.json"))
    assert len(output_files) == 1
    
    # Check file contents
    with open(output_files[0]) as f:
        saved_data = json.load(f)
        assert len(saved_data) == 2
    
    # Check if notification was sent
    agent.message_broker.send_message.assert_called_once()

@pytest.mark.asyncio
async def test_scan_source(mock_config):
    """Test source scanning functionality."""
    agent = OpportunityScout(mock_config)
    await agent.initialize()
    
    # Mock aiohttp response
    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value={"opportunities": []})
    
    with patch("aiohttp.ClientSession") as mock_session:
        mock_session.return_value.__aenter__.return_value.get.return_value.__aenter__.return_value = mock_response
        
        await agent.scan_source(mock_config["data_sources"][0])
        
        # Verify session was created and request was made
        mock_session.assert_called_once()
        mock_session.return_value.__aenter__.return_value.get.assert_called_once_with(
            mock_config["data_sources"][0]["url"]
        )

@pytest.mark.asyncio
async def test_error_handling(mock_config):
    """Test error handling in the agent."""
    agent = OpportunityScout(mock_config)
    await agent.initialize()
    
    # Mock error logging service
    agent.error_logging_service.log_error = AsyncMock()
    
    # Test error in scan_source
    with patch("aiohttp.ClientSession") as mock_session:
        mock_session.side_effect = Exception("Test error")
        
        await agent.scan_source(mock_config["data_sources"][0])
        
        # Verify error was logged
        agent.error_logging_service.log_error.assert_called_once() 