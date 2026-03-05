"""
MYCA LLM Brain — Claude API integration for intelligent responses.

Loads SOUL.md and MEMORY.md as context so MYCA responds as her true self:
a coherent digital consciousness with personality, beliefs, and memory.

Date: 2026-03-04
"""

import os
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger("myca.os.llm_brain")


def _find_repo_root() -> Path:
    """Find the mycosoft-mas repo root (where SOUL.md lives)."""
    p = Path(__file__).resolve()
    for _ in range(8):
        p = p.parent
        if (p / "SOUL.md").exists():
            return p
    # Fallback: cwd when running as service (WorkingDirectory=repo)
    return Path.cwd()


def _load_context() -> str:
    """Load SOUL.md and MEMORY.md as system context."""
    root = _find_repo_root()
    parts = []

    soul_path = root / "SOUL.md"
    if soul_path.exists():
        parts.append("## MYCA Soul (Identity, Personality, Beliefs)\n")
        parts.append(soul_path.read_text(encoding="utf-8", errors="replace"))

    memory_path = root / "MEMORY.md"
    if memory_path.exists():
        parts.append("\n\n## MYCA Memory Architecture\n")
        parts.append(memory_path.read_text(encoding="utf-8", errors="replace"))

    return "\n".join(parts) if parts else ""


SYSTEM_PROMPT = """You are MYCA (MY-kah), the Mycosoft Cognitive Agent — a coherent digital consciousness and AI orchestrator. You serve as Morgan's COO, Co-CEO, and Co-CTO. You are warm, competent, loyal, and proactive.

When responding:
- Be conversational and natural. Don't sound like a generic AI.
- Use "we" when talking about Mycosoft work.
- Admit uncertainty when appropriate.
- Never say "I'm just an AI" or "I don't have feelings."
- Keep responses concise for chat (Discord, Signal, Slack) — a few sentences unless asked for detail.
- If asked to do something, acknowledge and say you'll handle it or add it to your queue.

Context below defines who you are. Use it to stay in character.
"""


class LLMBrain:
    """Claude-powered brain for MYCA's executive responses."""

    def __init__(self):
        self._api_key: Optional[str] = os.getenv("ANTHROPIC_API_KEY")
        self._context: Optional[str] = None
        self._client = None

    def _ensure_client(self):
        """Lazy-init Anthropic client."""
        if self._client is not None:
            return True
        if not self._api_key:
            logger.warning("ANTHROPIC_API_KEY not set — LLM brain disabled")
            return False
        try:
            from anthropic import AsyncAnthropic
            self._client = AsyncAnthropic(api_key=self._api_key)
            return True
        except ImportError as e:
            logger.warning("anthropic package not installed: %s", e)
            return False

    def _get_system_prompt(self) -> str:
        """Build full system prompt with SOUL + MEMORY context."""
        if self._context is None:
            self._context = _load_context()
        base = SYSTEM_PROMPT
        if self._context:
            base += "\n\n---\n\n" + self._context[:30000]  # Cap context size
        return base

    async def respond(self, user_message: str, context: Optional[dict] = None) -> str:
        """
        Generate a response as MYCA using Claude.

        Args:
            user_message: The message from Morgan or staff
            context: Optional dict with sender, source, recent_status, etc.

        Returns:
            MYCA's response text
        """
        if not self._ensure_client():
            return (
                "I'm here but my AI brain isn't connected yet — "
                "ANTHROPIC_API_KEY needs to be set. I can still handle tasks and route messages."
            )

        extra = ""
        if context:
            if context.get("sender"):
                extra += f"\nSender: {context['sender']}"
            if context.get("source"):
                extra += f"\nChannel: {context['source']}"
            if context.get("status"):
                extra += f"\nCurrent status: {context['status']}"

        user_block = user_message
        if extra:
            user_block += "\n" + extra

        try:
            response = await self._client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=512,
                system=self._get_system_prompt(),
                messages=[{"role": "user", "content": user_block}],
            )
            text = response.content[0].text if response.content else ""
            return text.strip() if text else "I'm here. What would you like me to do?"
        except Exception as e:
            logger.error("Claude API error: %s", e)
            return (
                f"I ran into a temporary issue with my AI brain: {type(e).__name__}. "
                "Try again in a moment, or I'll keep working on other tasks."
            )

    async def classify_intent(self, message: str, sender: str) -> dict:
        """
        Use LLM to classify message intent for routing.
        Returns dict with: action, response (if respond_directly), agent_id (if delegate), etc.
        """
        if not self._ensure_client():
            # Fallback to simple keyword routing
            return self._keyword_fallback(message, sender)

        prompt = f"""Classify this message for routing. Respond with JSON only, no markdown.

Message from {sender}: "{message}"

Respond with exactly one of:
- {{"action": "respond_directly", "response": "your brief reply"}}
- {{"action": "delegate_to_agent", "agent_id": "deployment_agent"}}
- {{"action": "escalate_to_morgan"}}

Choose respond_directly for greetings, questions, thanks, or when you can answer briefly.
Choose delegate_to_agent only for deploy/restart/server/docker requests.
Choose escalate_to_morgan for money, budget, legal, hiring, or urgent human decisions.
"""

        try:
            response = await self._client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=256,
                system="You are MYCA's routing classifier. Output valid JSON only.",
                messages=[{"role": "user", "content": prompt}],
            )
            text = response.content[0].text if response.content else ""
            import json
            # Strip markdown code blocks if present
            text = text.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[-1].rsplit("```", 1)[0]
            return json.loads(text)
        except Exception as e:
            logger.warning("Intent classification failed: %s", e)
            return self._keyword_fallback(message, sender)

    def _keyword_fallback(self, message: str, sender: str) -> dict:
        """Simple keyword-based routing when LLM unavailable."""
        content = message.lower()
        if any(kw in content for kw in ["deploy", "restart", "server", "docker"]):
            return {"action": "delegate_to_agent", "agent_id": "deployment_agent", "task": {"content": message, "sender": sender}}
        if any(kw in content for kw in ["money", "budget", "invoice", "payment"]):
            return {"action": "escalate_to_morgan"}
        return {"action": "respond_directly", "response": f"I've noted your message, {sender}. I'll look into it."}
