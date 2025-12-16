"""
Model Registry

Manages model configurations and provider mappings.
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class ModelType(str, Enum):
    """Model usage types."""
    PLANNING = "planning"
    EXECUTION = "execution"
    FAST = "fast"
    EMBEDDING = "embedding"
    CODE = "code"
    VISION = "vision"


@dataclass
class ModelConfig:
    """Configuration for a single model."""
    
    name: str
    provider: str
    model_id: str
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    supports_functions: bool = False
    supports_vision: bool = False
    cost_per_1k_prompt_tokens: float = 0.0
    cost_per_1k_completion_tokens: float = 0.0
    context_window: int = 4096
    
    @classmethod
    def from_dict(cls, name: str, data: Dict[str, Any]) -> "ModelConfig":
        """Create ModelConfig from dictionary."""
        return cls(
            name=name,
            provider=data["provider"],
            model_id=data["model"],
            temperature=data.get("temperature", 0.7),
            max_tokens=data.get("max_tokens"),
            supports_functions=data.get("supports_functions", False),
            supports_vision=data.get("supports_vision", False),
            cost_per_1k_prompt_tokens=data.get("cost_per_1k_prompt_tokens", 0.0),
            cost_per_1k_completion_tokens=data.get("cost_per_1k_completion_tokens", 0.0),
            context_window=data.get("context_window", 4096)
        )


class ModelRegistry:
    """Registry for managing models and their configurations."""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the model registry.
        
        Args:
            config_path: Path to models configuration file (YAML)
        """
        self.config_path = config_path or self._find_config_file()
        self.models: Dict[str, ModelConfig] = {}
        self.model_types: Dict[ModelType, str] = {}
        self.provider_configs: Dict[str, Dict[str, Any]] = {}
        
        self._load_config()
    
    def _find_config_file(self) -> str:
        """Find the models configuration file."""
        # Try multiple locations
        possible_paths = [
            Path("config/models.yaml"),
            Path("config/models.yml"),
            Path("models.yaml"),
            Path(__file__).parent.parent.parent / "config" / "models.yaml",
        ]
        
        for path in possible_paths:
            if path.exists():
                return str(path)
        
        # Return default path (will be created if needed)
        return "config/models.yaml"
    
    def _load_config(self):
        """Load configuration from file."""
        config_file = Path(self.config_path)
        
        if not config_file.exists():
            logger.warning(f"Models config file not found: {self.config_path}. Using defaults.")
            self._load_default_config()
            return
        
        try:
            with open(config_file, "r") as f:
                config = yaml.safe_load(f)
            
            # Load models
            models_config = config.get("models", {})
            for model_name, model_data in models_config.items():
                self.models[model_name] = ModelConfig.from_dict(model_name, model_data)
            
            # Load model type mappings
            for model_type in ModelType:
                type_key = model_type.value
                if type_key in models_config:
                    model_name = models_config[type_key].get("model_name", type_key)
                    self.model_types[model_type] = model_name
            
            # Load provider configs
            self.provider_configs = config.get("providers", {})
            
            # Environment variable overrides
            self._apply_env_overrides()
            
            logger.info(f"Loaded {len(self.models)} models from {self.config_path}")
            
        except Exception as e:
            logger.error(f"Failed to load models config: {e}. Using defaults.")
            self._load_default_config()
    
    def _load_default_config(self):
        """Load default configuration."""
        # Default models
        self.models = {
            "gpt-4-turbo": ModelConfig(
                name="gpt-4-turbo",
                provider="openai",
                model_id="gpt-4-turbo-preview",
                temperature=0.7,
                max_tokens=4096,
                supports_functions=True,
                cost_per_1k_prompt_tokens=0.01,
                cost_per_1k_completion_tokens=0.03,
                context_window=128000
            ),
            "gpt-3.5-turbo": ModelConfig(
                name="gpt-3.5-turbo",
                provider="openai",
                model_id="gpt-3.5-turbo",
                temperature=0.7,
                max_tokens=4096,
                supports_functions=True,
                cost_per_1k_prompt_tokens=0.0005,
                cost_per_1k_completion_tokens=0.0015,
                context_window=16385
            ),
        }
        
        # Default type mappings
        self.model_types = {
            ModelType.PLANNING: "gpt-4-turbo",
            ModelType.EXECUTION: "gpt-4-turbo",
            ModelType.FAST: "gpt-3.5-turbo",
            ModelType.EMBEDDING: "text-embedding-3-small",
        }
        
        # Default provider configs
        self.provider_configs = {
            "openai": {
                "api_key": os.getenv("OPENAI_API_KEY", ""),
                "base_url": os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
            }
        }
    
    def _apply_env_overrides(self):
        """Apply environment variable overrides."""
        # Override default provider
        default_provider = os.getenv("LLM_DEFAULT_PROVIDER")
        if default_provider:
            logger.info(f"Overriding default provider to: {default_provider}")
        
        # Override specific models
        for model_type in ModelType:
            env_key = f"LLM_MODEL_{model_type.value.upper()}"
            env_value = os.getenv(env_key)
            if env_value:
                self.model_types[model_type] = env_value
                logger.info(f"Override {model_type.value} model to: {env_value}")
    
    def get_model(self, model_name: str) -> Optional[ModelConfig]:
        """
        Get model configuration by name.
        
        Args:
            model_name: Name of the model
            
        Returns:
            ModelConfig or None if not found
        """
        return self.models.get(model_name)
    
    def get_model_for_type(self, model_type: ModelType) -> Optional[ModelConfig]:
        """
        Get model configuration for a specific use case type.
        
        Args:
            model_type: Type of model needed
            
        Returns:
            ModelConfig or None if not found
        """
        model_name = self.model_types.get(model_type)
        if not model_name:
            return None
        return self.get_model(model_name)
    
    def get_provider_config(self, provider: str) -> Dict[str, Any]:
        """
        Get configuration for a provider.
        
        Args:
            provider: Provider name
            
        Returns:
            Provider configuration dictionary
        """
        return self.provider_configs.get(provider, {})
    
    def list_models(self, provider: Optional[str] = None) -> List[ModelConfig]:
        """
        List all models, optionally filtered by provider.
        
        Args:
            provider: Optional provider name to filter by
            
        Returns:
            List of ModelConfig objects
        """
        models = list(self.models.values())
        if provider:
            models = [m for m in models if m.provider == provider]
        return models
    
    def list_providers(self) -> List[str]:
        """
        List all configured providers.
        
        Returns:
            List of provider names
        """
        return list(self.provider_configs.keys())
    
    def estimate_cost(
        self,
        model_name: str,
        prompt_tokens: int,
        completion_tokens: int
    ) -> float:
        """
        Estimate cost for a model call.
        
        Args:
            model_name: Name of the model
            prompt_tokens: Number of prompt tokens
            completion_tokens: Number of completion tokens
            
        Returns:
            Estimated cost in USD
        """
        model = self.get_model(model_name)
        if not model:
            return 0.0
        
        prompt_cost = (prompt_tokens / 1000) * model.cost_per_1k_prompt_tokens
        completion_cost = (completion_tokens / 1000) * model.cost_per_1k_completion_tokens
        
        return prompt_cost + completion_cost
