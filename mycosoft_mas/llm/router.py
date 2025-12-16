"""
LLM Router Module

Provides intelligent routing of LLM requests to appropriate providers and models
based on task type, tool requirements, cost preferences, and availability.
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, AsyncGenerator, Optional

from mycosoft_mas.llm.config import LLMConfig, get_llm_config
from mycosoft_mas.llm.providers.base import (
    BaseLLMProvider,
    LLMResponse,
    LLMError,
    LLMErrorType,
    EmbeddingResponse,
    Message,
)
from mycosoft_mas.llm.providers.openai_compatible import OpenAICompatibleProvider
from mycosoft_mas.llm.providers.openai_provider import OpenAIProvider

logger = logging.getLogger(__name__)


@dataclass
class ProviderHealth:
    """Track health status of a provider."""
    provider: str
    is_healthy: bool = True
    last_check: datetime = field(default_factory=datetime.now)
    failure_count: int = 0
    last_failure: Optional[datetime] = None
    
    def mark_failure(self) -> None:
        self.failure_count += 1
        self.last_failure = datetime.now()
        if self.failure_count >= 3:
            self.is_healthy = False
    
    def mark_success(self) -> None:
        self.is_healthy = True
        self.failure_count = 0
    
    def should_retry(self) -> bool:
        """Check if we should retry this provider after failures."""
        if self.is_healthy:
            return True
        if self.last_failure is None:
            return True
        # Wait at least 60 seconds before retrying a failed provider
        return datetime.now() - self.last_failure > timedelta(seconds=60)


@dataclass
class UsageTracker:
    """Track LLM usage for cost management."""
    total_tokens: int = 0
    total_cost: float = 0.0
    request_count: int = 0
    daily_tokens: int = 0
    daily_cost: float = 0.0
    daily_reset: datetime = field(default_factory=datetime.now)
    
    def add_usage(self, tokens: int, cost: float) -> None:
        self.total_tokens += tokens
        self.total_cost += cost
        self.request_count += 1
        
        # Reset daily counters if needed
        if datetime.now().date() > self.daily_reset.date():
            self.daily_tokens = 0
            self.daily_cost = 0.0
            self.daily_reset = datetime.now()
        
        self.daily_tokens += tokens
        self.daily_cost += cost
    
    def is_over_budget(self, daily_budget: float) -> bool:
        return self.daily_cost >= daily_budget


class LLMRouter:
    """
    Intelligent LLM request router.
    
    Routes requests to appropriate providers/models based on:
    - Task type (planning, execution, fast, embedding)
    - Tool calling requirements
    - Cost/latency preferences
    - Provider availability
    
    Supports automatic fallback when providers are unavailable.
    """
    
    def __init__(
        self,
        config: Optional[LLMConfig] = None,
    ):
        self.config = config or get_llm_config()
        self.logger = logging.getLogger("llm.router")
        
        # Provider instances
        self._providers: dict[str, BaseLLMProvider] = {}
        
        # Health tracking
        self._health: dict[str, ProviderHealth] = {}
        
        # Usage tracking
        self._usage = UsageTracker()
        
        # Initialize providers
        self._init_providers()
    
    def _init_providers(self) -> None:
        """Initialize configured providers."""
        # Always initialize the OpenAI-compatible provider (for LiteLLM)
        if self.config.litellm_base_url:
            self._providers["litellm"] = OpenAICompatibleProvider(
                api_key=self.config.litellm_api_key,
                base_url=self.config.litellm_base_url,
                timeout=self.config.default_timeout,
                max_retries=self.config.default_max_retries,
            )
            self._health["litellm"] = ProviderHealth(provider="litellm")
        
        # Initialize OpenAI if configured
        openai_config = self.config.get_provider_config("openai")
        if openai_config and openai_config.api_key:
            self._providers["openai"] = OpenAIProvider(
                api_key=openai_config.api_key,
                base_url=openai_config.base_url or "",
                timeout=self.config.default_timeout,
                max_retries=self.config.default_max_retries,
            )
            self._health["openai"] = ProviderHealth(provider="openai")
        
        # Initialize Azure OpenAI if configured
        azure_config = self.config.get_provider_config("azure")
        if azure_config and azure_config.api_key:
            self._providers["azure"] = OpenAIProvider(
                api_key=azure_config.api_key,
                base_url=azure_config.base_url,
                azure_api_version=azure_config.api_version,
                timeout=self.config.default_timeout,
                max_retries=self.config.default_max_retries,
            )
            self._health["azure"] = ProviderHealth(provider="azure")
    
    def _select_provider(
        self,
        preferred: Optional[str] = None,
    ) -> tuple[str, BaseLLMProvider]:
        """
        Select the best available provider.
        
        Args:
            preferred: Preferred provider name
            
        Returns:
            Tuple of (provider_name, provider_instance)
            
        Raises:
            LLMError: If no providers are available
        """
        # Try preferred provider first
        if preferred and preferred in self._providers:
            health = self._health.get(preferred)
            if health and health.should_retry():
                return preferred, self._providers[preferred]
        
        # Try default provider
        default = self.config.default_provider
        if default in self._providers:
            health = self._health.get(default)
            if health and health.should_retry():
                return default, self._providers[default]
        
        # Fall back to LiteLLM (unified proxy)
        if "litellm" in self._providers:
            return "litellm", self._providers["litellm"]
        
        # Try any available provider
        for name, provider in self._providers.items():
            health = self._health.get(name)
            if health and health.should_retry():
                return name, provider
        
        raise LLMError(
            error_type=LLMErrorType.SERVICE_UNAVAILABLE,
            message="No LLM providers available",
            provider="router",
            model="",
        )
    
    def _select_model(
        self,
        task_type: str = "execution",
        requires_tools: bool = False,
        requires_vision: bool = False,
    ) -> str:
        """
        Select the appropriate model for a task.
        
        Args:
            task_type: Type of task (planning, execution, fast, embedding)
            requires_tools: Whether the task requires tool/function calling
            requires_vision: Whether the task requires vision capabilities
            
        Returns:
            Model identifier string
        """
        model = self.config.get_model_for_task(task_type)
        
        # Check model capabilities if we have registry info
        if model in self.config.models:
            model_info = self.config.models[model]
            
            if requires_tools and not model_info.supports_tools:
                # Fall back to a model that supports tools
                model = self.config.execution_model
            
            if requires_vision and not model_info.supports_vision:
                # Fall back to a vision-capable model
                model = "gpt-4o"  # Known to support vision
        
        return model
    
    async def chat(
        self,
        messages: list[Message],
        task_type: str = "execution",
        model: Optional[str] = None,
        provider: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        tools: Optional[list[dict[str, Any]]] = None,
        tool_choice: Optional[str | dict[str, Any]] = None,
        **kwargs: Any,
    ) -> LLMResponse:
        """
        Send a chat completion request with automatic routing.
        
        Args:
            messages: List of chat messages
            task_type: Type of task for model selection
            model: Override model selection
            provider: Override provider selection
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            tools: Tool definitions for function calling
            tool_choice: Tool selection strategy
            **kwargs: Additional provider-specific parameters
            
        Returns:
            LLMResponse with generated content
        """
        # Check budget
        if self._usage.is_over_budget(self.config.daily_budget):
            raise LLMError(
                error_type=LLMErrorType.RATE_LIMIT,
                message=f"Daily budget exceeded: ${self._usage.daily_cost:.2f}",
                provider="router",
                model="",
            )
        
        # Select model
        selected_model = model or self._select_model(
            task_type=task_type,
            requires_tools=bool(tools),
        )
        
        # Try primary provider
        provider_name, provider_instance = self._select_provider(provider)
        
        try:
            response = await provider_instance.chat(
                messages=messages,
                model=selected_model,
                temperature=temperature,
                max_tokens=max_tokens,
                tools=tools,
                tool_choice=tool_choice,
                **kwargs,
            )
            
            # Update tracking
            self._health[provider_name].mark_success()
            self._usage.add_usage(
                tokens=response.usage.total_tokens,
                cost=response.estimated_cost,
            )
            
            return response
            
        except LLMError as e:
            self._health[provider_name].mark_failure()
            
            # Try fallback if enabled
            if self.config.enable_fallback and e.retryable:
                return await self._fallback_chat(
                    messages=messages,
                    model=selected_model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    tools=tools,
                    tool_choice=tool_choice,
                    exclude_provider=provider_name,
                    **kwargs,
                )
            
            raise
    
    async def _fallback_chat(
        self,
        messages: list[Message],
        model: str,
        exclude_provider: str,
        **kwargs: Any,
    ) -> LLMResponse:
        """Try fallback providers when primary fails."""
        errors = []
        
        for fallback_name in self.config.fallback_providers:
            if fallback_name == exclude_provider:
                continue
            
            if fallback_name not in self._providers:
                continue
            
            health = self._health.get(fallback_name)
            if not health or not health.should_retry():
                continue
            
            try:
                self.logger.info(f"Trying fallback provider: {fallback_name}")
                
                # Use fallback model if configured
                fallback_model = self.config.fallback_model or model
                
                response = await self._providers[fallback_name].chat(
                    messages=messages,
                    model=fallback_model,
                    **kwargs,
                )
                
                self._health[fallback_name].mark_success()
                self._usage.add_usage(
                    tokens=response.usage.total_tokens,
                    cost=response.estimated_cost,
                )
                
                return response
                
            except LLMError as e:
                self._health[fallback_name].mark_failure()
                errors.append(f"{fallback_name}: {e.message}")
                continue
        
        # All fallbacks failed
        raise LLMError(
            error_type=LLMErrorType.SERVICE_UNAVAILABLE,
            message=f"All providers failed. Errors: {'; '.join(errors)}",
            provider="router",
            model=model,
        )
    
    async def complete(
        self,
        prompt: str,
        task_type: str = "execution",
        model: Optional[str] = None,
        provider: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> LLMResponse:
        """Send a text completion request."""
        messages = [Message(role="user", content=prompt)]
        return await self.chat(
            messages=messages,
            task_type=task_type,
            model=model,
            provider=provider,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        )
    
    async def embed(
        self,
        texts: list[str],
        model: Optional[str] = None,
        provider: Optional[str] = None,
        **kwargs: Any,
    ) -> EmbeddingResponse:
        """Generate embeddings with automatic routing."""
        selected_model = model or self.config.embedding_model
        provider_name, provider_instance = self._select_provider(provider)
        
        try:
            response = await provider_instance.embed(
                texts=texts,
                model=selected_model,
                **kwargs,
            )
            
            self._health[provider_name].mark_success()
            return response
            
        except LLMError as e:
            self._health[provider_name].mark_failure()
            raise
    
    async def chat_stream(
        self,
        messages: list[Message],
        task_type: str = "execution",
        model: Optional[str] = None,
        provider: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> AsyncGenerator[str, None]:
        """Stream chat completion response."""
        selected_model = model or self._select_model(task_type=task_type)
        provider_name, provider_instance = self._select_provider(provider)
        
        async for chunk in provider_instance.chat_stream(
            messages=messages,
            model=selected_model,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        ):
            yield chunk
    
    async def health_check(self) -> dict[str, bool]:
        """Check health of all configured providers."""
        results = {}
        
        for name, provider in self._providers.items():
            try:
                is_healthy = await provider.health_check()
                self._health[name].is_healthy = is_healthy
                results[name] = is_healthy
            except Exception:
                self._health[name].mark_failure()
                results[name] = False
        
        return results
    
    def get_usage_stats(self) -> dict[str, Any]:
        """Get current usage statistics."""
        return {
            "total_tokens": self._usage.total_tokens,
            "total_cost": self._usage.total_cost,
            "request_count": self._usage.request_count,
            "daily_tokens": self._usage.daily_tokens,
            "daily_cost": self._usage.daily_cost,
            "daily_budget": self.config.daily_budget,
            "budget_remaining": self.config.daily_budget - self._usage.daily_cost,
        }
    
    def get_provider_status(self) -> dict[str, dict[str, Any]]:
        """Get status of all providers."""
        return {
            name: {
                "is_healthy": health.is_healthy,
                "failure_count": health.failure_count,
                "last_check": health.last_check.isoformat(),
            }
            for name, health in self._health.items()
        }
