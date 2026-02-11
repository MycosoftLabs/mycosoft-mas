"""
MYCA Intent Engine - LLM-based intent classification for routing

Created: Feb 11, 2026

Classifies user messages into intent types for unified routing:
- agent_task: Delegate to a specific agent
- tool_call: Execute a tool
- knowledge_query: Query MINDEX for fungi/data
- general_chat: LLM conversation
- system_command: N8N workflow or system action
- status_query: System/agent/data status
"""

from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)


class IntentType(Enum):
    """Types of intents MYCA can handle."""
    AGENT_TASK = "agent_task"
    TOOL_CALL = "tool_call"
    KNOWLEDGE_QUERY = "knowledge_query"
    GENERAL_CHAT = "general_chat"
    SYSTEM_COMMAND = "system_command"
    STATUS_QUERY = "status_query"
    UNKNOWN = "unknown"


@dataclass
class IntentResult:
    """Result of intent classification."""
    intent_type: IntentType
    confidence: float
    entities: Dict[str, Any] = field(default_factory=dict)
    target: Optional[str] = None  # Specific agent, tool, or workflow name
    reasoning: str = ""
    fallback_used: bool = False


class IntentEngine:
    """
    LLM-based intent classification engine for MYCA.
    
    Uses fast LLM (Gemini Flash) for quick classification,
    with rule-based fallback when LLM is unavailable.
    """
    
    # Keyword patterns for rule-based fallback
    AGENT_KEYWORDS = [
        r"\b(lab|laboratory|experiment)\b.*\b(agent|run|start|execute)\b",
        r"\b(deploy|deployment)\b.*\b(agent)\b",
        r"\b(ask|tell|have)\b.*\b(agent)\b",
        r"\b(delegate|assign)\b.*\bto\b",
        r"\b(ceo|cfo|cto|coo|hr|legal|security|marketing|sales)\b.*\b(agent)\b",
    ]
    
    TOOL_KEYWORDS = [
        r"\b(run|execute|call|use)\b.*\b(tool|function|command)\b",
        r"\b(tool)\b.*\b(list|available|show)\b",
        r"\b(calculate|compute|analyze)\b",
    ]
    
    KNOWLEDGE_KEYWORDS = [
        r"\b(what|tell me about|explain|describe)\b.*\b(fungi|mushroom|species|taxon|mycel|amanita|psilocybe|boletus)\b",
        r"\b(fungi|mushroom|species|mycel|spore|hypha|amanita|psilocybe)\b.*\b(information|data|details|properties)\b",
        r"\b(search|find|lookup|query)\b.*\b(database|mindex|knowledge)\b",
        r"\b(how many|count|list)\b.*\b(species|observations|compounds)\b",
        r"\b(tell me about|what is|what are)\b.*\b(amanita|psilocybe|boletus|russula|lactarius)\b",
        r"\bamanita\s+muscaria\b",
    ]
    
    STATUS_KEYWORDS = [
        r"\b(status|state|health|running|online|offline)\b",
        r"\b(how|what)\b.*\b(agents|system|sensors|world)\b.*\b(doing|status)\b",
        r"\b(crep|earth2|flights|vessels|satellites|weather)\b.*\b(now|current|latest)\b",
        r"\b(metrics|statistics|stats)\b",
        r"\bwhat.*happening\b",
        r"\bsystem.*overview\b",
    ]
    
    SYSTEM_KEYWORDS = [
        r"\b(workflow|n8n|automation)\b",
        r"\b(restart|reboot|shutdown|deploy)\b.*\b(system|service|container)\b",
        r"\b(backup|sync|update)\b.*\b(database|system)\b",
        r"\b(trigger|execute)\b.*\b(workflow|pipeline)\b",
    ]
    
    def __init__(self):
        self.gemini_api_key = os.environ.get("GEMINI_API_KEY", "")
        self._compile_patterns()
    
    def _compile_patterns(self):
        """Pre-compile regex patterns for faster matching."""
        self._agent_patterns = [re.compile(p, re.IGNORECASE) for p in self.AGENT_KEYWORDS]
        self._tool_patterns = [re.compile(p, re.IGNORECASE) for p in self.TOOL_KEYWORDS]
        self._knowledge_patterns = [re.compile(p, re.IGNORECASE) for p in self.KNOWLEDGE_KEYWORDS]
        self._status_patterns = [re.compile(p, re.IGNORECASE) for p in self.STATUS_KEYWORDS]
        self._system_patterns = [re.compile(p, re.IGNORECASE) for p in self.SYSTEM_KEYWORDS]
    
    async def classify(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None
    ) -> IntentResult:
        """
        Classify user message intent.
        
        Args:
            message: User's message
            context: Optional context (conversation history, user info, etc.)
            
        Returns:
            IntentResult with classified intent
        """
        context = context or {}
        
        # Try LLM classification first
        if self.gemini_api_key:
            try:
                result = await self._classify_with_llm(message, context)
                if result.confidence > 0.5:
                    return result
            except Exception as e:
                logger.warning(f"LLM classification failed: {e}")
        
        # Fall back to rule-based classification
        return self._classify_with_rules(message, context)
    
    async def _classify_with_llm(
        self,
        message: str,
        context: Dict[str, Any]
    ) -> IntentResult:
        """Use LLM for intent classification."""
        
        system_prompt = """You are an intent classifier for MYCA, an AI orchestrator.
Classify the user's message into exactly ONE of these intent types:

1. agent_task - User wants to delegate a task to a specific agent (e.g., "ask the lab agent to run an experiment")
2. tool_call - User wants to execute a tool or function (e.g., "run the backup tool")
3. knowledge_query - User wants information about fungi, species, or data from MINDEX (e.g., "tell me about Amanita muscaria")
4. general_chat - General conversation or questions not fitting other categories
5. system_command - System operations, workflows, deployments (e.g., "trigger the backup workflow")
6. status_query - Asking about system status, agent status, sensor data, world state (e.g., "how many flights are tracked?")

Respond with JSON only:
{
  "intent_type": "one_of_the_above",
  "confidence": 0.0-1.0,
  "target": "specific agent/tool/workflow name if mentioned, else null",
  "entities": {"key": "value pairs of extracted entities"},
  "reasoning": "brief explanation"
}"""

        user_prompt = f"Classify this message: \"{message}\""
        
        if context.get("conversation_history"):
            user_prompt += f"\n\nRecent context: {context['conversation_history'][-3:]}"
        
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={self.gemini_api_key}"
        
        payload = {
            "contents": [
                {"role": "user", "parts": [{"text": system_prompt + "\n\n" + user_prompt}]}
            ],
            "generationConfig": {
                "temperature": 0.1,
                "maxOutputTokens": 256,
            }
        }
        
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(url, json=payload)
            
            if response.status_code != 200:
                raise Exception(f"Gemini API error: {response.status_code}")
            
            data = response.json()
            text = data["candidates"][0]["content"]["parts"][0]["text"]
            
            # Extract JSON from response - handle nested braces
            # First try to find JSON block between ```json and ``` if present
            json_block = re.search(r'```json\s*([\s\S]*?)\s*```', text)
            if json_block:
                json_str = json_block.group(1).strip()
            else:
                # Try to find JSON object by matching balanced braces
                start = text.find('{')
                if start == -1:
                    raise Exception("No JSON found in response")
                
                brace_count = 0
                end = start
                for i, char in enumerate(text[start:], start):
                    if char == '{':
                        brace_count += 1
                    elif char == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            end = i + 1
                            break
                
                json_str = text[start:end]
            
            if not json_str:
                raise Exception("No JSON found in response")
            
            result = json.loads(json_str)
            
            intent_type = IntentType(result.get("intent_type", "unknown"))
            
            return IntentResult(
                intent_type=intent_type,
                confidence=float(result.get("confidence", 0.7)),
                entities=result.get("entities", {}),
                target=result.get("target"),
                reasoning=result.get("reasoning", ""),
                fallback_used=False
            )
    
    def _classify_with_rules(
        self,
        message: str,
        context: Dict[str, Any]
    ) -> IntentResult:
        """Rule-based intent classification fallback."""
        
        message_lower = message.lower()
        
        # Check patterns in order of specificity
        scores = {
            IntentType.AGENT_TASK: self._match_patterns(message, self._agent_patterns),
            IntentType.TOOL_CALL: self._match_patterns(message, self._tool_patterns),
            IntentType.KNOWLEDGE_QUERY: self._match_patterns(message, self._knowledge_patterns),
            IntentType.STATUS_QUERY: self._match_patterns(message, self._status_patterns),
            IntentType.SYSTEM_COMMAND: self._match_patterns(message, self._system_patterns),
        }
        
        # Find best match
        best_intent = IntentType.GENERAL_CHAT
        best_score = 0.0
        
        for intent, score in scores.items():
            if score > best_score:
                best_score = score
                best_intent = intent
        
        # Extract target if possible
        target = self._extract_target(message, best_intent)
        
        # Extract entities
        entities = self._extract_entities(message, best_intent)
        
        confidence = min(best_score, 0.85)  # Cap at 0.85 for rule-based
        if confidence == 0:
            confidence = 0.6  # Default confidence for general chat
        
        return IntentResult(
            intent_type=best_intent,
            confidence=confidence,
            entities=entities,
            target=target,
            reasoning="Rule-based classification",
            fallback_used=True
        )
    
    def _match_patterns(self, message: str, patterns: List[re.Pattern]) -> float:
        """Count pattern matches and return normalized score."""
        matches = sum(1 for p in patterns if p.search(message))
        if matches == 0:
            return 0.0
        return min(0.4 + (matches * 0.2), 0.9)
    
    def _extract_target(self, message: str, intent: IntentType) -> Optional[str]:
        """Extract target (agent name, tool name, etc.) from message."""
        
        message_lower = message.lower()
        
        if intent == IntentType.AGENT_TASK:
            # Look for agent names
            agent_patterns = [
                r"(lab|laboratory)\s*agent",
                r"(ceo|cfo|cto|coo|hr|legal|security|marketing|sales)\s*agent",
                r"(deploy|deployment)\s*agent",
                r"(data|etl|mindex)\s*agent",
                r"(weather|earth2)\s*agent",
            ]
            for pattern in agent_patterns:
                match = re.search(pattern, message_lower)
                if match:
                    return match.group(0).replace(" ", "_")
        
        elif intent == IntentType.SYSTEM_COMMAND:
            # Look for workflow names
            workflow_patterns = [
                r"(backup|sync|deploy|update)\s*(workflow|pipeline)?",
            ]
            for pattern in workflow_patterns:
                match = re.search(pattern, message_lower)
                if match:
                    return match.group(1)
        
        return None
    
    def _extract_entities(self, message: str, intent: IntentType) -> Dict[str, Any]:
        """Extract relevant entities from message."""
        
        entities = {}
        
        if intent == IntentType.KNOWLEDGE_QUERY:
            # Extract species names
            species_pattern = r'\b([A-Z][a-z]+\s+[a-z]+)\b'
            species_match = re.search(species_pattern, message)
            if species_match:
                entities["species_name"] = species_match.group(1)
            
            # Extract common fungi terms
            fungi_terms = ["mushroom", "fungi", "mycelium", "spore", "hypha"]
            for term in fungi_terms:
                if term in message.lower():
                    entities["topic"] = term
                    break
        
        elif intent == IntentType.STATUS_QUERY:
            # Extract what status is being asked about
            status_targets = {
                "flights": ["flight", "aircraft", "plane", "aviation"],
                "vessels": ["vessel", "ship", "boat", "marine", "maritime"],
                "satellites": ["satellite", "orbit", "space"],
                "weather": ["weather", "forecast", "temperature", "climate"],
                "agents": ["agent", "agents"],
                "system": ["system", "service", "server"],
            }
            for target, keywords in status_targets.items():
                if any(kw in message.lower() for kw in keywords):
                    entities["status_target"] = target
                    break
        
        return entities


# Singleton instance
_intent_engine: Optional[IntentEngine] = None


def get_intent_engine() -> IntentEngine:
    """Get or create the intent engine singleton."""
    global _intent_engine
    if _intent_engine is None:
        _intent_engine = IntentEngine()
    return _intent_engine
