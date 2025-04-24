import pytest
from unittest.mock import Mock, patch
from mycosoft_mas.integrations.integration_manager import IntegrationManager
from mycosoft_mas.agents.base_agent import BaseAgent

@pytest.fixture
def integration_manager():
    return IntegrationManager()

@pytest.fixture
def mock_agent():
    agent = Mock(spec=BaseAgent)
    agent.agent_id = "test_agent"
    agent.capabilities = ["test_capability"]
    return agent

def test_integration_manager_initialization(integration_manager):
    assert integration_manager.integrations == {}
    assert integration_manager.adapters == {}
    assert integration_manager.connection_pool == {}
    assert integration_manager.integration_metrics == {}

def test_register_integration(integration_manager):
    def integration_handler():
        return True
    integration_manager.register_integration("test_integration", integration_handler)
    assert "test_integration" in integration_manager.integrations
    assert integration_manager.integrations["test_integration"] == integration_handler

def test_unregister_integration(integration_manager):
    def integration_handler():
        return True
    integration_manager.register_integration("test_integration", integration_handler)
    integration_manager.unregister_integration("test_integration")
    assert "test_integration" not in integration_manager.integrations

def test_add_adapter(integration_manager):
    def adapter_handler():
        return True
    integration_manager.add_adapter("test_adapter", adapter_handler)
    assert "test_adapter" in integration_manager.adapters
    assert integration_manager.adapters["test_adapter"] == adapter_handler

def test_remove_adapter(integration_manager):
    def adapter_handler():
        return True
    integration_manager.add_adapter("test_adapter", adapter_handler)
    integration_manager.remove_adapter("test_adapter")
    assert "test_adapter" not in integration_manager.adapters

def test_establish_connection(integration_manager):
    connection_config = {
        "type": "test_connection",
        "host": "localhost",
        "port": 8080
    }
    connection = integration_manager.establish_connection("test_connection", connection_config)
    assert "test_connection" in integration_manager.connection_pool
    assert integration_manager.connection_pool["test_connection"] == connection

def test_close_connection(integration_manager):
    connection_config = {
        "type": "test_connection",
        "host": "localhost",
        "port": 8080
    }
    integration_manager.establish_connection("test_connection", connection_config)
    integration_manager.close_connection("test_connection")
    assert "test_connection" not in integration_manager.connection_pool

def test_execute_integration(integration_manager):
    def integration_handler(data):
        return {"result": data}
    integration_manager.register_integration("test_integration", integration_handler)
    result = integration_manager.execute_integration("test_integration", {"test": "data"})
    assert result["result"]["test"] == "data"

def test_transform_data(integration_manager):
    def adapter_handler(data):
        return {"transformed": data}
    integration_manager.add_adapter("test_adapter", adapter_handler)
    result = integration_manager.transform_data("test_adapter", {"test": "data"})
    assert result["transformed"]["test"] == "data"

def test_monitor_integration(integration_manager):
    integration_manager.monitor_integration("test_integration")
    assert "test_integration" in integration_manager.integration_metrics
    assert "last_execution" in integration_manager.integration_metrics["test_integration"]
    assert "execution_count" in integration_manager.integration_metrics["test_integration"]

def test_get_integration_status(integration_manager):
    integration_manager.monitor_integration("test_integration")
    status = integration_manager.get_integration_status("test_integration")
    assert "last_execution" in status
    assert "execution_count" in status
    assert "is_active" in status

def test_generate_integration_report(integration_manager):
    integration_manager.monitor_integration("test_integration")
    report = integration_manager.generate_integration_report()
    assert "test_integration" in report
    assert "last_execution" in report["test_integration"]
    assert "execution_count" in report["test_integration"]
    assert "is_active" in report["test_integration"] 