import pytest
from unittest.mock import Mock, patch
from mycosoft_mas.main import MASApplication
from mycosoft_mas.core.agent import BaseAgent
from mycosoft_mas.core.orchestrator import Orchestrator
from mycosoft_mas.core.cluster import Cluster
from mycosoft_mas.services.monitoring import MonitoringService
from mycosoft_mas.services.security import SecurityService

@pytest.fixture
def mas_application():
    return MASApplication()

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

@pytest.fixture
def mock_monitoring_service():
    service = Mock(spec=MonitoringService)
    service.get_status.return_value = {
        "status": "running",
        "metrics": {},
        "alerts": []
    }
    return service

@pytest.fixture
def mock_security_service():
    service = Mock(spec=SecurityService)
    service.get_status.return_value = {
        "status": "running",
        "authenticated_agents": 1,
        "security_events": 0
    }
    return service

def test_mas_application_initialization(mas_application):
    assert mas_application.orchestrator is None
    assert mas_application.clusters == []
    assert mas_application.monitoring_service is None
    assert mas_application.security_service is None
    assert mas_application.is_running is False

def test_initialize_services(mas_application, mock_orchestrator, mock_monitoring_service, mock_security_service):
    with patch('mycosoft_mas.core.orchestrator.Orchestrator', return_value=mock_orchestrator):
        with patch('mycosoft_mas.services.monitoring.MonitoringService', return_value=mock_monitoring_service):
            with patch('mycosoft_mas.services.security.SecurityService', return_value=mock_security_service):
                mas_application.initialize_services()
                assert mas_application.orchestrator is not None
                assert mas_application.monitoring_service is not None
                assert mas_application.security_service is not None

def test_add_cluster(mas_application, mock_cluster):
    with patch('mycosoft_mas.core.cluster.Cluster', return_value=mock_cluster):
        mas_application.add_cluster("test_cluster")
        assert len(mas_application.clusters) == 1
        assert mas_application.clusters[0].get_status()["status"] == "running"

def test_remove_cluster(mas_application, mock_cluster):
    with patch('mycosoft_mas.core.cluster.Cluster', return_value=mock_cluster):
        mas_application.add_cluster("test_cluster")
        mas_application.remove_cluster("test_cluster")
        assert len(mas_application.clusters) == 0

def test_start_application(mas_application, mock_orchestrator, mock_monitoring_service, mock_security_service):
    with patch('mycosoft_mas.core.orchestrator.Orchestrator', return_value=mock_orchestrator):
        with patch('mycosoft_mas.services.monitoring.MonitoringService', return_value=mock_monitoring_service):
            with patch('mycosoft_mas.services.security.SecurityService', return_value=mock_security_service):
                mas_application.initialize_services()
                mas_application.start()
                assert mas_application.is_running is True
                mock_orchestrator.start.assert_called_once()
                mock_monitoring_service.start.assert_called_once()
                mock_security_service.start.assert_called_once()

def test_stop_application(mas_application, mock_orchestrator, mock_monitoring_service, mock_security_service):
    with patch('mycosoft_mas.core.orchestrator.Orchestrator', return_value=mock_orchestrator):
        with patch('mycosoft_mas.services.monitoring.MonitoringService', return_value=mock_monitoring_service):
            with patch('mycosoft_mas.services.security.SecurityService', return_value=mock_security_service):
                mas_application.initialize_services()
                mas_application.start()
                mas_application.stop()
                assert mas_application.is_running is False
                mock_orchestrator.stop.assert_called_once()
                mock_monitoring_service.stop.assert_called_once()
                mock_security_service.stop.assert_called_once()

def test_get_application_status(mas_application, mock_orchestrator, mock_monitoring_service, mock_security_service):
    with patch('mycosoft_mas.core.orchestrator.Orchestrator', return_value=mock_orchestrator):
        with patch('mycosoft_mas.services.monitoring.MonitoringService', return_value=mock_monitoring_service):
            with patch('mycosoft_mas.services.security.SecurityService', return_value=mock_security_service):
                mas_application.initialize_services()
                status = mas_application.get_status()
                assert "orchestrator" in status
                assert "monitoring" in status
                assert "security" in status
                assert "clusters" in status
                assert status["orchestrator"]["status"] == "running"
                assert status["monitoring"]["status"] == "running"
                assert status["security"]["status"] == "running"

def test_handle_agent_registration(mas_application, mock_orchestrator, mock_agent):
    mas_application.orchestrator = mock_orchestrator
    mas_application.handle_agent_registration(mock_agent)
    mock_orchestrator.register_agent.assert_called_once_with(mock_agent)

def test_handle_agent_unregistration(mas_application, mock_orchestrator, mock_agent):
    mas_application.orchestrator = mock_orchestrator
    mas_application.handle_agent_unregistration(mock_agent.agent_id)
    mock_orchestrator.unregister_agent.assert_called_once_with(mock_agent.agent_id)

def test_handle_task_submission(mas_application, mock_orchestrator):
    mas_application.orchestrator = mock_orchestrator
    task = {"type": "test_task", "data": "test_data"}
    mas_application.handle_task_submission(task)
    mock_orchestrator.submit_task.assert_called_once_with(task)

def test_generate_system_report(mas_application, mock_orchestrator, mock_monitoring_service, mock_security_service):
    with patch('mycosoft_mas.core.orchestrator.Orchestrator', return_value=mock_orchestrator):
        with patch('mycosoft_mas.services.monitoring.MonitoringService', return_value=mock_monitoring_service):
            with patch('mycosoft_mas.services.security.SecurityService', return_value=mock_security_service):
                mas_application.initialize_services()
                report = mas_application.generate_system_report()
                assert "orchestrator_status" in report
                assert "monitoring_metrics" in report
                assert "security_status" in report
                assert "cluster_status" in report
                assert report["orchestrator_status"]["status"] == "running"
                assert report["monitoring_metrics"]["status"] == "running"
                assert report["security_status"]["status"] == "running" 