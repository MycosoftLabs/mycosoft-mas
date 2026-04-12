"""
Configuration helpers for Deep Agents feature flags.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class DeepAgentsConfig:
    enabled: bool
    protocol_enabled: bool
    filesystem_enabled: bool
    redis_events_enabled: bool
    model: str
    default_timeout_seconds: float


def get_deep_agents_config() -> DeepAgentsConfig:
    return DeepAgentsConfig(
        enabled=_env_bool("MYCA_DEEP_AGENTS_ENABLED", False),
        protocol_enabled=_env_bool("MYCA_AGENT_PROTOCOL_ENABLED", False),
        filesystem_enabled=_env_bool("MYCA_DEEP_AGENTS_FILESYSTEM_ENABLED", True),
        redis_events_enabled=_env_bool("MYCA_DEEP_AGENTS_REDIS_EVENTS_ENABLED", True),
        model=os.getenv("MYCA_DEEP_AGENTS_MODEL", "gpt-4o"),
        default_timeout_seconds=float(os.getenv("MYCA_DEEP_AGENTS_TIMEOUT_SECONDS", "180")),
    )
