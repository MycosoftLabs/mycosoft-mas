from __future__ import annotations

import logging
import re
from typing import Any, Dict, Iterable, List, Optional, Tuple

from mycosoft_mas.agents.base_agent import BaseAgent
from mycosoft_mas.core.agent_registry import AgentCategory, AgentDefinition, get_agent_registry


logger = logging.getLogger(__name__)


class ManagerAgent(BaseAgent):
    """
    ManagerAgent routes tasks to the best-fit agent.

    Responsibilities:
    - Lightweight intent classification
    - Candidate selection from the AgentRegistry
    - Return a routing decision and ranked candidates
    """

    def __init__(self, agent_id: str, name: str, config: dict):
        super().__init__(agent_id, name, config)
        self.capabilities = {
            "routing",
            "intent_classification",
            "agent_selection",
        }
        self._intent_keyword_map = {
            "infrastructure": ["deploy", "restart", "vm", "docker", "container", "infra"],
            "security": ["audit", "pii", "security", "guardrail", "compliance"],
            "data": ["mindex", "dataset", "etl", "ingest", "telemetry", "query"],
            "simulation": ["simulate", "simulator", "petri", "mycelium", "earth2"],
            "financial": ["billing", "stripe", "revenue", "invoice", "payment"],
            "mycology": ["mycology", "fungi", "mushroom", "species", "spore"],
            "research": ["research", "paper", "study", "experiment"],
            "integration": ["n8n", "workflow", "webhook", "integration", "api"],
            "communication": ["announce", "press", "marketing", "pr", "copy"],
            "corporate": ["board", "legal", "hr", "policy", "ops"],
        }

    async def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        text = self._extract_text(task)
        if not text:
            return {
                "status": "error",
                "error": "Task text is required for routing",
            }

        intent = self._classify_intent(text, task.get("intent"))
        candidates = self._rank_agents(text, intent)
        primary = candidates[0] if candidates else None

        result = {
            "status": "success",
            "result": {
                "intent": intent,
                "primary_agent": self._serialize_agent(primary),
                "candidates": [self._serialize_agent(agent) for agent in candidates[:5]],
                "routing_reason": self._build_reason(text, intent, primary, candidates),
            },
        }
        await self.record_task_completion("manager_agent_route", result["result"])
        return result

    def _extract_text(self, task: Dict[str, Any]) -> str:
        for key in ("message", "query", "text", "prompt", "task"):
            value = task.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        return ""

    def _classify_intent(self, text: str, explicit_intent: Optional[str]) -> Dict[str, Any]:
        if explicit_intent:
            return {"category": explicit_intent, "source": "explicit"}

        tokens = self._tokenize(text)
        matches: List[Tuple[str, int]] = []
        for intent, keywords in self._intent_keyword_map.items():
            score = sum(1 for token in tokens if token in keywords)
            if score:
                matches.append((intent, score))

        if not matches:
            return {"category": "general", "source": "fallback"}

        matches.sort(key=lambda item: item[1], reverse=True)
        return {"category": matches[0][0], "source": "keyword"}

    def _rank_agents(self, text: str, intent: Dict[str, Any]) -> List[AgentDefinition]:
        registry = get_agent_registry()
        agents = registry.list_active()
        intent_category = self._map_category(intent.get("category", "general"))

        scored: List[Tuple[int, AgentDefinition]] = []
        for agent in agents:
            score = self._score_agent(agent, text, intent_category)
            if score > 0:
                scored.append((score, agent))

        scored.sort(key=lambda item: item[0], reverse=True)
        return [agent for _, agent in scored]

    def _score_agent(self, agent: AgentDefinition, text: str, intent_category: Optional[AgentCategory]) -> int:
        score = 0
        lowered = text.lower()

        if intent_category and agent.category == intent_category:
            score += 4

        for keyword in agent.keywords:
            if keyword and keyword.lower() in lowered:
                score += 2

        for trigger in agent.voice_triggers:
            if trigger and trigger.lower() in lowered:
                score += 3

        if agent.name.lower() in lowered or agent.display_name.lower() in lowered:
            score += 5

        return score

    def _map_category(self, category: str) -> Optional[AgentCategory]:
        if not category:
            return None
        try:
            return AgentCategory(category)
        except ValueError:
            return None

    def _tokenize(self, text: str) -> Iterable[str]:
        return re.findall(r"[a-z0-9]+", text.lower())

    def _serialize_agent(self, agent: Optional[AgentDefinition]) -> Optional[Dict[str, Any]]:
        if not agent:
            return None
        return {
            "agent_id": agent.agent_id,
            "name": agent.name,
            "display_name": agent.display_name,
            "category": agent.category.value,
            "capabilities": [cap.value for cap in agent.capabilities],
            "requires_confirmation": agent.requires_confirmation,
        }

    def _build_reason(
        self,
        text: str,
        intent: Dict[str, Any],
        primary: Optional[AgentDefinition],
        candidates: List[AgentDefinition],
    ) -> str:
        if not primary:
            return "No matching agents found for the provided task text."
        intent_category = intent.get("category", "general")
        match_count = len(candidates)
        return (
            f"Intent='{intent_category}' matched {match_count} agents. "
            f"Selected '{primary.display_name}' based on category and keyword relevance."
        )
