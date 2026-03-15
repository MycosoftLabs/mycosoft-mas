"""
MYCA LLM Brain — Own LLM (Ollama) 99.9% of the time.

MYCA uses her own brain (Ollama on MAS VM) and MAS/BRAIN intention memory.
Frontier models (Claude, GPT, etc.) are ONLY for integration/tool use (e.g. plan_browser_action),
never as fallback for user-facing responses.

Loads SOUL.md and MEMORY.md as context. Injects live world/device context
before every respond() and classify_intent() for non-hallucination grounding.

Date: 2026-03-09
"""

import json
import os
import logging
from pathlib import Path
from typing import Optional, TYPE_CHECKING, List

import aiohttp
from mycosoft_mas.llm.backend_selection import get_backend_for_role, MYCA_CORE
from mycosoft_mas.myca.os.staff_registry import load_staff_directory

if TYPE_CHECKING:
    from .core import MycaOS
    from mycosoft_mas.schemas.experience_packet import ExperiencePacket


def experience_packet_to_live_context(ep: "ExperiencePacket") -> str:
    """
    Convert ExperiencePacket to live-context string for LLM grounding.

    Produces the same format as _build_live_context for world/self sections.
    Used when ExperiencePacket is the primary grounding input (EP-as-primary path).
    """
    parts: List[str] = []
    if ep.world_state and ep.world_state.summary:
        parts.append(f"[World model]: {ep.world_state.summary}")
    if ep.world_state and ep.world_state.nlm_prediction:
        insights = ep.world_state.nlm_prediction.get("insights", [])
        if insights:
            parts.append(f"[NLM]: {insights[0]}" if len(insights) == 1 else f"[NLM]: {len(insights)} insights")
    if ep.self_state:
        ss = ep.self_state
        ss_parts = []
        if ss.services:
            ss_parts.append(f"services: {str(ss.services)[:400]}")
        if ss.agents:
            ss_parts.append(f"agents: {str(ss.agents)[:200]}")
        if ss.active_plans:
            ss_parts.append(f"active_plans: {', '.join(ss.active_plans[:5])}")
        if ss_parts:
            parts.append(f"[Self state]: {'; '.join(ss_parts)}")
    if not parts:
        return ""
    return "\n\n---\n\n## Live Context (Memory, Knowledge, Worldview)\n\n" + "\n\n".join(parts)

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

    async def _respond_ollama(self, base_url: str, model: str, messages: list) -> Optional[str]:
        """
        Call Ollama /api/chat.
        messages: list of {"role": "user"|"system"|"assistant", "content": "..."}
        Returns response text or None on failure.
        """
        url = f"{base_url.rstrip('/')}/api/chat"
        payload = {"model": model, "messages": messages, "stream": False}
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
            logger.warning("Ollama request failed: %s", e)
            return None

    async def _respond_openai_compatible(self, base_url: str, model: str, api_key: str, messages: list) -> Optional[str]:
        """
        Call OpenAI-compatible /v1/chat/completions (e.g. Nemotron).
        Returns response text or None on failure.
        """
        url = f"{base_url.rstrip('/')}/v1/chat/completions"
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        body = {"model": model, "messages": messages, "stream": False}
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    json=body,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=60),
                ) as resp:
                    if resp.status != 200:
                        logger.warning("OpenAI-compatible returned status %s", resp.status)
                        return None
                    data = await resp.json()
                    choice = (data.get("choices") or [{}])[0]
                    msg = choice.get("message", {})
                    content = msg.get("content", "")
                    return content.strip() if content else None
        except Exception as e:
            logger.warning("OpenAI-compatible request failed: %s", e)
            return None

    async def _respond_backend(self, messages: list) -> Optional[str]:
        """
        Call the MYCA core backend (from unified backend_selection).
        Uses get_backend_for_role(MYCA_CORE); dispatches to Ollama or OpenAI-compatible (e.g. Nemotron).
        """
        selection = get_backend_for_role(MYCA_CORE)
        if selection.provider == "ollama":
            return await self._respond_ollama(selection.base_url, selection.model, messages)
        return await self._respond_openai_compatible(
            selection.base_url, selection.model, selection.api_key or "", messages
        )

    async def _build_live_context(self, user_message: str, context: Optional[dict] = None) -> str:
        """
        Assemble live context from memory, devices, CREP, Earth2, MycoBrain, world model.
        ALWAYS include device/world data when available for non-hallucination grounding.
        Builds Merkle world root from slot data and injects [Merkle world root] for provable grounding.
        No keyword gating — inject whenever we have live data.
        """
        if not self._os:
            return ""

        parts: list[str] = []
        slot_data: dict = {}  # For Merkle world root
        msg_lower = (user_message or "").lower()

        try:
            # Device registry snapshot (sync) — for Merkle and context
            try:
                from mycosoft_mas.core.routers.device_registry_api import get_device_registry_snapshot

                snap = get_device_registry_snapshot()
                slot_data["device_registry"] = snap
                slot_data["device_health"] = {
                    k: v.get("status", "unknown")
                    for k, v in snap.get("devices", {}).items()
                }
            except Exception:
                pass

            # 1. Recall from memory (session, working, episodic)
            mb = getattr(self._os, "mindex_bridge", None)
            mas = getattr(self._os, "mas_bridge", None)
            person_id = (context or {}).get("person_id") if context else None
            staff_directory = load_staff_directory() if person_id else {}
            if mb and hasattr(mb, "recall"):
                for key in ["session:last_topic", "working:current_task", "episodic:recent_decisions"]:
                    val = await mb.recall(key)
                    if val:
                        parts.append(f"[Memory {key}]: {val[:500]}")
                if person_id:
                    personal_key = f"session:last_topic:{person_id}"
                    personal_val = await mb.recall(personal_key)
                    if personal_val:
                        parts.append(f"[Person memory {person_id}]: {personal_val[:500]}")
            if mas and hasattr(mas, "recall_memory"):
                memories = await mas.recall_memory(user_message[:100] if user_message else "context", limit=3)
                if memories:
                    for m in memories:
                        c = m.get("content", m) if isinstance(m, dict) else str(m)
                        parts.append(f"[MAS memory]: {str(c)[:300]}")
            if person_id and staff_directory.get(person_id):
                staff = staff_directory[person_id]
                parts.append(
                    f"[Staff profile]: {staff.get('name')} | role: {staff.get('role')} | "
                    f"scopes: {', '.join(staff.get('scopes', [])[:6])}"
                )

            # 2. MINDEX KG if domain-specific
            if mb and any(kw in msg_lower for kw in ["species", "fungi", "fungus", "taxonomy", "compound", "mushroom", "mycology"]):
                try:
                    kg_results = await mb.query_knowledge_graph(user_message[:80], limit=5)
                    if kg_results:
                        parts.append(f"[MINDEX knowledge]: {str(kg_results)[:800]}")
                except Exception:
                    pass

            # 3. CREP worldview — ALWAYS include when available (non-hallucination)
            crep = getattr(self._os, "crep_bridge", None)
            if crep and hasattr(crep, "get_worldview_summary"):
                try:
                    summary = await crep.get_worldview_summary()
                    if summary:
                        parts.append(f"[CREP worldview]: {summary}")
                        slot_data["crep_summary"] = summary
                except Exception:
                    pass

            # 4. Earth2 weather — ALWAYS include when available
            earth2 = getattr(self._os, "earth2_bridge", None)
            if earth2 and hasattr(earth2, "get_weather_context"):
                try:
                    ctx = await earth2.get_weather_context()
                    if ctx:
                        parts.append(f"[Earth2]: {ctx}")
                        slot_data["earth_sim_summary"] = ctx
                except Exception:
                    pass

            # 5. MycoBrain/device status — ALWAYS include when available (device grounding)
            mycobrain = getattr(self._os, "mycobrain_bridge", None)
            if mycobrain and hasattr(mycobrain, "get_telemetry_summary"):
                try:
                    summary = await mycobrain.get_telemetry_summary()
                    if summary:
                        parts.append(f"[Devices]: {summary}")
                        slot_data["environment_feeds"] = summary
                except Exception:
                    pass

            # 6. NatureOS — ALWAYS include when available
            natureos = getattr(self._os, "natureos_bridge", None)
            if natureos and hasattr(natureos, "get_context_summary"):
                try:
                    summary = await natureos.get_context_summary()
                    if summary:
                        parts.append(f"[NatureOS]: {summary}")
                        if "environment_feeds" not in slot_data:
                            slot_data["environment_feeds"] = summary
                except Exception:
                    pass

            # 7. Unified search when query looks like search (via MAS search orchestrator)
            if any(kw in msg_lower for kw in ["search", "find", "lookup", "where is", "show me", "what do we know"]):
                try:
                    from mycosoft_mas.consciousness.search_orchestrator import run_unified_search
                    result = await run_unified_search(query=user_message[:120], limit=5)
                    res = result.get("results") or {}
                    combined = (res.get("keyword") or []) + (res.get("semantic") or [])
                    if combined:
                        parts.append(f"[Unified search]: {str(combined)[:800]}")
                except Exception:
                    pass

            # 8. World model — ALWAYS include when available (world state grounding)
            world_model = getattr(self._os, "world_model", None)
            if world_model:
                try:
                    await world_model.update()
                    summary = await world_model.get_summary()
                    if summary:
                        parts.append(f"[World model]: {summary}")
                        slot_data["map_state"] = summary
                    relevant = await world_model.get_relevant_context(
                        type("Focus", (), {"content": user_message, "related_entities": []})()
                    )
                    if relevant:
                        parts.append(f"[World context]: {str(relevant)[:1200]}")
                except Exception:
                    pass

            # 9. Presence — ALWAYS include when available
            presence = getattr(self._os, "presence_bridge", None)
            if presence and hasattr(presence, "get_presence_summary"):
                try:
                    summary = await presence.get_presence_summary()
                    if summary:
                        parts.append(f"[Presence]: {summary}")
                except Exception:
                    pass

            # 10. NLM — ALWAYS include when available
            nlm = getattr(self._os, "nlm_bridge", None)
            if nlm and hasattr(nlm, "get_summary"):
                try:
                    summary = await nlm.get_summary()
                    if summary:
                        parts.append(f"[NLM]: {summary}")
                        slot_data["nlm_summary"] = summary
                except Exception:
                    pass

            # 11. Merkle world root — provable grounding anchor
            if slot_data:
                try:
                    from mycosoft_mas.merkle.world_root_service import build_world_root

                    root_hex = build_world_root(slot_data)
                    parts.append(f"[Merkle world root]: {root_hex}")
                except Exception as e:
                    logger.debug("Merkle world root build failed: %s", e)
        except Exception as e:
            logger.debug("Live context build failed: %s", e)

        if not parts:
            return ""
        return "\n\n---\n\n## Live Context (Memory, Knowledge, Worldview)\n\n" + "\n\n".join(parts)

    async def _build_live_context_with_packet(
        self,
        user_message: str,
        context: Optional[dict],
        ep: "ExperiencePacket",
    ) -> str:
        """
        Build live context using ExperiencePacket for world/self and bridges for memory.
        Used when EP is the primary grounding input (EP-as-primary path).
        """
        parts: List[str] = []
        if not self._os:
            pass
        else:
            try:
                mb = getattr(self._os, "mindex_bridge", None)
                mas = getattr(self._os, "mas_bridge", None)
                person_id = (context or {}).get("person_id") if context else None
                staff_directory = load_staff_directory() if person_id else {}
                if mb and hasattr(mb, "recall"):
                    for key in ["session:last_topic", "working:current_task", "episodic:recent_decisions"]:
                        val = await mb.recall(key)
                        if val:
                            parts.append(f"[Memory {key}]: {val[:500]}")
                    if person_id:
                        personal_val = await mb.recall(f"session:last_topic:{person_id}")
                        if personal_val:
                            parts.append(f"[Person memory {person_id}]: {personal_val[:500]}")
                if mas and hasattr(mas, "recall_memory"):
                    memories = await mas.recall_memory(user_message[:100] if user_message else "context", limit=3)
                    if memories:
                        for m in memories:
                            c = m.get("content", m) if isinstance(m, dict) else str(m)
                            parts.append(f"[MAS memory]: {str(c)[:300]}")
                if person_id and staff_directory.get(person_id):
                    staff = staff_directory[person_id]
                    parts.append(
                        f"[Staff profile]: {staff.get('name')} | role: {staff.get('role')} | "
                        f"scopes: {', '.join(staff.get('scopes', [])[:6])}"
                    )
            except Exception as e:
                logger.debug("Memory context with packet failed: %s", e)
        packet_ctx = experience_packet_to_live_context(ep)
        if packet_ctx:
            parts.append(packet_ctx)
        if not parts:
            return ""
        return "\n\n---\n\n## Live Context (Memory, Knowledge, Worldview)\n\n" + "\n\n".join(parts)

    async def respond(
        self,
        user_message: str,
        context: Optional[dict] = None,
        experience_packet: Optional["ExperiencePacket"] = None,
    ) -> str:
        """
        Generate a response as MYCA using her OWN LLM (Ollama). 99.9% of the time.
        No frontier-model fallback — if Ollama fails, MYCA reports the issue.

        When experience_packet is provided with world_state and self_state, it is used
        as the primary grounding source for world/self context instead of ad hoc bridge
        fan-out (EP-as-primary path). Memory recall is still fetched from bridges.
        """
        if experience_packet and experience_packet.world_state and experience_packet.self_state:
            live_ctx = await self._build_live_context_with_packet(user_message, context, experience_packet)
        else:
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
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_block},
        ]

        # Primary: unified MYCA core backend (Ollama or Nemotron via backend_selection)
        text = await self._respond_backend(messages)
        if text:
            return text.strip() or "I'm here. What would you like me to do?"

        # No fallback to frontier models — MYCA needs to be fixed
        logger.error("MYCA brain backend failed — no fallback. Check config/models.yaml and backend_selection.")
        return (
            "My brain isn't responding right now — Ollama needs to be checked on the MAS server. "
            "I'm not falling back to other AI providers; this needs to be fixed."
        )

    async def classify_intent(self, message: str, sender: str) -> dict:
        """
        Use MYCA's own LLM (Ollama) to classify message intent for routing.
        No frontier-model fallback — on failure use keyword routing.
        """
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

        messages = [
            {"role": "system", "content": "You are MYCA's routing classifier. Output valid JSON only."},
            {"role": "user", "content": prompt},
        ]

        fallback_text = await self._respond_backend(messages)
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
