"""
Tests for the BaseAgent class.
"""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from mycosoft_mas.agents.base_agent import BaseAgent
from mycosoft_mas.agents.mycology_bio_agent import MycologyBioAgent
from mycosoft_mas.agents.finance_admin_agent import FinanceAdminAgent
from mycosoft_mas.agents.marketing_agent import MarketingAgent
from mycosoft_mas.agents.project_manager_agent import ProjectManagerAgent
from mycosoft_mas.agents.myco_dao_agent import MycoDAOAgent
from mycosoft_mas.agents.enums.agent_status import AgentStatus

@pytest.fixture
def base_agent():
    """Create a base agent instance."""
    return BaseAgent(
        agent_id="test_agent",
        name="Test Agent",
        config={
            "health_check_interval": 60,
            "retry_interval": 300,
            "max_retries": 3
        }
    )

@pytest.fixture
def mycology_bio_agent():
    config = {
        "health_check_interval": 1,
        "retry_interval": 1,
        "max_retries": 3,
        "agent_id": "mycology_bio",
        "name": "Mycology BioAgent"
    }
    return MycologyBioAgent(
        agent_id="mycology_bio",
        name="Mycology BioAgent",
        config=config
    )

@pytest.fixture
def finance_admin_agent():
    config = {
        "health_check_interval": 1,
        "retry_interval": 1,
        "max_retries": 3,
        "agent_id": "finance_admin",
        "name": "Finance Admin Agent"
    }
    return FinanceAdminAgent(config)

@pytest.fixture
def marketing_agent():
    config = {
        "health_check_interval": 1,
        "retry_interval": 1,
        "max_retries": 3,
        "agent_id": "marketing",
        "name": "Marketing Agent"
    }
    return MarketingAgent(
        agent_id="marketing",
        name="Marketing Agent",
        config=config
    )

@pytest.fixture
def project_manager_agent():
    config = {
        "health_check_interval": 1,
        "retry_interval": 1,
        "max_retries": 3,
        "agent_id": "project_manager",
        "name": "Project Manager Agent"
    }
    return ProjectManagerAgent(
        agent_id="project_manager",
        name="Project Manager Agent",
        config=config
    )

@pytest.fixture
def myco_dao_agent():
    config = {
        "health_check_interval": 1,
        "retry_interval": 1,
        "max_retries": 3,
        "agent_id": "myco_dao",
        "name": "MycoDAO Agent"
    }
    return MycoDAOAgent(
        agent_id="myco_dao",
        name="MycoDAO Agent",
        config=config
    )

@pytest.mark.asyncio
async def test_agent_initialization(base_agent):
    """Test agent initialization."""
    assert base_agent.agent_id == "test_agent"
    assert base_agent.name == "Test Agent"
    assert base_agent.status == AgentStatus.INITIALIZING
    assert base_agent.is_running == False
    assert base_agent.metrics["tasks_processed"] == 0
    assert base_agent.metrics["errors_handled"] == 0
    assert base_agent.metrics["last_health_check"] == None
    assert base_agent.metrics["uptime"] == 0
    assert base_agent.metrics["start_time"] == None

@pytest.mark.asyncio
async def test_health_check(base_agent):
    """Test health check functionality."""
    with patch.object(base_agent, '_check_services_health', new_callable=AsyncMock) as mock_services:
        with patch.object(base_agent, '_check_resource_usage', new_callable=AsyncMock) as mock_resources:
            mock_services.return_value = {"service": "healthy"}
            mock_resources.return_value = {"cpu": 0.5, "memory": 0.3}
            
            health_status = await base_agent.health_check()
            
            assert health_status["agent_id"] == "test_agent"
            assert health_status["name"] == "Test Agent"
            assert health_status["status"] == AgentStatus.INITIALIZING.value
            assert health_status["is_running"] == False
            assert "metrics" in health_status
            assert "queue_sizes" in health_status
            assert health_status["service_health"] == {"service": "healthy"}
            assert health_status["resource_usage"] == {"cpu": 0.5, "memory": 0.3}
            assert "timestamp" in health_status

@pytest.mark.asyncio
async def test_process_task(base_agent):
    """Test task processing."""
    task = {
        "type": "test_task",
        "id": "task_123",
        "payload": {"data": "test"}
    }
    
    with patch.object(base_agent, '_handle_task', new_callable=AsyncMock) as mock_handle:
        mock_handle.return_value = {"result": "success"}
        
        result = await base_agent.process_task(task)
        
        assert result["success"] == True
        assert result["task_id"] == "task_123"
        assert result["result"] == {"result": "success"}
        assert base_agent.metrics["tasks_processed"] == 1

@pytest.mark.asyncio
async def test_handle_error(base_agent):
    """Test error handling."""
    error = {
        "type": "test_error",
        "id": "error_123",
        "error": "Test error message"
    }
    
    with patch.object(base_agent, '_handle_error_type', new_callable=AsyncMock) as mock_handle:
        mock_handle.return_value = {"resolution": "fixed"}
        
        result = await base_agent.handle_error(error)
        
        assert result["success"] == True
        assert result["error_id"] == "error_123"
        assert result["result"] == {"resolution": "fixed"}
        assert base_agent.metrics["errors_handled"] == 1

@pytest.mark.asyncio
async def test_background_tasks(base_agent):
    """Test background task management."""
    with patch.object(base_agent, '_monitor_health', new_callable=AsyncMock) as mock_health:
        with patch.object(base_agent, '_process_tasks', new_callable=AsyncMock) as mock_tasks:
            with patch.object(base_agent, '_handle_errors', new_callable=AsyncMock) as mock_errors:
                with patch.object(base_agent, '_process_notifications', new_callable=AsyncMock) as mock_notifications:
                    await base_agent._start_background_tasks()
                    
                    assert len(base_agent.background_tasks) == 4
                    assert all(isinstance(task, asyncio.Task) for task in base_agent.background_tasks)

@pytest.mark.asyncio
async def test_not_implemented_methods(base_agent):
    """Test that abstract methods raise NotImplementedError."""
    with pytest.raises(NotImplementedError):
        await base_agent._handle_task("test", {})
    
    with pytest.raises(NotImplementedError):
        await base_agent._handle_error_type("test", "error")
    
    with pytest.raises(NotImplementedError):
        await base_agent._handle_notification({})
    
    with pytest.raises(NotImplementedError):
        await base_agent._check_services_health()
    
    with pytest.raises(NotImplementedError):
        await base_agent._check_resource_usage()
    
    with pytest.raises(NotImplementedError):
        await base_agent._initialize_services()

@pytest.mark.asyncio
async def test_base_agent_start_stop(base_agent):
    """Test agent start and stop functionality."""
    with patch.object(base_agent, '_initialize_services', new_callable=AsyncMock) as mock_init:
        with patch.object(base_agent, '_start_background_tasks', new_callable=AsyncMock) as mock_start:
            # Test initialization
            result = await base_agent.initialize()
            assert result == True
            assert base_agent.status == AgentStatus.ACTIVE
            assert base_agent.is_running == True
            assert base_agent.metrics["start_time"] is not None
            
            # Test stop
            result = await base_agent.stop()
            assert result == True
            assert base_agent.status == AgentStatus.SHUTDOWN
            assert base_agent.is_running == False
            assert len(base_agent.background_tasks) == 0

@pytest.mark.asyncio
async def test_mycology_bio_agent_initialization(mycology_bio_agent):
    assert mycology_bio_agent.agent_id == "mycology_bio"
    assert mycology_bio_agent.name == "Mycology BioAgent"
    assert mycology_bio_agent.status == AgentStatus.INITIALIZING
    assert not mycology_bio_agent.is_running

@pytest.mark.asyncio
async def test_finance_admin_agent_initialization(finance_admin_agent):
    """Test Finance Admin agent initialization."""
    assert finance_admin_agent.agent_id == "finance_admin"
    assert finance_admin_agent.name == "Finance Admin Agent"
    assert finance_admin_agent.status == AgentStatus.INITIALIZING
    assert finance_admin_agent.is_running == False

@pytest.mark.asyncio
async def test_marketing_agent_initialization(marketing_agent):
    assert marketing_agent.agent_id == "marketing"
    assert marketing_agent.name == "Marketing Agent"
    assert marketing_agent.status == AgentStatus.INITIALIZING
    assert not marketing_agent.is_running

@pytest.mark.asyncio
async def test_project_manager_agent_initialization(project_manager_agent):
    assert project_manager_agent.agent_id == "project_manager"
    assert project_manager_agent.name == "Project Manager Agent"
    assert project_manager_agent.status == AgentStatus.INITIALIZING
    assert not project_manager_agent.is_running

@pytest.mark.asyncio
async def test_myco_dao_agent_initialization(myco_dao_agent):
    """Test MycoDAO agent initialization."""
    assert myco_dao_agent.agent_id == "myco_dao"
    assert myco_dao_agent.name == "MycoDAO Agent"
    assert myco_dao_agent.status == AgentStatus.INITIALIZING
    assert myco_dao_agent.is_running == False 