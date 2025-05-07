import pytest
from unittest.mock import Mock, patch
from mycosoft_mas.core.task_manager import TaskManager
from mycosoft_mas.agents.base_agent import BaseAgent
from mycosoft_mas.orchestrator import Orchestrator
from mycosoft_mas.core.cluster import Cluster

@pytest.fixture
def task_manager():
    return TaskManager()

@pytest.fixture
def mock_agent():
    agent = Mock(spec=BaseAgent)
    agent.agent_id = "test_agent"
    agent.capabilities = ["test_capability"]
    return agent

@pytest.fixture
def mock_orchestrator():
    orchestrator = Mock(spec=Orchestrator)
    orchestrator.get_status.return_value = {
        "status": "running",
        "agent_count": 1,
        "task_queue_size": 0
    }
    return orchestrator

@pytest.fixture
def mock_cluster():
    cluster = Mock(spec=Cluster)
    cluster.get_status.return_value = {
        "status": "running",
        "node_count": 1,
        "active_nodes": 1
    }
    return cluster

def test_task_manager_initialization(task_manager):
    assert task_manager.tasks == []
    assert task_manager.task_history == []
    assert task_manager.task_metrics == {}
    assert task_manager.orchestrator_client is None
    assert task_manager.cluster_manager is None

def test_load_config(task_manager):
    config = {
        "orchestrator": {
            "url": "http://localhost:8000",
            "monitoring_interval": 60
        },
        "clusters": {
            "monitoring_interval": 60
        },
        "dependencies": {
            "auto_update": True,
            "update_interval": 3600
        }
    }
    task_manager.load_config(config)
    assert task_manager.config == config

def test_initialize_orchestrator_client(task_manager, mock_orchestrator):
    with patch('mycosoft_mas.orchestrator.Orchestrator', return_value=mock_orchestrator):
        task_manager.initialize_orchestrator_client()
        assert task_manager.orchestrator_client is not None

def test_initialize_cluster_manager(task_manager, mock_cluster):
    with patch('mycosoft_mas.core.cluster.Cluster', return_value=mock_cluster):
        task_manager.initialize_cluster_manager()
        assert task_manager.cluster_manager is not None

def test_get_orchestrator_status(task_manager, mock_orchestrator):
    task_manager.orchestrator_client = mock_orchestrator
    status = task_manager._get_orchestrator_status()
    assert status["status"] == "running"
    assert status["agent_count"] == 1
    assert status["task_queue_size"] == 0

def test_get_clusters(task_manager, mock_cluster):
    task_manager.cluster_manager = mock_cluster
    clusters = task_manager._get_clusters()
    assert len(clusters) == 1
    assert clusters[0]["status"] == "running"
    assert clusters[0]["node_count"] == 1
    assert clusters[0]["active_nodes"] == 1

def test_get_dependencies(task_manager):
    with patch('subprocess.run') as mock_run:
        mock_run.return_value.stdout = "Package Version\nnumpy 1.24.3\npandas 2.0.3"
        dependencies = task_manager._get_dependencies()
        assert "numpy" in dependencies
        assert "pandas" in dependencies
        assert dependencies["numpy"] == "1.24.3"
        assert dependencies["pandas"] == "2.0.3"

def test_restart_orchestrator(task_manager, mock_orchestrator):
    task_manager.orchestrator_client = mock_orchestrator
    task_manager.restart_orchestrator()
    mock_orchestrator.restart.assert_called_once()

def test_restart_clusters(task_manager, mock_cluster):
    task_manager.cluster_manager = mock_cluster
    task_manager.restart_clusters()
    mock_cluster.restart.assert_called_once()

def test_update_dependencies(task_manager):
    with patch('subprocess.run') as mock_run:
        mock_run.return_value.returncode = 0
        result = task_manager.update_dependencies()
        assert result["status"] == "success"
        mock_run.assert_called_with(
            ["poetry", "update"],
            capture_output=True,
            text=True
        )

def test_monitoring_loop(task_manager, mock_orchestrator, mock_cluster):
    task_manager.orchestrator_client = mock_orchestrator
    task_manager.cluster_manager = mock_cluster
    task_manager.config = {
        "orchestrator": {"monitoring_interval": 0.1},
        "clusters": {"monitoring_interval": 0.1},
        "dependencies": {"auto_update": True, "update_interval": 0.1}
    }
    
    with patch.object(task_manager, '_get_orchestrator_status') as mock_orch_status:
        with patch.object(task_manager, '_get_clusters') as mock_clusters:
            with patch.object(task_manager, '_get_dependencies') as mock_deps:
                mock_orch_status.return_value = {"status": "running"}
                mock_clusters.return_value = [{"status": "running"}]
                mock_deps.return_value = {"numpy": "1.24.3"}
                
                task_manager.start_monitoring()
                task_manager.stop_monitoring()
                
                assert mock_orch_status.called
                assert mock_clusters.called
                assert mock_deps.called 