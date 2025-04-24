import pytest
from unittest.mock import Mock, patch
from mycosoft_mas.services.security import SecurityService
from mycosoft_mas.agents.base_agent import BaseAgent

@pytest.fixture
def security_service():
    return SecurityService()

@pytest.fixture
def mock_agent():
    agent = Mock(spec=BaseAgent)
    agent.agent_id = "test_agent"
    agent.capabilities = ["test_capability"]
    return agent

def test_security_service_initialization(security_service):
    assert security_service.authentication_tokens == {}
    assert security_service.access_controls == {}
    assert security_service.security_logs == []
    assert security_service.incident_reports == []

def test_authenticate_agent(security_service, mock_agent):
    token = security_service.authenticate_agent(mock_agent)
    assert token is not None
    assert token in security_service.authentication_tokens
    assert security_service.authentication_tokens[token] == mock_agent.agent_id

def test_validate_token(security_service, mock_agent):
    token = security_service.authenticate_agent(mock_agent)
    assert security_service.validate_token(token) is True
    assert security_service.validate_token("invalid_token") is False

def test_revoke_token(security_service, mock_agent):
    token = security_service.authenticate_agent(mock_agent)
    security_service.revoke_token(token)
    assert token not in security_service.authentication_tokens
    assert security_service.validate_token(token) is False

def test_add_access_control(security_service):
    security_service.add_access_control("test_resource", ["test_agent"], ["read"])
    assert "test_resource" in security_service.access_controls
    assert "test_agent" in security_service.access_controls["test_resource"]
    assert "read" in security_service.access_controls["test_resource"]["test_agent"]

def test_remove_access_control(security_service):
    security_service.add_access_control("test_resource", ["test_agent"], ["read"])
    security_service.remove_access_control("test_resource", "test_agent")
    assert "test_agent" not in security_service.access_controls["test_resource"]

def test_check_access(security_service, mock_agent):
    security_service.add_access_control("test_resource", [mock_agent.agent_id], ["read"])
    token = security_service.authenticate_agent(mock_agent)
    assert security_service.check_access(token, "test_resource", "read") is True
    assert security_service.check_access(token, "test_resource", "write") is False

def test_log_security_event(security_service):
    security_service.log_security_event("test_event", "Test security event", "info")
    assert len(security_service.security_logs) == 1
    assert security_service.security_logs[0]["type"] == "info"
    assert security_service.security_logs[0]["message"] == "Test security event"

def test_clear_security_logs(security_service):
    security_service.log_security_event("test_event", "Test security event", "info")
    security_service.clear_security_logs()
    assert len(security_service.security_logs) == 0

def test_report_incident(security_service):
    security_service.report_incident("test_incident", "Test security incident", "high")
    assert len(security_service.incident_reports) == 1
    assert security_service.incident_reports[0]["severity"] == "high"
    assert security_service.incident_reports[0]["description"] == "Test security incident"

def test_resolve_incident(security_service):
    security_service.report_incident("test_incident", "Test security incident", "high")
    security_service.resolve_incident("test_incident")
    assert security_service.incident_reports[0]["status"] == "resolved"

def test_monitor_security(security_service, mock_agent):
    security_service.monitor_security(mock_agent)
    assert mock_agent.agent_id in security_service.security_metrics
    assert "last_activity" in security_service.security_metrics[mock_agent.agent_id]
    assert "access_attempts" in security_service.security_metrics[mock_agent.agent_id]

def test_generate_security_report(security_service):
    security_service.log_security_event("test_event", "Test security event", "info")
    security_service.report_incident("test_incident", "Test security incident", "high")
    report = security_service.generate_security_report()
    assert "security_logs" in report
    assert "incident_reports" in report
    assert "security_metrics" in report
    assert len(report["security_logs"]) == 1
    assert len(report["incident_reports"]) == 1 