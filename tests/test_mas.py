import pytest
from fastapi.testclient import TestClient
from mycosoft_mas import create_app
from mycosoft_mas.core.config import settings
import asyncio
import aioredis
import pytest_asyncio

@pytest.fixture
def test_client():
    app = create_app()
    return TestClient(app)

@pytest.fixture
async def redis_client():
    redis = await aioredis.from_url(f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}")
    yield redis
    await redis.close()

@pytest.mark.asyncio
async def test_health_check(test_client):
    response = test_client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

@pytest.mark.asyncio
async def test_agent_manager():
    from mycosoft_mas.agents.agent_manager import AgentManager
    manager = AgentManager()
    assert await manager.initialize() is True
    assert len(await manager.list_active_agents()) >= 0

@pytest.mark.asyncio
async def test_dependency_manager():
    from mycosoft_mas.dependencies.dependency_manager import DependencyManager
    manager = DependencyManager()
    assert await manager.check_dependencies() is True

@pytest.mark.asyncio
async def test_integration_manager():
    from mycosoft_mas.integrations.integration_manager import IntegrationManager
    manager = IntegrationManager()
    assert await manager.verify_integrations() is True

@pytest.mark.asyncio
async def test_security_service():
    from mycosoft_mas.security.security_service import SecurityService
    service = SecurityService()
    assert await service.verify_security_config() is True

@pytest.mark.asyncio
async def test_evolution_monitor():
    from mycosoft_mas.services.evolution_monitor import EvolutionMonitor
    monitor = EvolutionMonitor()
    assert await monitor.check_status() is True

@pytest.mark.asyncio
async def test_technology_tracker():
    from mycosoft_mas.services.technology_tracker import TechnologyTracker
    tracker = TechnologyTracker()
    assert await tracker.get_status() is True

@pytest.mark.asyncio
async def test_redis_connection(redis_client):
    await redis_client.set("test_key", "test_value")
    value = await redis_client.get("test_key")
    assert value.decode() == "test_value"

@pytest.mark.asyncio
async def test_prometheus_metrics(test_client):
    response = test_client.get("/metrics")
    assert response.status_code == 200
    assert "python_info" in response.text 