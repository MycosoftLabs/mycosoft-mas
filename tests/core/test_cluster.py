import pytest
from unittest.mock import Mock, patch
from mycosoft_mas.core.cluster import Cluster
from mycosoft_mas.agents.base_agent import BaseAgent

@pytest.fixture
def cluster():
    return Cluster()

@pytest.fixture
def mock_agent():
    agent = Mock(spec=BaseAgent)
    agent.agent_id = "test_agent"
    agent.capabilities = ["test_capability"]
    return agent

def test_cluster_initialization(cluster):
    assert cluster.nodes == []
    assert cluster.node_count == 0
    assert cluster.active_nodes == 0
    assert cluster.status == "stopped"

def test_add_node(cluster, mock_agent):
    cluster.add_node(mock_agent)
    assert mock_agent in cluster.nodes
    assert cluster.node_count == 1
    assert cluster.active_nodes == 1
    assert cluster.status == "running"

def test_remove_node(cluster, mock_agent):
    cluster.add_node(mock_agent)
    cluster.remove_node(mock_agent.agent_id)
    assert mock_agent not in cluster.nodes
    assert cluster.node_count == 0
    assert cluster.active_nodes == 0
    assert cluster.status == "stopped"

def test_get_node(cluster, mock_agent):
    cluster.add_node(mock_agent)
    node = cluster.get_node(mock_agent.agent_id)
    assert node == mock_agent

def test_get_status(cluster, mock_agent):
    cluster.add_node(mock_agent)
    status = cluster.get_status()
    assert status["status"] == "running"
    assert status["node_count"] == 1
    assert status["active_nodes"] == 1

def test_restart(cluster, mock_agent):
    cluster.add_node(mock_agent)
    cluster.restart()
    assert cluster.status == "running"
    assert cluster.active_nodes == 1

def test_stop(cluster, mock_agent):
    cluster.add_node(mock_agent)
    cluster.stop()
    assert cluster.status == "stopped"
    assert cluster.active_nodes == 0

def test_start(cluster, mock_agent):
    cluster.add_node(mock_agent)
    cluster.stop()
    cluster.start()
    assert cluster.status == "running"
    assert cluster.active_nodes == 1

def test_distribute_task(cluster, mock_agent):
    cluster.add_node(mock_agent)
    task = {"type": "test_task", "data": "test_data"}
    cluster.distribute_task(task)
    mock_agent.process_task.assert_called_once_with(task)

def test_get_node_status(cluster, mock_agent):
    cluster.add_node(mock_agent)
    mock_agent.get_status.return_value = {
        "status": "running",
        "capabilities": ["test_capability"],
        "task_count": 0
    }
    status = cluster.get_node_status(mock_agent.agent_id)
    assert status["status"] == "running"
    assert status["capabilities"] == ["test_capability"]
    assert status["task_count"] == 0

def test_handle_node_failure(cluster, mock_agent):
    cluster.add_node(mock_agent)
    cluster.handle_node_failure(mock_agent.agent_id)
    assert mock_agent not in cluster.nodes
    assert cluster.node_count == 0
    assert cluster.active_nodes == 0
    assert cluster.status == "stopped" 