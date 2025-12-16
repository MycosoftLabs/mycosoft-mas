import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from mycosoft_mas.llm.router import LLMRouter
from mycosoft_mas.llm.config import LLMConfig

@pytest.fixture
def mock_config():
    config = LLMConfig()
    config.default_provider = "openai"
    config.api_key = "test-key"
    return config

@pytest.mark.asyncio
async def test_router_initialization(mock_config):
    with patch("mycosoft_mas.llm.router.OpenAIProvider") as MockProvider:
        router = LLMRouter(mock_config)
        assert "openai" in router.providers
        MockProvider.assert_called_once()

@pytest.mark.asyncio
async def test_router_chat_delegation(mock_config):
    with patch("mycosoft_mas.llm.router.OpenAIProvider") as MockProvider:
        mock_instance = MockProvider.return_value
        mock_instance.chat = AsyncMock(return_value={"choices": []})
        
        router = LLMRouter(mock_config)
        await router.chat([{"role": "user", "content": "hi"}], usage="execution")
        
        mock_instance.chat.assert_called_once()
