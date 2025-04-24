import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from mycosoft_mas.agents.base_agent import BaseAgent
from mycosoft_mas.agents.project_manager_agent import ProjectManagerAgent
from mycosoft_mas.agents.ip_tokenization_agent import IPTokenizationAgent
from mycosoft_mas.agents.contract_agent import ContractAgent
from mycosoft_mas.agents.legal_agent import LegalAgent
from mycosoft_mas.agents.technical_agent import TechnicalAgent
from mycosoft_mas.agents.qa_agent import QAAgent
from mycosoft_mas.agents.verification_agent import VerificationAgent
from mycosoft_mas.agents.audit_agent import AuditAgent
from mycosoft_mas.agents.registry_agent import RegistryAgent
from mycosoft_mas.agents.analytics_agent import AnalyticsAgent
from mycosoft_mas.agents.risk_agent import RiskAgent
from mycosoft_mas.agents.compliance_agent import ComplianceAgent
from mycosoft_mas.agents.operations_agent import OperationsAgent
from mycosoft_mas.agents.agent_manager import AgentManager, AgentStatus
from mycosoft_mas.services.integration_service import IntegrationService
import pytest_asyncio

@pytest.fixture
def mock_config():
    return {
        "agent_id": "test_agent",
        "name": "Test Agent",
        "capabilities": ["test_capability"],
        "status": "idle",
        "max_retries": 3,
        "retry_delay": 1,
        "health_check_interval": 60,
        "processing_interval": 0.1
    }

@pytest.fixture
def mock_integration_service():
    service = AsyncMock(spec=IntegrationService)
    service.update_agent_metrics = AsyncMock()
    service.send_message = AsyncMock()
    service.receive_message = AsyncMock()
    return service

@pytest_asyncio.fixture
async def mock_agent_manager():
    manager = AgentManager(start_background_tasks=False)  # Don't start background tasks in tests
    await manager.start()
    yield manager
    await manager.stop()

@pytest.mark.asyncio
async def test_base_agent_initialization(mock_config, mock_integration_service):
    agent = BaseAgent(
        agent_id=mock_config["agent_id"],
        name=mock_config["name"],
        config=mock_config
    )
    await agent.initialize(mock_integration_service)
    assert agent.agent_id == mock_config["agent_id"]
    assert agent.name == mock_config["name"]
    assert agent.status == AgentStatus.ACTIVE
    assert agent.is_running == True
    await agent.shutdown()

@pytest.mark.asyncio
async def test_project_manager_agent_initialization(mock_config, mock_integration_service):
    agent = ProjectManagerAgent(
        agent_id=mock_config["agent_id"],
        name=mock_config["name"],
        config=mock_config
    )
    await agent.initialize(mock_integration_service)
    assert isinstance(agent, BaseAgent)
    assert agent.agent_id == mock_config["agent_id"]
    assert agent.name == mock_config["name"]
    await agent.shutdown()

@pytest.mark.asyncio
async def test_ip_tokenization_agent_initialization(mock_config, mock_integration_service):
    agent = IPTokenizationAgent(
        agent_id=mock_config["agent_id"],
        name=mock_config["name"],
        config=mock_config
    )
    await agent.initialize(mock_integration_service)
    assert isinstance(agent, BaseAgent)
    assert agent.agent_id == mock_config["agent_id"]
    assert agent.name == mock_config["name"]
    await agent.shutdown()

@pytest.mark.asyncio
async def test_contract_agent_initialization(mock_config, mock_integration_service):
    agent = ContractAgent(
        agent_id=mock_config["agent_id"],
        name=mock_config["name"],
        config=mock_config
    )
    await agent.initialize(mock_integration_service)
    assert isinstance(agent, BaseAgent)
    assert agent.agent_id == mock_config["agent_id"]
    assert agent.name == mock_config["name"]
    await agent.shutdown()

@pytest.mark.asyncio
async def test_legal_agent_initialization(mock_config, mock_integration_service):
    agent = LegalAgent(
        agent_id=mock_config["agent_id"],
        name=mock_config["name"],
        config=mock_config
    )
    await agent.initialize(mock_integration_service)
    assert isinstance(agent, BaseAgent)
    assert agent.agent_id == mock_config["agent_id"]
    assert agent.name == mock_config["name"]
    await agent.shutdown()

@pytest.mark.asyncio
async def test_technical_agent_initialization(mock_config, mock_integration_service):
    agent = TechnicalAgent(
        agent_id=mock_config["agent_id"],
        name=mock_config["name"],
        config=mock_config
    )
    await agent.initialize(mock_integration_service)
    assert isinstance(agent, BaseAgent)
    assert agent.agent_id == mock_config["agent_id"]
    assert agent.name == mock_config["name"]
    await agent.shutdown()

@pytest.mark.asyncio
async def test_qa_agent_initialization(mock_config, mock_integration_service):
    agent = QAAgent(
        agent_id=mock_config["agent_id"],
        name=mock_config["name"],
        config=mock_config
    )
    await agent.initialize(mock_integration_service)
    assert isinstance(agent, BaseAgent)
    assert agent.agent_id == mock_config["agent_id"]
    assert agent.name == mock_config["name"]
    await agent.shutdown()

@pytest.mark.asyncio
async def test_verification_agent_initialization(mock_config, mock_integration_service):
    agent = VerificationAgent(
        agent_id=mock_config["agent_id"],
        name=mock_config["name"],
        config=mock_config
    )
    await agent.initialize(mock_integration_service)
    assert isinstance(agent, BaseAgent)
    assert agent.agent_id == mock_config["agent_id"]
    assert agent.name == mock_config["name"]
    await agent.shutdown()

@pytest.mark.asyncio
async def test_audit_agent_initialization(mock_config, mock_integration_service):
    agent = AuditAgent(
        agent_id=mock_config["agent_id"],
        name=mock_config["name"],
        config=mock_config
    )
    await agent.initialize(mock_integration_service)
    assert isinstance(agent, BaseAgent)
    assert agent.agent_id == mock_config["agent_id"]
    assert agent.name == mock_config["name"]
    await agent.shutdown()

@pytest.mark.asyncio
async def test_registry_agent_initialization(mock_config, mock_integration_service):
    agent = RegistryAgent(
        agent_id=mock_config["agent_id"],
        name=mock_config["name"],
        config=mock_config
    )
    await agent.initialize(mock_integration_service)
    assert isinstance(agent, BaseAgent)
    assert agent.agent_id == mock_config["agent_id"]
    assert agent.name == mock_config["name"]
    await agent.shutdown()

@pytest.mark.asyncio
async def test_analytics_agent_initialization(mock_config, mock_integration_service):
    agent = AnalyticsAgent(
        agent_id=mock_config["agent_id"],
        name=mock_config["name"],
        config=mock_config
    )
    await agent.initialize(mock_integration_service)
    assert isinstance(agent, BaseAgent)
    assert agent.agent_id == mock_config["agent_id"]
    assert agent.name == mock_config["name"]
    await agent.shutdown()

@pytest.mark.asyncio
async def test_risk_agent_initialization(mock_config, mock_integration_service):
    agent = RiskAgent(
        agent_id=mock_config["agent_id"],
        name=mock_config["name"],
        config=mock_config
    )
    await agent.initialize(mock_integration_service)
    assert isinstance(agent, BaseAgent)
    assert agent.agent_id == mock_config["agent_id"]
    assert agent.name == mock_config["name"]
    await agent.shutdown()

@pytest.mark.asyncio
async def test_compliance_agent_initialization(mock_config, mock_integration_service):
    agent = ComplianceAgent(
        agent_id=mock_config["agent_id"],
        name=mock_config["name"],
        config=mock_config
    )
    await agent.initialize(mock_integration_service)
    assert isinstance(agent, BaseAgent)
    assert agent.agent_id == mock_config["agent_id"]
    assert agent.name == mock_config["name"]
    await agent.shutdown()

@pytest.mark.asyncio
async def test_operations_agent_initialization(mock_config, mock_integration_service):
    agent = OperationsAgent(
        agent_id=mock_config["agent_id"],
        name=mock_config["name"],
        config=mock_config
    )
    await agent.initialize(mock_integration_service)
    assert isinstance(agent, BaseAgent)
    assert agent.agent_id == mock_config["agent_id"]
    assert agent.name == mock_config["name"]
    await agent.shutdown()

@pytest.mark.asyncio
async def test_agent_manager_initialization(mock_agent_manager):
    assert mock_agent_manager.agents == {}
    assert mock_agent_manager.agent_configs == {}
    assert mock_agent_manager.llm_providers == {}
    assert mock_agent_manager.user_profiles == {}
    assert mock_agent_manager.department_configs == {}
    assert mock_agent_manager.application_configs == {}
    assert mock_agent_manager.device_configs == {}
    assert isinstance(mock_agent_manager.notification_queue, asyncio.Queue)
    assert mock_agent_manager.error_log == []
    assert isinstance(mock_agent_manager.debug_mode, bool)
    assert mock_agent_manager.debounce_timers == {}
    assert mock_agent_manager.auto_heuristics == {}

@pytest.mark.asyncio
async def test_agent_manager_register_agent(mock_agent_manager, mock_config, mock_integration_service):
    agent = BaseAgent(
        agent_id=mock_config["agent_id"],
        name=mock_config["name"],
        config=mock_config
    )
    await agent.initialize(mock_integration_service)
    await mock_agent_manager.register_agent(agent)
    assert agent.agent_id in mock_agent_manager.agents
    assert mock_agent_manager.agents[agent.agent_id] == agent
    await agent.shutdown()

@pytest.mark.asyncio
async def test_agent_manager_create_agent(mock_agent_manager, mock_config):
    agent = await mock_agent_manager.create_agent(
        agent_type="project_manager",
        config=mock_config
    )
    assert isinstance(agent, str)  # Returns agent_id
    assert agent in mock_agent_manager.agents
    await mock_agent_manager.remove_agent(agent)

@pytest.mark.asyncio
async def test_agent_manager_get_agent(mock_agent_manager, mock_config, mock_integration_service):
    agent = BaseAgent(
        agent_id=mock_config["agent_id"],
        name=mock_config["name"],
        config=mock_config
    )
    await agent.initialize(mock_integration_service)
    await mock_agent_manager.register_agent(agent)
    retrieved_agent = mock_agent_manager.get_agent(agent.agent_id)
    assert retrieved_agent == agent
    await agent.shutdown()

@pytest.mark.asyncio
async def test_agent_manager_remove_agent(mock_agent_manager, mock_config, mock_integration_service):
    agent = BaseAgent(
        agent_id=mock_config["agent_id"],
        name=mock_config["name"],
        config=mock_config
    )
    await agent.initialize(mock_integration_service)
    await mock_agent_manager.register_agent(agent)
    await mock_agent_manager.remove_agent(agent.agent_id)
    assert agent.agent_id not in mock_agent_manager.agents
    await agent.shutdown() 