from unittest.mock import Mock

import pytest

from mycosoft_mas.agents.base_agent import BaseAgent
from mycosoft_mas.services.monitoring import MonitoringService


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
