"""
Tests for LLM Router

Tests the LLM routing, fallback, and error handling logic.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from mycosoft_mas.llm.config import LLMConfig, ProviderConfig
from mycosoft_mas.llm.router import LLMRouter, ProviderHealth, UsageTracker
from mycosoft_mas.llm.providers.base import (
    LLMResponse,
    LLMError,
    LLMErrorType,
    Message,
    TokenUsage,
)


class TestUsageTracker:
    """Tests for UsageTracker."""
    
    def test_add_usage(self):
        """Test adding usage stats."""
        tracker = UsageTracker()
        
        tracker.add_usage(tokens=100, cost=0.01)
        
        assert tracker.total_tokens == 100
        assert tracker.total_cost == 0.01
        assert tracker.request_count == 1
        assert tracker.daily_tokens == 100
        assert tracker.daily_cost == 0.01
    
    def test_cumulative_usage(self):
        """Test cumulative usage tracking."""
        tracker = UsageTracker()
        
        tracker.add_usage(tokens=100, cost=0.01)
        tracker.add_usage(tokens=200, cost=0.02)
        tracker.add_usage(tokens=50, cost=0.005)
        
        assert tracker.total_tokens == 350
        assert tracker.total_cost == 0.035
        assert tracker.request_count == 3
    
    def test_is_over_budget(self):
        """Test budget checking."""
        tracker = UsageTracker()
        tracker.daily_cost = 99.0
        
        assert not tracker.is_over_budget(100.0)
        
        tracker.daily_cost = 100.0
        assert tracker.is_over_budget(100.0)
        
        tracker.daily_cost = 101.0
        assert tracker.is_over_budget(100.0)


class TestProviderHealth:
    """Tests for ProviderHealth."""
    
    def test_initial_state(self):
        """Test initial health state."""
        health = ProviderHealth(provider="test")
        
        assert health.is_healthy
        assert health.failure_count == 0
        assert health.should_retry()
    
    def test_mark_failure(self):
        """Test marking failures."""
        health = ProviderHealth(provider="test")
        
        health.mark_failure()
        assert health.failure_count == 1
        assert health.is_healthy  # Still healthy after 1 failure
        
        health.mark_failure()
        health.mark_failure()  # 3rd failure
        assert health.failure_count == 3
        assert not health.is_healthy  # Unhealthy after 3 failures
    
    def test_mark_success_resets(self):
        """Test that success resets failure count."""
        health = ProviderHealth(provider="test")
        
        health.mark_failure()
        health.mark_failure()
        health.mark_failure()
        assert not health.is_healthy
        
        health.mark_success()
        assert health.is_healthy
        assert health.failure_count == 0


class TestLLMRouter:
    """Tests for LLMRouter."""
    
    @pytest.fixture
    def mock_config(self):
        """Create mock config."""
        config = LLMConfig()
        config.default_provider = "litellm"
        config.litellm_base_url = "http://localhost:4000"
        config.litellm_api_key = "test-key"
        config.planning_model = "gpt-4o"
        config.execution_model = "gpt-4o-mini"
        config.fast_model = "gpt-4o-mini"
        config.enable_fallback = True
        config.daily_budget = 100.0
        return config
    
    def test_model_selection_by_task(self, mock_config):
        """Test model selection based on task type."""
        router = LLMRouter(config=mock_config)
        
        assert router._select_model(task_type="planning") == "gpt-4o"
        assert router._select_model(task_type="execution") == "gpt-4o-mini"
        assert router._select_model(task_type="fast") == "gpt-4o-mini"
    
    @pytest.mark.asyncio
    async def test_chat_success(self, mock_config):
        """Test successful chat completion."""
        router = LLMRouter(config=mock_config)
        
        # Mock the provider
        mock_response = LLMResponse(
            content="Test response",
            model="gpt-4o-mini",
            provider="litellm",
            usage=TokenUsage(prompt_tokens=10, completion_tokens=20, total_tokens=30),
        )
        
        with patch.object(
            router._providers["litellm"],
            "chat",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            messages = [Message(role="user", content="Hello")]
            response = await router.chat(messages=messages)
            
            assert response.content == "Test response"
            assert response.model == "gpt-4o-mini"
    
    @pytest.mark.asyncio
    async def test_budget_exceeded_error(self, mock_config):
        """Test that budget exceeded raises error."""
        router = LLMRouter(config=mock_config)
        router._usage.daily_cost = 100.0  # At budget limit
        
        messages = [Message(role="user", content="Hello")]
        
        with pytest.raises(LLMError) as exc_info:
            await router.chat(messages=messages)
        
        assert exc_info.value.error_type == LLMErrorType.RATE_LIMIT
        assert "budget" in exc_info.value.message.lower()
    
    @pytest.mark.asyncio
    async def test_fallback_on_error(self, mock_config):
        """Test fallback to another provider on error."""
        mock_config.fallback_providers = ["litellm", "openai"]
        router = LLMRouter(config=mock_config)
        
        # Add a mock openai provider
        mock_openai = MagicMock()
        mock_openai.chat = AsyncMock(
            return_value=LLMResponse(
                content="Fallback response",
                model="gpt-4o-mini",
                provider="openai",
            )
        )
        router._providers["openai"] = mock_openai
        router._health["openai"] = ProviderHealth(provider="openai")
        
        # Make litellm fail
        router._providers["litellm"].chat = AsyncMock(
            side_effect=LLMError(
                error_type=LLMErrorType.SERVICE_UNAVAILABLE,
                message="Service unavailable",
                provider="litellm",
                model="gpt-4o-mini",
                retryable=True,
            )
        )
        
        messages = [Message(role="user", content="Hello")]
        response = await router.chat(messages=messages)
        
        assert response.content == "Fallback response"
        assert response.provider == "openai"
    
    def test_get_usage_stats(self, mock_config):
        """Test getting usage statistics."""
        router = LLMRouter(config=mock_config)
        router._usage.total_tokens = 1000
        router._usage.total_cost = 0.05
        router._usage.request_count = 10
        
        stats = router.get_usage_stats()
        
        assert stats["total_tokens"] == 1000
        assert stats["total_cost"] == 0.05
        assert stats["request_count"] == 10
        assert stats["daily_budget"] == 100.0
    
    def test_get_provider_status(self, mock_config):
        """Test getting provider status."""
        router = LLMRouter(config=mock_config)
        
        status = router.get_provider_status()
        
        assert "litellm" in status
        assert status["litellm"]["is_healthy"] is True


class TestLLMConfig:
    """Tests for LLMConfig."""
    
    def test_from_env_defaults(self):
        """Test loading config with defaults."""
        with patch.dict("os.environ", {}, clear=True):
            config = LLMConfig.from_env()
            
            assert config.default_provider == "openai"
            assert config.planning_model == "gpt-4o"
            assert config.execution_model == "gpt-4o-mini"
    
    def test_from_env_custom(self):
        """Test loading config from environment."""
        env_vars = {
            "LLM_DEFAULT_PROVIDER": "azure",
            "LLM_MODEL_PLANNING": "azure-gpt-4",
            "LLM_MODEL_EXECUTION": "azure-gpt-35",
            "OPENAI_API_KEY": "sk-test",
            "LLM_DAILY_BUDGET": "50.0",
        }
        
        with patch.dict("os.environ", env_vars, clear=True):
            config = LLMConfig.from_env()
            
            assert config.default_provider == "azure"
            assert config.planning_model == "azure-gpt-4"
            assert config.execution_model == "azure-gpt-35"
            assert config.daily_budget == 50.0
    
    def test_get_model_for_task(self):
        """Test getting model for task type."""
        config = LLMConfig()
        config.planning_model = "gpt-4o"
        config.execution_model = "gpt-4o-mini"
        config.fast_model = "gpt-4o-mini"
        config.embedding_model = "text-embedding-3-small"
        
        assert config.get_model_for_task("planning") == "gpt-4o"
        assert config.get_model_for_task("execution") == "gpt-4o-mini"
        assert config.get_model_for_task("fast") == "gpt-4o-mini"
        assert config.get_model_for_task("embedding") == "text-embedding-3-small"
        assert config.get_model_for_task("unknown") == "gpt-4o-mini"  # Default
    
    def test_is_provider_configured(self):
        """Test checking if provider is configured."""
        config = LLMConfig()
        config.providers["openai"] = ProviderConfig(
            name="openai",
            api_key="sk-test",
        )
        config.providers["azure"] = ProviderConfig(
            name="azure",
            api_key="",  # Not configured
        )
        config.providers["litellm"] = ProviderConfig(
            name="litellm",
            base_url="http://localhost:4000",
        )
        
        assert config.is_provider_configured("openai")
        assert not config.is_provider_configured("azure")
        assert config.is_provider_configured("litellm")  # No API key needed
    
    def test_to_sanitized_dict(self):
        """Test sanitized config output."""
        config = LLMConfig()
        config.default_provider = "openai"
        config.planning_model = "gpt-4o"
        config.providers["openai"] = ProviderConfig(
            name="openai",
            api_key="sk-secret-key",
        )
        
        sanitized = config.to_sanitized_dict()
        
        assert sanitized["default_provider"] == "openai"
        assert sanitized["planning_model"] == "gpt-4o"
        assert "sk-secret-key" not in str(sanitized)  # API key not in output
        assert "openai" in sanitized["providers_configured"]
