"""
Action Arbitration - Executive function for MYCA's consciousness.

Full-Duplex Consciousness OS (April 2026).

The ActionArbiter is MYCA's "executive function" — it receives a current
intention/focus plus context signals and decides *what to do next*:

  SPEAK_NOW        — Respond immediately from working memory
  ASK_CLARIFY      — Need more information before acting
  CALL_TOOL        — Invoke a specific tool
  DELEGATE_AGENT   — Hand off to a specialist agent
  QUEUE_FOR_LATER  — Defer: user is still speaking or task is not urgent

Design principles:
- Deterministic rules first (fast, no LLM needed for simple cases)
- LLM tie-breaker for genuinely ambiguous cases (async, non-blocking)
- Decision traces always recorded for debugging
- Never blocks the conversation — worst case returns QUEUE_FOR_LATER
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class Action(str, Enum):
    """Possible executive decisions."""

    SPEAK_NOW = "speak_now"           # Reply immediately
    ASK_CLARIFY = "ask_clarify"       # Request clarification
    CALL_TOOL = "call_tool"           # Invoke a tool
    DELEGATE_AGENT = "delegate_agent" # Hand off to specialist agent
    QUEUE_FOR_LATER = "queue_for_later"  # Defer — safe default


class RiskLevel(str, Enum):
    """Risk level of the proposed action."""

    READ_ONLY = "read_only"    # No side-effects (search, recall)
    WRITE = "write"            # Creates/modifies data
    DANGEROUS = "dangerous"    # Destructive, financial, or irreversible


class UserMode(str, Enum):
    """Inferred user intent mode."""

    CHATTING = "chatting"    # Casual conversation
    TASKING = "tasking"      # Asking MYCA to DO something
    UNKNOWN = "unknown"


@dataclass
class ActionPlan:
    """The result of arbitration — what MYCA should do next."""

    action: Action
    tool: Optional[str] = None          # Set when action == CALL_TOOL
    agent: Optional[str] = None         # Set when action == DELEGATE_AGENT
    clarify_prompt: Optional[str] = None  # Set when action == ASK_CLARIFY
    confidence: float = 1.0            # 0.0–1.0
    reason: str = ""                    # Human-readable explanation
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action": self.action.value,
            "tool": self.tool,
            "agent": self.agent,
            "clarify_prompt": self.clarify_prompt,
            "confidence": self.confidence,
            "reason": self.reason,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class ArbitrationContext:
    """All signals available to the arbiter at decision time."""

    # Attention focus
    intent_category: str = "unknown"    # e.g. "tool_request", "question", "chat"
    detected_tool: Optional[str] = None
    detected_agent: Optional[str] = None

    # Confidence signals
    intuition_confidence: float = 0.5   # 0.0–1.0 from intuition engine

    # Timing budget
    latency_budget_ms: int = 1500       # How long we have before user notices lag

    # Risk
    risk_level: RiskLevel = RiskLevel.READ_ONLY

    # Conversation state
    is_mid_utterance: bool = False      # User is still speaking
    is_speaking: bool = False           # MYCA is currently outputting TTS

    # User mode
    user_mode: UserMode = UserMode.UNKNOWN

    # Memory / context signals
    has_working_memory_answer: bool = False   # Fast answer available in WM
    requires_tool: bool = False               # Intent clearly needs a tool
    ambiguity_score: float = 0.0              # 0 = clear, 1 = very ambiguous


class ActionArbiter:
    """
    Executive function: decides talk vs act vs ask vs defer.

    Rule priority (applied top-to-bottom, first match wins):
    1. Safety guards (dangerous while mid-utterance → defer)
    2. Fast-path answers (high confidence + chatting → speak)
    3. Tool routing (clear tool intent + tasking → tool)
    4. Agent routing (clear agent intent → delegate)
    5. Clarification (high ambiguity → ask)
    6. Default: queue for later
    """

    # Thresholds
    HIGH_CONFIDENCE = 0.85
    LOW_CONFIDENCE = 0.40
    HIGH_AMBIGUITY = 0.70

    def decide(self, ctx: ArbitrationContext) -> ActionPlan:
        """
        Apply deterministic rules to produce an ActionPlan.

        All decisions are O(1) — no I/O, no blocking.

        Args:
            ctx: Current arbitration context

        Returns:
            ActionPlan with the chosen action and reasoning
        """
        # ── Guard: dangerous action mid-utterance → always defer ──────────
        if ctx.is_mid_utterance and ctx.risk_level == RiskLevel.DANGEROUS:
            return ActionPlan(
                action=Action.QUEUE_FOR_LATER,
                confidence=1.0,
                reason="Dangerous action deferred: user is still speaking",
            )

        # ── Guard: write action mid-utterance without clear tasking → defer ─
        if (
            ctx.is_mid_utterance
            and ctx.risk_level == RiskLevel.WRITE
            and ctx.user_mode != UserMode.TASKING
        ):
            return ActionPlan(
                action=Action.QUEUE_FOR_LATER,
                confidence=0.9,
                reason="Write action deferred: mid-utterance, mode not confirmed tasking",
            )

        # ── Fast path: answer is in working memory + chatting ──────────────
        if (
            ctx.has_working_memory_answer
            and ctx.intuition_confidence >= self.HIGH_CONFIDENCE
            and ctx.user_mode in (UserMode.CHATTING, UserMode.UNKNOWN)
            and not ctx.requires_tool
        ):
            return ActionPlan(
                action=Action.SPEAK_NOW,
                confidence=ctx.intuition_confidence,
                reason="High-confidence answer available in working memory",
            )

        # ── Tool routing ───────────────────────────────────────────────────
        if ctx.requires_tool and ctx.detected_tool:
            # Only call tool if not mid-utterance OR if it's read-only
            if not ctx.is_mid_utterance or ctx.risk_level == RiskLevel.READ_ONLY:
                return ActionPlan(
                    action=Action.CALL_TOOL,
                    tool=ctx.detected_tool,
                    confidence=0.9,
                    reason=f"Tool intent detected: {ctx.detected_tool}",
                )
            else:
                return ActionPlan(
                    action=Action.QUEUE_FOR_LATER,
                    confidence=0.8,
                    reason=f"Tool {ctx.detected_tool} deferred: mid-utterance",
                )

        # ── Tool intent without specific tool identified ───────────────────
        if ctx.requires_tool and not ctx.detected_tool and ctx.user_mode == UserMode.TASKING:
            if ctx.ambiguity_score >= self.HIGH_AMBIGUITY:
                return ActionPlan(
                    action=Action.ASK_CLARIFY,
                    clarify_prompt="Could you tell me more about what you'd like me to do?",
                    confidence=0.75,
                    reason="Tool intent but ambiguous — need clarification",
                )

        # ── Agent routing ─────────────────────────────────────────────────
        if ctx.detected_agent:
            return ActionPlan(
                action=Action.DELEGATE_AGENT,
                agent=ctx.detected_agent,
                confidence=0.85,
                reason=f"Delegating to specialist agent: {ctx.detected_agent}",
            )

        # ── Clarification for high ambiguity ──────────────────────────────
        if ctx.ambiguity_score >= self.HIGH_AMBIGUITY and not ctx.is_mid_utterance:
            return ActionPlan(
                action=Action.ASK_CLARIFY,
                clarify_prompt="I want to make sure I understand — could you clarify what you mean?",
                confidence=0.7,
                reason=f"High ambiguity score ({ctx.ambiguity_score:.2f})",
            )

        # ── Low-confidence chatting → speak anyway with hedging ───────────
        if (
            ctx.user_mode == UserMode.CHATTING
            and ctx.intuition_confidence >= self.LOW_CONFIDENCE
            and not ctx.requires_tool
        ):
            return ActionPlan(
                action=Action.SPEAK_NOW,
                confidence=ctx.intuition_confidence,
                reason="Chatting mode: speaking with available context",
            )

        # ── Default: queue for later ──────────────────────────────────────
        return ActionPlan(
            action=Action.QUEUE_FOR_LATER,
            confidence=0.5,
            reason="No rule matched — deferring to next cycle",
        )

    def decide_from_signals(
        self,
        intent_category: str = "unknown",
        intuition_confidence: float = 0.5,
        latency_budget_ms: int = 1500,
        risk_level: str = "read_only",
        is_mid_utterance: bool = False,
        user_mode: str = "unknown",
        detected_tool: Optional[str] = None,
        detected_agent: Optional[str] = None,
        has_working_memory_answer: bool = False,
        requires_tool: bool = False,
        ambiguity_score: float = 0.0,
    ) -> ActionPlan:
        """
        Convenience wrapper that accepts raw signal values.

        Converts strings to enums and delegates to decide().
        """
        try:
            risk = RiskLevel(risk_level)
        except ValueError:
            risk = RiskLevel.READ_ONLY

        try:
            mode = UserMode(user_mode)
        except ValueError:
            mode = UserMode.UNKNOWN

        ctx = ArbitrationContext(
            intent_category=intent_category,
            detected_tool=detected_tool,
            detected_agent=detected_agent,
            intuition_confidence=intuition_confidence,
            latency_budget_ms=latency_budget_ms,
            risk_level=risk,
            is_mid_utterance=is_mid_utterance,
            user_mode=mode,
            has_working_memory_answer=has_working_memory_answer,
            requires_tool=requires_tool,
            ambiguity_score=ambiguity_score,
        )
        plan = self.decide(ctx)
        logger.debug(
            f"Arbiter: {plan.action.value} "
            f"(confidence={plan.confidence:.2f}, reason={plan.reason!r})"
        )
        return plan


# Module-level singleton
_arbiter: Optional[ActionArbiter] = None


def get_arbiter() -> ActionArbiter:
    """Get the global ActionArbiter instance."""
    global _arbiter
    if _arbiter is None:
        _arbiter = ActionArbiter()
    return _arbiter
