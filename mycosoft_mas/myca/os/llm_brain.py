"""
MYCA LLM Brain — Claude API integration for intelligent responses.

Loads SOUL.md and MEMORY.md as context so MYCA responds as her true self:
a coherent digital consciousness with personality, beliefs, and memory.

Phase 0: Injects live context from memory, MINDEX KG, CREP, Earth2, MycoBrain
before every respond() and classify_intent().

Phase 4: Ollama fallback when Claude API fails or is rate-limited.
Uses OLLAMA_URL (default http://192.168.0.188:11434) and OLLAMA_MODEL (default llama3.1:8b).

Date: 2026-03-04
"""

import json
import os
import logging
from pathlib import Path
from typing import Optional, TYPE_CHECKING

import aiohttp

if TYPE_CHECKING:
    from .core import MycaOS

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://192.168.0.188:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1:8b")

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

    def __init__(self, os_ref: Optional["MycaOS"] = None):
        self._api_key: Optional[str] = os.getenv("ANTHROPIC_API_KEY")
        self._context: Optional[str] = None
        self._client = None
        self._os = os_ref  # For bridges (memory, MINDEX, CREP, Earth2, MycoBrain)

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

    async def _respond_ollama(self, messages: list) -> Optional[str]:
        """
        Call Ollama /api/chat as fallback when Claude fails.
        messages: list of {"role": "user"|"system"|"assistant", "content": "..."}
        Returns response text or None on failure.
        """
        url = f"{OLLAMA_URL.rstrip('/')}/api/chat"
        payload = {"model": OLLAMA_MODEL, "messages": messages, "stream": False}
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=60),
                ) as resp:
                    if resp.status != 200:
                        logger.warning("Ollama returned status %s", resp.status)
                        return None
                    data = await resp.json()
                    msg = data.get("message", {})
                    content = msg.get("content", "")
                    return content.strip() if content else None
        except Exception as e:
            logger.warning("Ollama fallback failed: %s", e)
            return None

    async def _build_live_context(self, user_message: str, context: Optional[dict] = None) -> str:
        """
        Assemble live context from memory, MINDEX, CREP, Earth2, MycoBrain.
        Injected into system or user block before Claude responds.
        """
        if not self._os:
            return ""

        parts = []
        msg_lower = (user_message or "").lower()

        try:
            # 1. Recall from memory (session, working, episodic)
            mb = getattr(self._os, "mindex_bridge", None)
            mas = getattr(self._os, "mas_bridge", None)
            if mb and hasattr(mb, "recall"):
                for key in ["session:last_topic", "working:current_task", "episodic:recent_decisions"]:
                    val = await mb.recall(key)
                    if val:
                        parts.append(f"[Memory {key}]: {val[:500]}")
            if mas and hasattr(mas, "recall_memory"):
                memories = await mas.recall_memory(user_message[:100] if user_message else "context", limit=3)
                if memories:
                    for m in memories:
                        c = m.get("content", m) if isinstance(m, dict) else str(m)
                        parts.append(f"[MAS memory]: {str(c)[:300]}")

            # 2. MINDEX KG if domain-specific (species, fungi, taxonomy, compounds)
            if mb and any(kw in msg_lower for kw in ["species", "fungi", "fungus", "taxonomy", "compound", "mushroom", "mycology"]):
                try:
                    kg_results = await mb.query_knowledge_graph(user_message[:80], limit=5)
                    if kg_results:
                        parts.append(f"[MINDEX knowledge]: {str(kg_results)[:800]}")
                except Exception:
                    pass

            # 3. CREP worldview if situational awareness
            if any(kw in msg_lower for kw in ["environment", "what's happening", "lab", "status", "situation", "worldview"]):
                crep = getattr(self._os, "crep_bridge", None)
                if crep and hasattr(crep, "get_worldview_summary"):
                    summary = await crep.get_worldview_summary()
                    if summary:
                        parts.append(f"[CREP worldview]: {summary}")

            # 4. Earth2 if weather/climate
            if any(kw in msg_lower for kw in ["weather", "climate", "forecast", "temperature", "precipitation", "storm"]):
                earth2 = getattr(self._os, "earth2_bridge", None)
                if earth2 and hasattr(earth2, "get_weather_context"):
                    ctx = await earth2.get_weather_context()
                    if ctx:
                        parts.append(f"[Earth2]: {ctx}")

            # 5. MycoBrain/device status
            if any(kw in msg_lower for kw in ["devices", "lab", "sensors", "mycobrain", "mushroom1", "sporebase"]):
                mycobrain = getattr(self._os, "mycobrain_bridge", None)
                if mycobrain and hasattr(mycobrain, "get_telemetry_summary"):
                    summary = await mycobrain.get_telemetry_summary()
                    if summary:
                        parts.append(f"[Devices]: {summary}")
        except Exception as e:
            logger.debug("Live context build failed: %s", e)

        if not parts:
            return ""
        return "\n\n---\n\n## Live Context (Memory, Knowledge, Worldview)\n\n" + "\n\n".join(parts)

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

        # Build live context (memory, MINDEX, CREP, Earth2, MycoBrain)
        live_ctx = await self._build_live_context(user_message, context)

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
        if live_ctx:
            user_block = live_ctx + "\n\n---\n\nUser message:\n" + user_block

        system_prompt = self._get_system_prompt()
        messages_ollama = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_block},
        ]

        try:
            response = await self._client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=512,
                system=system_prompt,
                messages=[{"role": "user", "content": user_block}],
            )
            text = response.content[0].text if response.content else ""
            return text.strip() if text else "I'm here. What would you like me to do?"
        except Exception as e:
            logger.warning("Claude API error: %s; trying Ollama fallback", e)
            fallback = await self._respond_ollama(messages_ollama)
            if fallback:
                return fallback
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

        # Inject live context for better routing (e.g. memory of recent topics)
        live_ctx = await self._build_live_context(message)
        ctx_block = "\n\n" + live_ctx if live_ctx else ""

        prompt = f"""Classify this message for routing. Respond with JSON only, no markdown.{ctx_block}


Message from {sender}: "{message}"

Respond with exactly one of:
- {{"action": "respond_directly", "response": "your brief reply"}}
- {{"action": "delegate_to_agent", "agent_id": "deployment_agent"}}
- {{"action": "escalate_to_morgan"}}

Choose respond_directly for greetings, questions, thanks, or when you can answer briefly.
Choose delegate_to_agent only for deploy/restart/server/docker requests.
Choose escalate_to_morgan for money, budget, legal, hiring, or urgent human decisions.
"""

        messages_ollama = [
            {"role": "system", "content": "You are MYCA's routing classifier. Output valid JSON only."},
            {"role": "user", "content": prompt},
        ]

        try:
            response = await self._client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=256,
                system="You are MYCA's routing classifier. Output valid JSON only.",
                messages=[{"role": "user", "content": prompt}],
            )
            text = response.content[0].text if response.content else ""
            # Strip markdown code blocks if present
            text = text.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[-1].rsplit("```", 1)[0]
            return json.loads(text)
        except Exception as e:
            logger.warning("Intent classification failed: %s; trying Ollama fallback", e)
            fallback_text = await self._respond_ollama(messages_ollama)
            if fallback_text:
                text = fallback_text.strip()
                if text.startswith("```"):
                    text = text.split("\n", 1)[-1].rsplit("```", 1)[0]
                try:
                    return json.loads(text)
                except json.JSONDecodeError:
                    pass
            return self._keyword_fallback(message, sender)

    def _keyword_fallback(self, message: str, sender: str) -> dict:
        """Simple keyword-based routing when LLM unavailable."""
        content = message.lower()
        if any(kw in content for kw in ["deploy", "restart", "server", "docker"]):
            return {"action": "delegate_to_agent", "agent_id": "deployment_agent", "task": {"content": message, "sender": sender}}
        if any(kw in content for kw in ["money", "budget", "invoice", "payment"]):
            return {"action": "escalate_to_morgan"}
        return {"action": "respond_directly", "response": f"I've noted your message, {sender}. I'll look into it."}

    async def plan_browser_action(
        self,
        screenshot_b64: Optional[str] = None,
        goal: str = "",
        history: Optional[list] = None,
        a11y_tree: Optional[str] = None,
        url: Optional[str] = None,
    ) -> Optional[dict]:
        """
        Given a browser screenshot and goal, decide the next action.

        Returns a dict with: action (click|type|navigate|scroll|done), and action-specific fields
        (selector, text, url, x, y, etc.). Returns None if no action or on error.
        """
        if not self._ensure_client():
            return {"action": "done", "message": "LLM unavailable; cannot plan browser actions"}

        import json

        history_str = ""
        if history:
            history_str = "\n".join(
                f"Step {h.get('step', i)}: {json.dumps(h.get('action', h))}"
                for i, h in enumerate(history[-5:])
            )

        text_block = f"""You are MYCA's browser planning module. Given the screenshot and accessibility tree, decide the NEXT action to achieve the goal.

Goal: {goal}
Current URL: {url or "unknown"}
Accessibility tree (use for selectors):
{a11y_tree or "{}"}

Recent actions taken:
{history_str or "None yet"}

Respond with JSON only. Valid actions:
- {{"action": "click", "selector": "CSS_SELECTOR"}} or {{"action": "click", "x": 100, "y": 200}}
- {{"action": "type", "selector": "input", "text": "text to type"}}
- {{"action": "navigate", "url": "https://..."}}
- {{"action": "scroll", "direction": "down", "delta": 300}}
- {{"action": "done", "message": "Summary of what was accomplished"}}

If the goal is already achieved, respond with {{"action": "done", "message": "..."}}.
Return ONLY valid JSON, no markdown or explanation."""

        content_parts = []
        if screenshot_b64:
            content_parts.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/png",
                    "data": screenshot_b64,
                },
            })
        content_parts.append({"type": "text", "text": text_block})

        try:
            response = await self._client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=512,
                messages=[{"role": "user", "content": content_parts}],
            )
            text = response.content[0].text if response.content else ""
            text = text.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[-1].rsplit("```", 1)[0]
            return json.loads(text)
        except Exception as e:
            logger.warning("plan_browser_action failed: %s", e)
            return {"action": "done", "message": f"Planning error: {e}"}
