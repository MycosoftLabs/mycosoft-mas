import pytest
from unittest.mock import Mock, patch
from mycosoft_mas.services.monitoring import MonitoringService
from mycosoft_mas.agents.base_agent import BaseAgent

@pytest.fixture
def monitoring_service():
    return MonitoringService()

@pytest.fixture
def mock_agent():
    agent = Mock(spec=BaseAgent)
    agent.agent_id = "test_agent"
    agent.capabilities = ["test_capability"]
    return agent

def test_monitoring_service_initialization(monitoring_service):
    assert monitoring_service.metrics == {}
    assert monitoring_service.alerts == []
    assert monitoring_service.health_checks == {}
    assert monitoring_service.performance_metrics == {}

def test_add_health_check(monitoring_service):
    def health_check():
        return True
    monitoring_service.add_health_check("test_check", health_check)
    assert "test_check" in monitoring_service.health_checks

def test_remove_health_check(monitoring_service):
    def health_check():
        return True
    monitoring_service.add_health_check("test_check", health_check)
    monitoring_service.remove_health_check("test_check")
    assert "test_check" not in monitoring_service.health_checks

def test_run_health_checks(monitoring_service):
    def passing_check():
        return True
    def failing_check():
        return False
    monitoring_service.add_health_check("passing", passing_check)
    monitoring_service.add_health_check("failing", failing_check)
    results = monitoring_service.run_health_checks()
    assert results["passing"] is True
    assert results["failing"] is False

def test_add_metric(monitoring_service):
    monitoring_service.add_metric("test_metric", 100)
    assert "test_metric" in monitoring_service.metrics
    assert monitoring_service.metrics["test_metric"] == 100

def test_update_metric(monitoring_service):
    monitoring_service.add_metric("test_metric", 100)
    monitoring_service.update_metric("test_metric", 200)
    assert monitoring_service.metrics["test_metric"] == 200

def test_get_metric(monitoring_service):
    monitoring_service.add_metric("test_metric", 100)
    value = monitoring_service.get_metric("test_metric")
    assert value == 100

def test_add_alert(monitoring_service):
    monitoring_service.add_alert("test_alert", "Test alert message", "warning")
    assert len(monitoring_service.alerts) == 1
    assert monitoring_service.alerts[0]["type"] == "warning"
    assert monitoring_service.alerts[0]["message"] == "Test alert message"

def test_clear_alerts(monitoring_service):
    monitoring_service.add_alert("test_alert", "Test alert message", "warning")
    monitoring_service.clear_alerts()
    assert len(monitoring_service.alerts) == 0

def test_track_performance(monitoring_service):
    monitoring_service.track_performance("test_operation", 1.5)
    assert "test_operation" in monitoring_service.performance_metrics
    assert len(monitoring_service.performance_metrics["test_operation"]) == 1
    assert monitoring_service.performance_metrics["test_operation"][0] == 1.5

def test_get_performance_stats(monitoring_service):
    monitoring_service.track_performance("test_operation", 1.0)
    monitoring_service.track_performance("test_operation", 2.0)
    monitoring_service.track_performance("test_operation", 3.0)
    stats = monitoring_service.get_performance_stats("test_operation")
    assert stats["min"] == 1.0
    assert stats["max"] == 3.0
    assert stats["mean"] == 2.0
    assert stats["count"] == 3

def test_monitor_agent(monitoring_service, mock_agent):
    mock_agent.get_status.return_value = {
        "status": "running",
        "capabilities": ["test_capability"],
        "task_count": 0
    }
    monitoring_service.monitor_agent(mock_agent)
    key_prefix = f"{mock_agent.__class__.__name__}"
    assert f"{key_prefix}_status" in monitoring_service.metrics
    assert monitoring_service.metrics[f"{key_prefix}_status"]["status"] == "running"
    assert monitoring_service.metrics[f"{key_prefix}_status"]["task_count"] == 0

def test_generate_insights(monitoring_service):
    monitoring_service.track_performance("test_operation", 1.0)
    monitoring_service.track_performance("test_operation", 2.0)
    monitoring_service.track_performance("test_operation", 3.0)
    insights = monitoring_service.generate_insights()
    assert "test_operation" in insights["performance"]
    assert "min" in insights["performance"]["test_operation"]
    assert "max" in insights["performance"]["test_operation"]
    assert "mean" in insights["performance"]["test_operation"]
