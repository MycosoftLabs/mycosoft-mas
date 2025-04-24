import pytest
from unittest.mock import Mock, patch
from mycosoft_mas.orchestrator import Orchestrator, MCPServer
from mycosoft_mas.agents.base_agent import BaseAgent
from mycosoft_mas.agents.messaging.message import Message, MessageType

@pytest.fixture
def mock_config():
    return {
        "name": "test_orchestrator",
        "host": "localhost",
        "port": 8000,
        "protocol": "http",
        "api_key": "test_key",
        "capabilities": ["test"],
        "backup_servers": [],
        "health_check_interval": 5,
        "retry_count": 3,
        "timeout": 10
    }

@pytest.fixture
def orchestrator(mock_config, tmp_path):
    config_file = tmp_path / "config.yaml"
    with open(config_file, "w") as f:
        import yaml
        yaml.dump({"orchestrator": mock_config}, f)
    return Orchestrator(str(config_file))

@pytest.fixture
def mock_agent():
    agent = Mock(spec=BaseAgent)
    agent.agent_id = "test_agent"
    agent.capabilities = ["test_capability"]
    return agent

@pytest.mark.asyncio
async def test_orchestrator_initialization(orchestrator):
    """Test that the orchestrator initializes correctly."""
    await orchestrator.initialize()
    assert orchestrator._config is not None
    assert orchestrator._agents == {}
    assert orchestrator._mcp_servers == {}

@pytest.mark.asyncio
async def test_add_agent(orchestrator, mock_agent):
    """Test adding an agent to the orchestrator."""
    await orchestrator.initialize()
    config = {
        "agent_id": mock_agent.agent_id,
        "type": "test",
        "capabilities": mock_agent.capabilities
    }
    with patch.object(orchestrator, '_create_agent', return_value=mock_agent):
        agent = await orchestrator.add_agent(config)
        assert agent.agent_id == mock_agent.agent_id
        assert agent.capabilities == mock_agent.capabilities

@pytest.mark.asyncio
async def test_remove_agent(orchestrator, mock_agent):
    """Test removing an agent from the orchestrator."""
    await orchestrator.initialize()
    config = {
        "agent_id": mock_agent.agent_id,
        "type": "test",
        "capabilities": mock_agent.capabilities
    }
    with patch.object(orchestrator, '_create_agent', return_value=mock_agent):
        await orchestrator.add_agent(config)
        await orchestrator.remove_agent(mock_agent.agent_id)
        assert mock_agent.agent_id not in orchestrator._agents

@pytest.mark.asyncio
async def test_handle_message(orchestrator, mock_agent):
    """Test handling a message."""
    await orchestrator.initialize()
    message = Message(
        type=MessageType.COMMAND,
        sender="test_sender",
        receiver="test_receiver",
        content={"command": "test"}
    )
    with patch.object(orchestrator, '_agents', {mock_agent.agent_id: mock_agent}):
        await orchestrator.handle_message(message)
        mock_agent.handle_message.assert_called_once_with(message)

@pytest.mark.asyncio
async def test_health_check(orchestrator):
    """Test health check functionality."""
    await orchestrator.initialize()
    health_status = await orchestrator.health_check()
    assert "status" in health_status
    assert "agent_count" in health_status
    assert "uptime" in health_status

@pytest.mark.asyncio
async def test_system_metrics(orchestrator):
    """Test getting system metrics."""
    await orchestrator.initialize()
    metrics = orchestrator.get_system_metrics()
    assert "agent_count" in metrics
    assert "active_agents" in metrics
    assert "memory_usage" in metrics 