import pytest
import asyncio
from unittest.mock import Mock, patch
from mycosoft_mas.agents.base_agent import BaseAgent
from mycosoft_mas.core.agent_manager import AgentManager
from mycosoft_mas.core.task_manager import TaskManager
from mycosoft_mas.core.metrics_collector import MetricsCollector
from mycosoft_mas.orchestrator import Orchestrator
from mycosoft_mas.core.cluster import Cluster
from mycosoft_mas.services.integration_service import IntegrationService

@pytest.fixture
def event_loop():
    """Create an instance of the default event loop for each test case."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def mock_agent():
    agent = Mock(spec=BaseAgent)
    agent.agent_id = "test_agent"
    agent.capabilities = ["test_capability"]
    agent.status = "running"
    agent.get_status.return_value = {
        "status": "running",
        "capabilities": ["test_capability"],
        "task_count": 0
    }
    return agent

@pytest.fixture
def orchestrator():
    """Create a new orchestrator instance for testing."""
    return Orchestrator()

@pytest.fixture
def cluster():
    """Create a new cluster instance for testing."""
    return Cluster("test_cluster", "Test Cluster")

@pytest.fixture
def integration_service():
    """Create an integration service instance for testing."""
    config = {
        "data_dir": "test_data",
        "websocket_host": "localhost",
        "websocket_port": 8765,
        "metrics_interval": 1.0
    }
    return IntegrationService(config)

@pytest.fixture
def mock_agent_manager():
    manager = Mock(spec=AgentManager)
    manager.get_status.return_value = {
        "status": "running",
        "agent_count": 1,
        "task_queue_size": 0
    }
    return manager

@pytest.fixture
def mock_task_manager():
    manager = Mock(spec=TaskManager)
    manager.get_status.return_value = {
        "status": "running",
        "tasks_pending": 0,
        "tasks_completed": 0
    }
    return manager

@pytest.fixture
def mock_metrics_collector():
    collector = Mock(spec=MetricsCollector)
    collector.get_status.return_value = {
        "status": "running",
        "metrics": {},
        "alerts": []
    }
    return collector

@pytest.fixture
def mock_task():
    return {
        "type": "test_task",
        "data": "test_data",
        "priority": "high",
        "timestamp": "2024-04-19T00:00:00Z"
    }

@pytest.fixture
def mock_config():
    return {
        "agent_manager": {
            "url": "http://localhost:8000",
            "monitoring_interval": 60
        },
        "task_manager": {
            "monitoring_interval": 60
        },
        "monitoring": {
            "enabled": True,
            "alert_threshold": 80
        },
        "security": {
            "enabled": True,
            "auth_timeout": 3600
        },
        "dependencies": {
            "auto_update": True,
            "update_interval": 3600
        },
        "data_dir": "test_data",
        "websocket_host": "localhost",
        "websocket_port": 8765,
        "metrics_interval": 1.0
    }

@pytest.fixture(autouse=True)
def setup_test_env(tmp_path):
    """Set up the test environment."""
    # Create test data directory
    test_data_dir = tmp_path / "test_data"
    test_data_dir.mkdir(exist_ok=True)
    
    # Set up environment variables
    with patch.dict('os.environ', {
        'MAS_DATA_DIR': str(test_data_dir),
        'MAS_ENV': 'test'
    }):
        yield 