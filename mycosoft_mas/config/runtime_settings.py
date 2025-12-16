from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from pydantic import BaseModel, Field


def _load_yaml_with_env(path: Path) -> Dict[str, Any]:
    """Load YAML and expand ${ENV_VAR} placeholders via the current environment."""
    if not path.exists():
        return {}
    text = path.read_text()
    expanded = os.path.expandvars(text)
    return yaml.safe_load(expanded) or {}


class ProviderConfig(BaseModel):
    provider: str
    model: str
    base_url: Optional[str] = None
    api_key: Optional[str] = None


class ModelRegistry(BaseModel):
    providers: Dict[str, ProviderConfig] = Field(default_factory=dict)
    roles: Dict[str, str] = Field(default_factory=dict)  # e.g., "planning_model": "openai:gpt-4o-mini"

    def get_model_target(self, role: str) -> Optional[tuple[str, str]]:
        """
        Return (provider_key, model_name) for a logical role such as planning_model.
        """
        role_value = self.roles.get(role)
        if not role_value:
            return None
        if ":" in role_value:
            provider_key, model_name = role_value.split(":", 1)
            return provider_key, model_name
        return role_value, self.providers.get(role_value, ProviderConfig(provider=role_value, model="")).model


class RuntimeSettings(BaseModel):
    database_url: str
    redis_url: str
    qdrant_url: Optional[str] = None
    llm_default_provider: Optional[str] = None
    llm_base_url: Optional[str] = None
    llm_api_key: Optional[str] = None
    model_registry: ModelRegistry = Field(default_factory=ModelRegistry)
    approval_required: bool = False
    log_level: str = "INFO"

    @classmethod
    def from_files(
        cls,
        config_path: Path = Path("config/config.yaml"),
        models_path: Path = Path("config/models.yaml"),
    ) -> tuple["RuntimeSettings", Dict[str, Any]]:
        """
        Load runtime settings from YAML files plus environment overrides.
        Returns a (settings, raw_config_dict) tuple; raw_config_dict preserves the existing
        nested structure for backwards compatibility.
        """
        raw_config = _load_yaml_with_env(config_path)
        raw_models = _load_yaml_with_env(models_path)

        # Backwards-compatible dictionary (existing callers expect this)
        merged_config = raw_config.copy()

        database_url = os.getenv("DATABASE_URL", raw_config.get("database", {}).get("url", ""))
        redis_url = os.getenv("REDIS_URL", raw_config.get("redis", {}).get("url", "redis://redis:6379/0"))
        qdrant_url = os.getenv("QDRANT_URL", raw_config.get("qdrant", {}).get("url", "http://qdrant:6333"))

        model_registry = _build_model_registry(raw_models)
        settings = cls(
            database_url=database_url,
            redis_url=redis_url,
            qdrant_url=qdrant_url,
            llm_default_provider=os.getenv("LLM_DEFAULT_PROVIDER", raw_models.get("default_provider")),
            llm_base_url=os.getenv("LLM_BASE_URL", raw_models.get("default_base_url")),
            llm_api_key=os.getenv("LLM_API_KEY"),
            model_registry=model_registry,
            approval_required=_as_bool(os.getenv("APPROVAL_REQUIRED", "false")),
            log_level=os.getenv("LOG_LEVEL", raw_config.get("app", {}).get("log_level", "INFO")),
        )

        # Keep model registry in the raw config for compatibility
        merged_config.setdefault("llm", {})
        merged_config["llm"]["model_registry"] = model_registry.model_dump()
        merged_config["llm"]["default_provider"] = settings.llm_default_provider
        merged_config["llm"]["base_url"] = settings.llm_base_url

        return settings, merged_config

    def sanitized_summary(self) -> Dict[str, Any]:
        """Return a redacted summary safe to log."""
        return {
            "database_url": _mask_url(self.database_url),
            "redis_url": _mask_url(self.redis_url),
            "qdrant_url": self.qdrant_url,
            "llm_default_provider": self.llm_default_provider,
            "llm_base_url": self.llm_base_url,
            "approval_required": self.approval_required,
            "log_level": self.log_level,
            "model_roles": self.model_registry.roles,
        }


def _build_model_registry(raw_models: Dict[str, Any]) -> ModelRegistry:
    providers: Dict[str, ProviderConfig] = {}
    for key, value in (raw_models.get("providers") or {}).items():
        if not isinstance(value, dict):
            continue
        providers[key] = ProviderConfig(
            provider=value.get("provider", key),
            model=value.get("model", ""),
            base_url=value.get("base_url"),
            api_key=value.get("api_key"),
        )
    roles = raw_models.get("roles") or {}
    return ModelRegistry(providers=providers, roles=roles)


def _mask_url(url: Optional[str]) -> Optional[str]:
    if not url:
        return url
    # Preserve scheme + host, mask credentials if present
    if "@" in url:
        prefix, host = url.rsplit("@", 1)
        return "***@" + host
    if len(url) > 12:
        return url[:4] + "***" + url[-4:]
    return "***"


def _as_bool(value: str) -> bool:
    return value.lower() in {"1", "true", "yes", "on"}
