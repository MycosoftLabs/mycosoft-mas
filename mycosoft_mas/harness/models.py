"""Harness domain models — packets, routes, planner contracts."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class RouteType(str, Enum):
    """STATIC = policy YAML hit. MINDEX_GROUNDED = MINDEX unified search + Nemotron."""

    STATIC = "static"
    MINDEX_GROUNDED = "mindex_grounded"
    NEMOTRON = "nemotron"
    PERSONAPLEX_VOICE = "personaplex_voice"
    NLM = "nlm"
    COMBINED = "combined"


class HarnessPacket(BaseModel):
    """Single unit of work through the harness."""

    query: str = ""
    intent: str | None = None
    raw_audio: bytes | None = None
    raw_sensor: dict[str, Any] | None = None
    session_id: str | None = None
    user_id: str | None = None
    prefer_voice: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


class HarnessResult(BaseModel):
    """Outcome from routing + workers."""

    route: RouteType
    text: str | None = None
    audio: bytes | None = None
    structured: dict[str, Any] = Field(default_factory=dict)
    sources: list[str] = Field(default_factory=list)
    flags: list[str] = Field(default_factory=list)
    needs_review: bool = False
