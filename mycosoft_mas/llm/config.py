"""
LLM Configuration Module

Handles loading and validating LLM configuration from environment variables
and config files. Supports multiple providers and model selection policies.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional
import logging
import yaml

logger = logging.getLogger(__name__)


@dataclass
class ModelConfig:
    """Configuration for a specific model."""
    name: str
    provider: str
    max_tokens: int = 4096
    temperature: float = 0.7
    supports_tools: bool = True
    supports_vision: bool = False
    cost_per_1k_input: float = 0.0
    cost_per_1k_output: float = 0.0


@dataclass
class ProviderConfig:
    """Configuration for an LLM provider."""
    name: str
    api_key: str = ""
    base_url: str = ""
    api_version: str = ""
    timeout: int = 120
    max_retries: int = 3
    retry_delay: float = 1.0


@dataclass
class LLMConfig:
    """Main LLM configuration container."""
    # Default provider
    default_provider: str = "openai"
    
    # LiteLLM proxy (unified endpoint)
    litellm_base_url: str = "http://localhost:4000"
    litellm_api_key: str = ""
    
    # Provider configurations
    providers: dict[str, ProviderConfig] = field(default_factory=dict)
    
    # Model assignments by task type
    planning_model: str = "gpt-4o"
    execution_model: str = "gpt-4o-mini"
    fast_model: str = "gpt-4o-mini"
    embedding_model: str = "text-embedding-3-small"
    fallback_model: str = "gpt-4o-mini"
    
    # Model registry
    models: dict[str, ModelConfig] = field(default_factory=dict)
    
    # Router settings
    enable_fallback: bool = True
    fallback_providers: list[str] = field(default_factory=lambda: ["openai", "azure", "anthropic"])
    
    # Cost/budget controls
    max_tokens_per_request: int = 8192
    max_cost_per_request: float = 1.0  # USD
    daily_budget: float = 100.0  # USD
    
    # Retry policy
    default_timeout: int = 120
    default_max_retries: int = 3
    retry_on_rate_limit: bool = True
    
    @classmethod
    def from_env(cls) -> "LLMConfig":
        """Load configuration from environment variables."""
        config = cls()
        
        # Default provider
        config.default_provider = os.getenv("LLM_DEFAULT_PROVIDER", "openai")
        
        # LiteLLM settings
        config.litellm_base_url = os.getenv("LLM_BASE_URL", "http://localhost:4000")
        config.litellm_api_key = os.getenv("LITELLM_MASTER_KEY", "")
        
        # Model assignments
        config.planning_model = os.getenv("LLM_MODEL_PLANNING", "gpt-4o")
        config.execution_model = os.getenv("LLM_MODEL_EXECUTION", "gpt-4o-mini")
        config.fast_model = os.getenv("LLM_MODEL_FAST", "gpt-4o-mini")
        config.embedding_model = os.getenv("LLM_MODEL_EMBEDDING", "text-embedding-3-small")
        config.fallback_model = os.getenv("LLM_MODEL_FALLBACK", "gpt-4o-mini")
        
        # Provider configs
        config.providers = {
            "openai": ProviderConfig(
                name="openai",
                api_key=os.getenv("OPENAI_API_KEY", ""),
                base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
            ),
            "azure": ProviderConfig(
                name="azure",
                api_key=os.getenv("AZURE_API_KEY", ""),
                base_url=os.getenv("AZURE_API_BASE", ""),
                api_version=os.getenv("AZURE_API_VERSION", "2024-02-15-preview"),
            ),
            "gemini": ProviderConfig(
                name="gemini",
                api_key=os.getenv("GEMINI_API_KEY", ""),
            ),
            "anthropic": ProviderConfig(
                name="anthropic",
                api_key=os.getenv("ANTHROPIC_API_KEY", ""),
            ),
            "ollama": ProviderConfig(
                name="ollama",
                base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
            ),
            "litellm": ProviderConfig(
                name="litellm",
                api_key=os.getenv("LITELLM_MASTER_KEY", ""),
                base_url=os.getenv("LLM_BASE_URL", "http://localhost:4000"),
            ),
        }
        
        # Budget settings
        config.max_cost_per_request = float(os.getenv("LLM_MAX_COST_PER_REQUEST", "1.0"))
        config.daily_budget = float(os.getenv("LLM_DAILY_BUDGET", "100.0"))
        
        # Timeout and retry
        config.default_timeout = int(os.getenv("LLM_TIMEOUT", "120"))
        config.default_max_retries = int(os.getenv("LLM_MAX_RETRIES", "3"))
        
        return config
    
    @classmethod
    def from_yaml(cls, path: str | Path) -> "LLMConfig":
        """Load configuration from a YAML file."""
        path = Path(path)
        if not path.exists():
            logger.warning(f"Config file not found: {path}, using defaults")
            return cls.from_env()
        
        with open(path) as f:
            data = yaml.safe_load(f)
        
        config = cls.from_env()  # Start with env vars
        
        # Override with YAML values
        if "default_provider" in data:
            config.default_provider = data["default_provider"]
        
        if "models" in data:
            for task, model in data["models"].items():
                if task == "planning":
                    config.planning_model = model
                elif task == "execution":
                    config.execution_model = model
                elif task == "fast":
                    config.fast_model = model
                elif task == "embedding":
                    config.embedding_model = model
                elif task == "fallback":
                    config.fallback_model = model
        
        if "model_registry" in data:
            for name, model_data in data["model_registry"].items():
                config.models[name] = ModelConfig(
                    name=name,
                    provider=model_data.get("provider", "openai"),
                    max_tokens=model_data.get("max_tokens", 4096),
                    temperature=model_data.get("temperature", 0.7),
                    supports_tools=model_data.get("supports_tools", True),
                    supports_vision=model_data.get("supports_vision", False),
                    cost_per_1k_input=model_data.get("cost_per_1k_input", 0.0),
                    cost_per_1k_output=model_data.get("cost_per_1k_output", 0.0),
                )
        
        if "router" in data:
            router = data["router"]
            config.enable_fallback = router.get("enable_fallback", True)
            config.fallback_providers = router.get("fallback_providers", config.fallback_providers)
        
        if "budget" in data:
            budget = data["budget"]
            config.max_cost_per_request = budget.get("max_cost_per_request", config.max_cost_per_request)
            config.daily_budget = budget.get("daily_budget", config.daily_budget)
        
        return config
    
    def get_model_for_task(self, task_type: str) -> str:
        """Get the configured model for a specific task type."""
        task_models = {
            "planning": self.planning_model,
            "execution": self.execution_model,
            "fast": self.fast_model,
            "embedding": self.embedding_model,
            "fallback": self.fallback_model,
        }
        return task_models.get(task_type, self.execution_model)
    
    def get_provider_config(self, provider: str) -> Optional[ProviderConfig]:
        """Get configuration for a specific provider."""
        return self.providers.get(provider)
    
    def is_provider_configured(self, provider: str) -> bool:
        """Check if a provider has valid credentials configured."""
        config = self.providers.get(provider)
        if not config:
            return False
        
        # LiteLLM and Ollama don't require API keys
        if provider in ("litellm", "ollama"):
            return bool(config.base_url)
        
        return bool(config.api_key)
    
    def validate(self) -> list[str]:
        """Validate configuration and return list of errors."""
        errors = []
        
        # Check default provider is configured
        if not self.is_provider_configured(self.default_provider):
            # Allow litellm as fallback
            if self.default_provider != "litellm":
                errors.append(f"Default provider '{self.default_provider}' is not configured")
        
        return errors
    
    def to_sanitized_dict(self) -> dict[str, Any]:
        """Return config dict with secrets redacted for logging."""
        return {
            "default_provider": self.default_provider,
            "litellm_base_url": self.litellm_base_url,
            "planning_model": self.planning_model,
            "execution_model": self.execution_model,
            "fast_model": self.fast_model,
            "embedding_model": self.embedding_model,
            "fallback_model": self.fallback_model,
            "enable_fallback": self.enable_fallback,
            "max_cost_per_request": self.max_cost_per_request,
            "providers_configured": [
                name for name, _ in self.providers.items()
                if self.is_provider_configured(name)
            ],
        }


# Global config instance
_config: Optional[LLMConfig] = None


def get_llm_config() -> LLMConfig:
    """Get the global LLM configuration instance."""
    global _config
    if _config is None:
        # Try to load from YAML first, fall back to env
        config_path = Path("config/models.yaml")
        if config_path.exists():
            _config = LLMConfig.from_yaml(config_path)
        else:
            _config = LLMConfig.from_env()
        
        # Log sanitized config
        logger.info(f"LLM Config loaded: {_config.to_sanitized_dict()}")
    
    return _config


def reset_llm_config() -> None:
    """Reset the global config (useful for testing)."""
    global _config
    _config = None
