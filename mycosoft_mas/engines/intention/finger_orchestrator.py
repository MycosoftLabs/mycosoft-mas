"""
FingerOrchestrator - Task classification and routing to frontier models.

Routes content to appropriate LLM provider (Claude, Gemini, etc.) by task type.
Created: February 17, 2026
"""

import logging
from typing import Any, AsyncGenerator, Dict, Optional

logger = logging.getLogger(__name__)

TASK_PROVIDER_MAP = {
    "code": "claude",
    "coding": "claude",
    "programming": "claude",
    "reasoning": "claude",
    "logic": "claude",
    "analysis": "claude",
    "creative": "gemini",
    "writing": "gemini",
    "brainstorm": "gemini",
    "general": "gemini",
    "default": "gemini",
}


class FingerOrchestrator:
    """
    Classifies task type and routes to frontier LLM providers.
    Wraps FrontierLLMRouter with task-based provider selection.
    """

    def __init__(self):
        self._router = None

    def _get_router(self):
        """Lazy load FrontierLLMRouter."""
        if self._router is None:
            try:
                from mycosoft_mas.llm.frontier_router import FrontierLLMRouter
                self._router = FrontierLLMRouter()
            except ImportError as e:
                logger.warning("FrontierLLMRouter not available: %s", e)
        return self._router

    def classify_task(self, content: str) -> str:
        """
        Classify task type from content. Returns one of: code, reasoning, creative, general.
        V0: Keyword-based. Future: LLM classification.
        """
        content_lower = content.lower()
        if any(k in content_lower for k in ["code", "implement", "function", "api", "endpoint", "bug", "fix"]):
            return "code"
        if any(k in content_lower for k in ["analyze", "reason", "logic", "explain why", "compare"]):
            return "reasoning"
        if any(k in content_lower for k in ["write", "creative", "story", "brainstorm", "idea"]):
            return "creative"
        return "general"

    async def route(
        self,
        content: str,
        context: Dict[str, Any],
    ) -> AsyncGenerator[str, None]:
        """
        Route content to appropriate frontier provider and stream response.
        Uses FrontierLLMRouter.stream_response with provider hint.
        """
        router = self._get_router()
        if not router:
            yield "[Frontier LLM router not available. Please check configuration.]"
            return

        task_type = self.classify_task(content)
        provider = TASK_PROVIDER_MAP.get(task_type, TASK_PROVIDER_MAP["default"])

        from mycosoft_mas.llm.frontier_router import ConversationContext
        conv_context = ConversationContext(
            session_id=context.get("session_id", "default"),
            conversation_id=context.get("conversation_id", "default"),
            user_id=context.get("user_id", "morgan"),
            turn_count=context.get("turn_count", 0),
            history=context.get("history", []),
            active_tools=context.get("active_tools", []),
            current_role=context.get("current_role", "orchestrator"),
        )

        async for token in router.stream_response(
            message=content,
            context=conv_context,
            tools=context.get("tools"),
            provider=provider,
        ):
            yield token
