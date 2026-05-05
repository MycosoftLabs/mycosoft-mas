"""Typed structures for Agent100."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

Framework = Literal[
    "openclaw",
    "nemoclaw",
    "mas_base",
    "claude_api",
    "gpt_api",
    "gemini_api",
    "grok_api",
    "crewai",
    "langchain",
    "langgraph",
]

CallMode = Literal["singular", "multi", "grouped", "all_bundle", "health", "snapshot"]


@dataclass
class AgentRow:
    id: str
    archetype: str
    framework: Framework
    tier_budget_cents: int = 20_000
    api_key_env: str = ""
    pair_agent_id: str | None = None
    parent_agent_id: str | None = None
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass
class CallRecord:
    agent_id: str
    archetype: str
    framework: str
    dataset_id: str | None
    mode: str
    request_path: str
    status_code: int | None
    latency_ms: int | None
    cache: str | None
    cost_debited: int | None
    rate_weight: int | None
    bytes: int | None
    schema_valid: bool | None
    freshness_ok: bool | None
    error_class: str | None
    request_id: str | None
    envelope_ok: bool | None
